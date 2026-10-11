import SwiftUI
import AppKit
import LensCore
import DeviceKit

struct LensDraft: Equatable {
    var name: String
    var minimum: String
    var maximum: String
    var active: String
    var aperture: String
    var currentAperture: String
    var notes: String
    init(_ profile: LensProfile) {
        name = profile.displayName
        minimum = profile.minimumFocalLengthMM.formatted(.number.grouping(.never))
        maximum = profile.maximumFocalLengthMM.formatted(.number.grouping(.never))
        active = profile.activeFocalLengthMM?.formatted(.number.grouping(.never)) ?? ""
        aperture = profile.maximumAperture.formatted(.number.grouping(.never))
        currentAperture = profile.currentAperture?.formatted(.number.grouping(.never)) ?? ""
        notes = profile.notes
    }
    func profile(from base: LensProfile) throws -> LensProfile {
        func number(_ text: String, _ label: String) throws -> Double {
            let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: Locale.current.decimalSeparator ?? ".", with: ".")
            guard let value = Double(normalized), value.isFinite else { throw LibraryError.invalid("Enter a valid number for \(label).") }
            return value
        }
        func optional(_ text: String, _ label: String) throws -> Double? {
            text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : try number(text, label)
        }
        var result = base
        result.displayName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        result.minimumFocalLengthMM = try number(minimum, "focal length")
        result.maximumFocalLengthMM = base.kind == .zoom ? try number(maximum, "maximum focal length") : result.minimumFocalLengthMM
        result.activeFocalLengthMM = base.kind == .zoom ? try optional(active, "current zoom setting") : nil
        result.maximumAperture = try number(aperture, "maximum aperture")
        result.currentAperture = try optional(currentAperture, "fixed camera aperture")
        result.notes = notes
        try result.validate()
        return result
    }
}

enum AppTab: Hashable { case device, lensLibrary }

@MainActor final class AppModel: ObservableObject {
    @Published private(set) var selectedTab: AppTab = .device
    @Published var library: LensLibrary
    @Published var selection: String?
    @Published var draft: LensDraft?
    @Published var showLensEditor = false
    @Published var showPhotoCredits = false
    @Published var showDeviceTools = false
    @Published private(set) var preparedLensID: String?
    @Published var errorMessage: String?
    @Published var loadError: String?
    @Published var showSwitchConfirmation = false
    @Published var showImportConfirmation = false
    @Published var pendingImport: LensLibrary?
    @Published var devices: [DeviceIdentity] = []
    @Published var discoveryError = false
    @Published var isDiscovering = false
    @Published private(set) var isRefreshing = false
    @Published var firmwareObservation: FirmwareObservation?
    @Published var pendingUpdate: PendingUpdate?
    @Published var appliedLens: AppliedLens?
    @Published var stockUploadQualified = false
    @Published var updateStateError: String?
    @Published var pendingUpdateError: String?
    @Published var isUploadingFirmware = false
    @Published var isReadingFirmware = false
    @Published var deviceMessage = "Connect the LM-EA9 using its USB cap."
    @Published var idleAcknowledged = false
    @Published var reconnectRequired = false
    @Published var busy = false
    @Published var progress: BackupProgress?
    @Published var lastBackup: BackupResult?
    let store: LibraryStore
    let deviceService: DeviceService
    let firmwareStore: FirmwareObservationStore
    let preparedLensStore: PreparedLensStore
    private enum NavigationTarget { case profile(String?), tab(AppTab) }
    private var pendingNavigation: NavigationTarget?
    private var cancellation: CancellationToken?
    private var quitAfterBackup = false
    private let inventoryProvider: @Sendable () async throws -> [DeviceIdentity]
    private let reconnectProvider: @Sendable (UInt64) async throws -> Bool

