import Foundation
import AppKit
import LensCore
import DeviceKit

@MainActor extension AppModel {
    var deviceLensSelectionID: String? {
        let id = preparedLensID ?? currentBankState?.configured.id ?? currentAppliedLens?.setting.id
        return library.profiles.contains { $0.id == id } ? id : nil
    }
    var deviceLensPreview: LensProfile? { library.profiles.first { $0.id == deviceLensSelectionID } }
    var canRequestDeviceRead: Bool {
        !isPreview && adapterConnected && !busy && !isRefreshing && !reconnectRequired
    }
    var canRequestVerification: Bool {
        canRequestDeviceRead && updateStateError == nil && waitingForVerification
            && activePendingDevice?.id != devices.first?.id
            && activePendingDevice?.serial == devices.first?.serial
    }
    /// A cached observation is explicitly dated; it never substitutes for readback.
    var adapterFirmwareText: String {
        if waitingForVerification && pendingBelongsToConnectedAdapter {
            if pendingUpdate?.needsVerification != true { return pendingBank?.operation == .rollback ? "Restoring pre-bank firmware" : ProfileBank.version }
            return pendingUpdate?.version.map(String.init).joined(separator: ".") ?? "Awaiting verification"
        }
        return currentBankObservation?.version ?? currentAppliedLens?.firmwareVersion ?? currentFirmwareObservation?.version ?? "Not read"
    }
    var installedProfileText: String {
        if waitingForVerification && pendingBelongsToConnectedAdapter { return "Awaiting verification" }
        if let state = currentBankState { return state.configured.name + (state.pendingCameraBoot ? " · pending camera startup" : "") }
        if currentAppliedLens == nil && currentFirmwareObservation?.version == "1.8.0" {
            return "Stock lens settings are not decoded"
        }
        return currentAppliedLens?.setting.name ?? "Not read"
    }
    var selectedLensState: String {
        guard let preview = deviceLensPreview else { return "Choose a lens" }
        if let state = currentBankState,bankSelectionMatches { return state.pendingCameraBoot ? "Queued for camera" : "Configured · last read" }
        if pendingBank?.needsVerification == true { return "Reconnect and verify" }
        if let pendingUpdate, waitingForVerification, pendingUpdate.setting?.id == preview.id {
            return "Uploaded · verification needed"
        }
        if preparedMatchesApplied || (preparedLensID == nil && currentAppliedLens?.setting.id == preview.id) {
            return "On adapter · last verified"
        }
        return "Selected · not applied"
    }
    var lensActionHint: String {
        if busy { return progress?.phase ?? "Keep the USB cap connected." }
        if !adapterConnected { return "Connect the LM-EA9 through its USB cap to apply this lens." }
        if waitingForVerification || reconnectRequired { return workflowDetail }
        if let issue = preparedLensIssue { return issue }
        if loadError != nil || updateStateError != nil { return "Resolve the saved-data error before applying a profile." }
        if currentAppliedLens == nil && currentFirmwareObservation?.version != "1.8.0" {
            return "Read the adapter to identify its installed profile."
        }
        if !stockUploadQualified { return "Open USB tools to prepare this adapter for lens updates." }
        if preparedMatchesApplied { return "This lens metadata is already on the adapter." }
        if deviceLensPreview == nil { return "Choose the lens you mounted." }
        if currentFirmwareVariant != .lensProfiles {
            return "This cap requires a firmware update to change lenses. 4.7.0 still needs camera testing."
        }
        return "This USB path reflashes firmware per change. Parameter-only switching is not available yet."
    }
    var adapterStateText: String {
        if busy { return isUploadingFirmware ? "Updating" : "Reading" }
        if discoveryError { return "Connection error" }
        if !adapterConnected { return devices.isEmpty ? "Disconnected" : "Check connection" }
        if updateStateError != nil { return "History needs attention" }
        if reconnectRequired { return "Reconnect required" }
        if waitingForVerification { return pendingBelongsToConnectedAdapter ? "Verification needed" : "Another update is pending" }
        if let state = currentBankState { return state.pendingCameraBoot ? "Profile queued" : "Bank identified" }
        if currentAppliedLens == nil && currentFirmwareObservation?.version == "1.8.0" { return "Profile unavailable" }
        return currentAppliedLens != nil ? "Profile identified" : "Read needed"
    }

    private func confirmUSB(title: String, detail: String, action: String) -> Bool {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = detail + "\n\nKeep TECHART Update closed and the LM-EA9 on its reconnected USB cap."
        alert.addButton(withTitle: action); alert.addButton(withTitle: "Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else { return false }
        idleAcknowledged = true
        return true
    }
    func readAdapterFromCard() {
        guard canRequestDeviceRead, updateStateError == nil, !waitingForVerification else { return }
        guard confirmUSB(title: "Read adapter information?", detail: "Two complete reads verify the firmware and installed lens profile. A private backup is saved.", action: "Read") else { return }
        readAdapterLens()
    }
    func verifyFromCard() {
        guard canRequestVerification else { return }
        guard confirmUSB(title: "Verify the uploaded profile?", detail: "Physically unplug and reconnect the cap first. The complete firmware and protected data will be checked before camera use.", action: "Verify") else { return }
        verifyLensUpdate()
    }
    func applyPreparedLens() {
        guard canApplyLens, let profile = preparedLens, let target = devices.first else { return }
        // Materialize and validate the concrete image before asking for a write.
        do { _ = try FirmwareImageBuilder.prepare(profile: profile, variant: .lensProfiles) }
        catch { errorMessage = error.localizedDescription; return }
        let setting: AdapterLensSetting
        do { setting = try AdapterLensSetting(profile: profile) }
        catch { errorMessage = error.localizedDescription; return }
        let upgrade = currentFirmwareVariant == .lensProfiles ? "" :
            "\nThis installs firmware 4.7.0, which still needs camera validation."
        guard confirmUSB(title: "Update firmware for \(profile.displayName)?",
                         detail: "\(setting.focalLengthMM.formatted()) mm · startup f/\(setting.apertureLabel) · Sony dial f/1.2–f/22.\nThis path rewrites the application for each lens change; it is not a parameter-only update. A verified backup is saved first. Reconnect after upload, then verify. The physical iris stays manual." + upgrade,
                         action: "Update Firmware") else { return }
        guard devices.first == target, canApplyLens else {
            idleAcknowledged = false
            errorMessage = "The adapter or update state changed. Read the adapter again before updating."
            return
        }
        runLensOperation(writing: true) { device, token in
            _ = try await self.deviceService.apply(profile: profile, variant: .lensProfiles,
                device: device, idleAcknowledged: self.idleAcknowledged, cancellation: token,
                progress: { update in Task { @MainActor in self.progress = update } })
            self.pendingUpdate = try self.deviceService.pendingUpdate()
            self.deviceMessage = "Upload complete. Unplug and reconnect the USB cap, then verify."
        }
    }
}