    init(directory: URL,
         inventory: (@Sendable () async throws -> [DeviceIdentity])? = nil,
         reconnect: (@Sendable (UInt64) async throws -> Bool)? = nil) {
        store = LibraryStore(directory: directory)
        let service = DeviceService(stateDirectory: directory)
        deviceService = service
        inventoryProvider = inventory ?? { try await service.inventory() }
        reconnectProvider = reconnect ?? { try await service.reconnectRequired(for: $0) }
        firmwareStore = FirmwareObservationStore(directory: directory)
        preparedLensStore = PreparedLensStore(directory: directory)
        firmwareObservation = try? firmwareStore.load()
        pendingUpdate = try? deviceService.pendingUpdate()
        appliedLens = try? deviceService.appliedLens()
        do { library = try store.loadOrSeed() }
        catch {
            library = (try? LensLibrary.seeds()) ?? LensLibrary(profiles: [])
            loadError = "The saved library could not be opened: \(error.localizedDescription) It was preserved. Import a valid library to recover; saving is disabled."
        }
        selection = library.profiles.first?.id
        draft = library.profiles.first.map(LensDraft.init)
        preparedLensID = try? preparedLensStore.load(in: library)
        if preparedLensID == nil, let id = appliedLens?.setting.id,
           library.profiles.contains(where: { $0.id == id }) { preparedLensID = id }
    }
    var preparedLens: LensProfile? { library.profiles.first { $0.id == preparedLensID } }
    func prepareLens(_ profile: LensProfile) {
        guard loadError == nil, !isDirty, !busy else { return }
        do {
            try preparedLensStore.save(profile.id, in: library)
            preparedLensID = profile.id
            requestTab(.device)
        } catch { errorMessage = error.localizedDescription }
    }
    /// A dropdown selection is a local preparation. The Apply button owns USB writes.
    func chooseDeviceLens(_ id: String?) {
        guard let profile = library.profiles.first(where: { $0.id == id }), !busy, !isDirty else { return }
        prepareLens(profile)
    }
    var preparedLensIssue: String? {
        guard let profile = preparedLens else { return nil }
        do { _ = try AdapterLensSetting(profile: profile); return nil }
        catch { return error.localizedDescription }
    }
    func editLens(_ profile: LensProfile) {
        guard !isDirty else { return }
        select(profile.id); showLensEditor = true
    }
    func closeLensEditor() {
        if isDirty {
            let alert = NSAlert()
            alert.messageText = "Save your lens changes?"
            alert.informativeText = "Changes are stored on this Mac."
            alert.addButton(withTitle: "Save"); alert.addButton(withTitle: "Discard"); alert.addButton(withTitle: "Cancel")
            switch alert.runModal() {
            case .alertFirstButtonReturn: if !save() { return }
            case .alertSecondButtonReturn: revert()
            default: return
            }
        }
        showLensEditor = false
    }
    var selectedProfile: LensProfile? { library.profiles.first { $0.id == selection } }
    var isDirty: Bool { if let draft, let profile = selectedProfile { return draft != LensDraft(profile) }; return false }
    var validationMessage: String? {
        guard let draft, let profile = selectedProfile else { return nil }
        do { _ = try draft.profile(from: profile); return nil } catch { return error.localizedDescription }
    }
    var canSave: Bool { isDirty && loadError == nil && validationMessage == nil }
    var canReadDevice: Bool {
        !busy && !isRefreshing && idleAcknowledged && !reconnectRequired && !discoveryError
            && devices.count == 1 && devices.first?.qualifiedDescriptor == true
    }
    var currentFirmwareObservation: FirmwareObservation? {
        guard !discoveryError, devices.count == 1, let device = devices.first,
              let firmwareObservation, firmwareObservation.belongs(to: device) else { return nil }
        return firmwareObservation
    }
    var connectionLabel: String {
        if isDiscovering { return "Checking connection…" }
        if discoveryError { return "Unable to check connection" }
        if devices.isEmpty { return "Not connected" }
        return devices.count == 1 ? (devices.first?.qualifiedDescriptor == true ? "Connected" : "Unrecognized adapter") : "Multiple adapters connected"
    }
    func binding(_ keyPath: WritableKeyPath<LensDraft, String>) -> Binding<String> {
        Binding(get: { self.draft?[keyPath: keyPath] ?? "" }, set: { self.draft?[keyPath: keyPath] = $0 })
    }
    func requestSelection(_ id: String?) {
        guard id != selection else { return }
        requestNavigation(.profile(id))
    }
    func requestTab(_ tab: AppTab) {
        guard tab != selectedTab else { return }
        requestNavigation(.tab(tab))
    }
    private func requestNavigation(_ target: NavigationTarget) {
        if isDirty { pendingNavigation = target; showSwitchConfirmation = true }
        else { navigate(target) }
    }
    private func navigate(_ target: NavigationTarget) {
        switch target {
        case .profile(let id): select(id)
        case .tab(let tab): selectedTab = tab
        }
    }
    private func select(_ id: String?) { selection = id; draft = selectedProfile.map(LensDraft.init) }
    func finishSwitch(saveFirst: Bool) {
        if saveFirst && !save() { return }
        if !saveFirst { revert() }
        if let pendingNavigation { navigate(pendingNavigation) }
        pendingNavigation = nil
    }
    func cancelSwitch() { pendingNavigation = nil }
    @discardableResult func save() -> Bool {
        guard loadError == nil, let draft, let base = selectedProfile,
              let index = library.profiles.firstIndex(where: { $0.id == base.id }) else { return false }
        do {
            var updated = try draft.profile(from: base)
            updated.revision += 1; updated.savedAt = Date()
            var next = library; next.profiles[index] = updated
            try store.save(next)
            library = next; self.draft = LensDraft(updated)
            return true
        } catch { errorMessage = error.localizedDescription; return false }
    }
    func revert() { draft = selectedProfile.map(LensDraft.init) }
    func importLibrary() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.json]; panel.canChooseDirectories = false; panel.allowsMultipleSelection = false
        panel.message = "Choose an Open LM-EA9 lens library. You can review before replacing the local library."
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do { pendingImport = try LensLibrary.decode(store.readBounded(url)); showImportConfirmation = true }
        catch { errorMessage = error.localizedDescription }
    }
    func commitImport() {
        guard let pendingImport else { return }
        do {
            // Preserve even an unreadable original library before explicitly approved replacement.
            if FileManager.default.fileExists(atPath: store.fileURL.path) {
                try FileManager.default.copyItem(at: store.fileURL, to: store.directory.appendingPathComponent("profiles-before-import-\(UUID().uuidString).json"))
            }
            try store.save(pendingImport)
            library = pendingImport; loadError = nil; self.pendingImport = nil
            select(library.profiles.first?.id)
            selectedTab = .lensLibrary
            preparedLensID = try? preparedLensStore.load(in: library)
        } catch { errorMessage = error.localizedDescription }
    }
    func exportLibrary() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]; panel.nameFieldStringValue = "LM-EA9-lens-library.json"
        panel.message = "Export saved lens metadata. Unsaved edits are excluded."
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do { try store.export(library, to: url) } catch { errorMessage = error.localizedDescription }
    }
    /// Observe OS descriptors and bounded local files only; never send a HID report.
    func monitorDevices() async {
        await refreshDevices()
        while !Task.isCancelled {
            do { try await Task.sleep(for: .seconds(2)) } catch { return }
            if Task.isCancelled { return }
            await refreshDevices(silent: true)
        }
    }
    func refreshDevices(silent: Bool = false) async {
        guard !busy, !isRefreshing else { return }
        isRefreshing = true; isDiscovering = !silent
        defer { isRefreshing = false; isDiscovering = false }
        do {
            let previousIDs = devices.map(\.id)
            let wasDiscoveryError = discoveryError
            let discovered = try await inventoryProvider()
            let blocked = if let device = discovered.first { try await reconnectProvider(device.id) } else { false }
            devices = discovered
            discoveryError = false
            let changed = previousIDs != devices.map(\.id)
            if changed || blocked { idleAcknowledged = false }
            reconnectRequired = blocked
            if changed || wasDiscoveryError || !silent {
                deviceMessage = devices.isEmpty ? "Connect the LM-EA9 through its USB cap. Connection updates automatically." :
                    devices.count == 1 ? "Connected through the USB cap." : "Connect exactly one LM-EA9 for USB operations."
            }
        } catch {
            devices = []; idleAcknowledged = false; discoveryError = true
            deviceMessage = error.localizedDescription
        }
        refreshUpdateState(for: devices.count == 1 ? devices.first : nil)
    }
    private func refreshUpdateState(for device: DeviceIdentity?) {
        // CLI verification can publish a new observation while this window is open.
        // Refresh the bounded local cache without sending a CHECK report.
        firmwareObservation = try? firmwareStore.load()
        var errors: [String] = []
        do { pendingUpdate = try deviceService.pendingUpdate(); pendingUpdateError = nil }
        catch { pendingUpdate = nil; pendingUpdateError = error.localizedDescription; errors.append("Update journal: \(error.localizedDescription)") }
        do { appliedLens = try deviceService.appliedLens() }
        catch { appliedLens = nil; errors.append("Lens history: \(error.localizedDescription)") }
        do { stockUploadQualified = if let device { try deviceService.stockUploadQualified(for: device) } else { false } }
        catch { stockUploadQualified = false; errors.append("Upload qualification: \(error.localizedDescription)") }
        updateStateError = errors.isEmpty ? nil : errors.joined(separator: "\n") + "\nThe files were preserved. After reconnecting, USB tools can restore stock from a verified backup."
    }
    var currentAppliedLens: AppliedLens? {
        guard updateStateError == nil, !waitingForVerification, !discoveryError, devices.count == 1, let device = devices.first,
              let appliedLens, appliedLens.belongs(to: device) else { return nil }
        // Firmware history uses second-resolution ISO dates; applied history
        // retains fractions. Treat a differing observation in that same second
        // conservatively rather than displaying a stale lens setting.
        if let observation = currentFirmwareObservation,
           observation.readAt.timeIntervalSince1970 >= floor(appliedLens.verifiedAt.timeIntervalSince1970),
           observation.version != appliedLens.firmwareVersion { return nil }
        return appliedLens
    }
    var waitingForVerification: Bool { pendingUpdate?.needsVerification == true }
    var preparedMatchesApplied: Bool {
        guard let preparedLens, let currentAppliedLens else { return false }
        return (try? AdapterLensSetting(profile: preparedLens)) == currentAppliedLens.setting
    }
    var canApplyLens: Bool { canChangeFirmware && variantForLensChanges != nil && !preparedMatchesApplied }
    var canVerifyUpdate: Bool {
        canReadDevice && pendingUpdateError == nil && waitingForVerification && pendingUpdate?.device.id != devices.first?.id
            && pendingUpdate?.device.serial == devices.first?.serial
    }
    func prepareAdapter() {
        guard canReadDevice, updateStateError == nil, !waitingForVerification, !stockUploadQualified else { return }
        let alert = NSAlert()
        alert.messageText = "Prepare this adapter for lens changes?"
        alert.informativeText = "A verified backup is saved, then the same stock application is re-uploaded. Unplug and reconnect to verify it. This one-time check tests the USB upload path before custom firmware is installed."
        alert.addButton(withTitle: "Prepare"); alert.addButton(withTitle: "Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        runLensOperation(writing: true) { device, token in
            _ = try await self.deviceService.qualifyStockUpload(device: device, idleAcknowledged: self.idleAcknowledged,
                    cancellation: token, progress: { update in Task { @MainActor in self.progress = update } })
            self.deviceMessage = "Stock application uploaded. Reconnect the USB cap, refresh, then verify."
        }
    }
    func chooseStockRestore() {
        guard canReadDevice else { return }
        let panel = NSOpenPanel()
        panel.canChooseFiles = true; panel.canChooseDirectories = true; panel.allowsMultipleSelection = false
        panel.message = "Choose this adapter’s original verified stock 1.8.0 backup."
        guard panel.runModal() == .OK, let url = panel.url else { return }
        let alert = NSAlert()
        alert.messageText = "Restore stock firmware?"
        alert.informativeText = "The backup is validated for this adapter before any write. A fresh backup is saved, then the stock application is restored. Unplug and reconnect afterward to verify."
        alert.addButton(withTitle: "Restore"); alert.addButton(withTitle: "Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        runLensOperation(writing: true) { device, token in
            _ = try await self.deviceService.restoreStock(backupURL: url, device: device, idleAcknowledged: self.idleAcknowledged,
                    cancellation: token, progress: { update in Task { @MainActor in self.progress = update } })
            self.deviceMessage = "Stock application uploaded. Reconnect and verify before using the camera."
        }
    }
    var firmwareBehaviorNote: String {
        switch currentAppliedLens?.firmwareVersion {
        case "2.1.0", "2.2.0", "2.3.0", "2.4.0": return "This AF firmware is designed to move the mount. Focus accuracy still needs a camera test with the mounted lens."
        case "2.0.0": return "Verified metadata-only firmware disables motor motion. Use manual focus."
        default: return "Installed firmware and motor behavior have not been verified for this connection."
        }
    }
    var variantForLensChanges: FirmwareVariant? {
        if let applied = currentAppliedLens {
            return FirmwareVariant.allCases.first { $0.versionString == applied.firmwareVersion }
        }
        // An unknown custom image must never silently become a metadata-only upload.
        // Stock has no profile row; its separately qualified version permits initial setup.
        return currentFirmwareObservation?.version == "1.8.0" ? .metadataOnly : nil
    }
    var usesExperimentalAF: Bool { variantForLensChanges?.enablesAutofocus == true }
    var canChangeFirmware: Bool { canReadDevice && updateStateError == nil && stockUploadQualified && preparedLens != nil && preparedLensIssue == nil && !waitingForVerification && !isDirty }
    func applyLens() {
        guard canApplyLens, let variant = variantForLensChanges else { return }
        applyLens(variant: variant, preservingFirmware: true)
    }
    func installAutofocus() { applyLens(variant: .autofocusFactoryBaseline) }
    func installMetadataOnly() { applyLens(variant: .metadataOnly) }
    private func applyLens(variant: FirmwareVariant, preservingFirmware: Bool = false) {
        guard canChangeFirmware, let profile = preparedLens else { return }
        do { _ = try FirmwareImageBuilder.prepare(profile: profile, variant: variant) }
        catch { errorMessage = error.localizedDescription; return }
        let alert = NSAlert()
        alert.messageText = "Apply \(profile.displayName) to the adapter?"
        alert.informativeText = (variant.enablesAutofocus ? "Experimental AF \(variant.versionString) enables motor movement and uses bounded homing on camera startup. Focus accuracy with this lens is not yet qualified. A verified backup is saved first. Unplug and reconnect after upload to verify." : "This prototype installs custom firmware and saves a verified backup first. Motor motion is disabled in this metadata test build; use manual focus on the A7C II. It reports the focal length and aperture you choose; it cannot sense the lens’s aperture or zoom rings. Unplug and reconnect afterward to verify the update.")
        alert.addButton(withTitle: "Apply"); alert.addButton(withTitle: "Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        runLensOperation(writing: true) { device, token in
            _ = try await self.deviceService.apply(profile: profile, variant: variant, device: device, idleAcknowledged: self.idleAcknowledged,
                    preserveInstalledFirmware: preservingFirmware,
                    cancellation: token, progress: { update in Task { @MainActor in self.progress = update } })
            self.pendingUpdate = try self.deviceService.pendingUpdate()
            self.deviceMessage = "Uploaded. Unplug and reconnect the USB cap, then verify."
        }
    }
    func verifyLensUpdate() {
        guard canVerifyUpdate else { return }
        runLensOperation { device, token in
            self.appliedLens = try await self.deviceService.verifyUpdate(device: device, idleAcknowledged: self.idleAcknowledged,
                    cancellation: token, progress: { update in Task { @MainActor in self.progress = update } })
            self.pendingUpdate = try self.deviceService.pendingUpdate()
            self.rememberFirmware(FirmwareObservation(device: device, version: self.appliedLens?.firmwareVersion ?? "1.8.0"))
            self.deviceMessage = self.appliedLens == nil ? "Stock restoration verified." : "Lens setting verified on the adapter. Camera behavior needs a camera check."
        }
    }
    func readAdapterLens() {
        guard canReadDevice && updateStateError == nil && !waitingForVerification else { return }
        runLensOperation { device, token in
            self.appliedLens = try await self.deviceService.readLens(device: device, idleAcknowledged: self.idleAcknowledged,
                    cancellation: token, progress: { update in Task { @MainActor in self.progress = update } })
            self.deviceMessage = self.appliedLens == nil ? "Stock firmware has no supported readable lens profile." : "Lens setting verified on the adapter."
        }
    }
    private func runLensOperation(writing: Bool = false, _ operation: @escaping @MainActor (DeviceIdentity, CancellationToken) async throws -> Void) {
        let device = devices[0], token = CancellationToken()
        cancellation = token; busy = true; progress = nil; isUploadingFirmware = writing
        Task { [self] in
            do { try await operation(device, token) }
            catch { deviceMessage = error.localizedDescription; errorMessage = deviceMessage }
            refreshUpdateState(for: device)
            reconnectRequired = (try? await deviceService.reconnectRequired(for: device.id)) ?? true
            busy = false; cancellation = nil; idleAcknowledged = false; isUploadingFirmware = false
            if quitAfterBackup { NSApp.terminate(nil) }
        }
    }
    private func rememberFirmware(_ observation: FirmwareObservation) {
        firmwareObservation = observation
        do { try firmwareStore.save(observation) }
        catch { errorMessage = "The version was read, but its local history could not be saved: \(error.localizedDescription)" }
    }
    func readFirmware() {
        guard canReadDevice else { return }
        let device = devices[0], token = CancellationToken()
        cancellation = token; busy = true; isReadingFirmware = true; progress = nil
        Task { [self] in
            do {
                let observation = try await deviceService.readFirmware(device: device, idleAcknowledged: idleAcknowledged, cancellation: token)
                rememberFirmware(observation)
                deviceMessage = "Firmware version read from the adapter."
            } catch {
                errorMessage = error.localizedDescription; idleAcknowledged = false
                deviceMessage = "Version read stopped. Reconnect the USB cap, then refresh."
            }
            reconnectRequired = (try? await deviceService.reconnectRequired(for: device.id)) ?? true
            busy = false; isReadingFirmware = false; cancellation = nil
            if quitAfterBackup { NSApp.terminate(nil) }
        }
    }
    func chooseBackup() {
        guard canReadDevice else { return }
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "LM-EA9-\(Date().formatted(.iso8601.year().month().day().dateSeparator(.dash))).ea9backup"
        panel.message = "Choose a new backup name. Two complete flash reads will be compared before saving."
        panel.canCreateDirectories = true
        guard panel.runModal() == .OK, let url = panel.url else { return }
        var destination = url
        if destination.pathExtension != "ea9backup" { destination.appendPathExtension("ea9backup") }
        startBackup(to: destination)
    }
    private func startBackup(to url: URL) {
        let device = devices[0], token = CancellationToken()
        cancellation = token; busy = true; progress = nil; lastBackup = nil
        Task { [self] in
            do {
                lastBackup = try await deviceService.backup(device: device, to: url, idleAcknowledged: idleAcknowledged,
                    cancellation: token, progress: { [weak self] update in
                        Task { @MainActor in self?.progress = update }
                    })
                if let lastBackup {
                    rememberFirmware(FirmwareObservation(device: device, version: lastBackup.manifest.reportedFirmwareVersion,
                                                         readAt: lastBackup.manifest.createdAt))
                }
                deviceMessage = "Backup verified and saved."
            } catch {
                errorMessage = error.localizedDescription
                deviceMessage = "Backup stopped. Reconnect the USB cap, then refresh."
            }
            reconnectRequired = (try? await deviceService.reconnectRequired(for: device.id)) ?? true
            busy = false; cancellation = nil; idleAcknowledged = false
            if quitAfterBackup { NSApp.terminate(nil) }
        }
    }
    func cancelBackup() {
        if isUploadingFirmware {
            let alert = NSAlert()
            alert.messageText = "Stop the firmware update?"
            alert.informativeText = "Stopping during programming can leave an incomplete application. You will need to unplug and reconnect, then verify or restore stock from the saved backup."
            alert.addButton(withTitle: "Continue Update"); alert.addButton(withTitle: "Stop Update")
            guard alert.runModal() == .alertSecondButtonReturn else { return }
        }
        cancellation?.cancel()
    }
    func shouldTerminate() -> Bool {
        if busy {
            let alert = NSAlert()
            alert.messageText = "A device operation is running"
            alert.informativeText = "Wait for it to finish, or cancel the USB operation and quit. Cancelling an upload can leave an incomplete application. Reconnect before verification or recovery from the saved backup."
            alert.addButton(withTitle: "Keep Open")
            if cancellation != nil { alert.addButton(withTitle: "Cancel USB Operation and Quit") }
            if alert.runModal() == .alertSecondButtonReturn { quitAfterBackup = true; cancellation?.cancel() }
            return false
        }
        guard isDirty else { return true }
        let alert = NSAlert()
        alert.messageText = "Save your lens changes?"
        alert.informativeText = "Changes are stored on this Mac."
        alert.addButton(withTitle: "Save"); alert.addButton(withTitle: "Discard"); alert.addButton(withTitle: "Cancel")
        switch alert.runModal() {
        case .alertFirstButtonReturn: return save()
        case .alertSecondButtonReturn: return true
        default: return false
        }
    }
}
