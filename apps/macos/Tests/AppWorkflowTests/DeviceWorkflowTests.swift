import Foundation
import Testing
import LensCore
@testable import DeviceKit
@testable import OpenLMEA9

private actor DiscoveryFixture {
    var devices: [DeviceIdentity] = []
    var blocked = false
    var calls = 0
    func set(_ ids: [UInt64], blocked: Bool = false) {
        devices = ids.map { DeviceIdentity(id: $0, product: "LM-EA9", manufacturer: "TECHART", serial: "WORKFLOW-TEST", location: 0, qualifiedDescriptor: true) }
        self.blocked = blocked
    }
    func inventory() -> [DeviceIdentity] { calls += 1; return devices }
    func reconnect(_ id: UInt64) -> Bool { blocked }
}

@Test @MainActor func corruptFirmwareHistoryHidesOldLensUntilRepaired() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([71])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first)
    let profile = try #require(model.library.profiles.first { $0.id == "contax-zeiss-50-f1-4" })
    let image = try ApplicationImage.personalized(profile, variant: .autofocusAuditedAperture)
    let store = UpdateStore(directory: folder)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(image.setting),
        firmwareVersion: "2.6.0", imageSHA256: digest(image.data), verifiedAt: Date()))
    try store.saveQualification(device: device, transactionID: UUID())
    let firmware = FirmwareObservationStore(directory: folder)
    try firmware.save(FirmwareObservation(device: device, version: "2.6.0"))
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.currentAppliedLens != nil && model.canApplyLens)
    let corrupt = Data("{}".utf8)
    try corrupt.write(to: firmware.fileURL)
    await model.refreshDevices(silent: true)
    #expect(model.updateStateError?.contains("Firmware history") == true)
    #expect(model.currentAppliedLens == nil && !model.canApplyLens)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "Review recovery options")
    #expect(try Data(contentsOf: firmware.fileURL) == corrupt) // Refresh preserves evidence.
    try firmware.save(FirmwareObservation(device: device, version: "2.6.0"))
    await model.refreshDevices(silent: true)
    #expect(model.updateStateError == nil && model.currentAppliedLens != nil && model.canApplyLens)
}

@Test @MainActor func hotplugRefreshResetsUSBConsentAndNeverRunsWhileBusy() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture()
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    #expect(model.devices.isEmpty)
    await fixture.set([10])
    await model.refreshDevices(silent: true)
    #expect(model.devices.first?.id == 10 && !model.idleAcknowledged)
    model.idleAcknowledged = true
    await model.refreshDevices(silent: true)
    #expect(model.idleAcknowledged && model.canReadDevice)
    model.busy = true
    await fixture.set([11])
    let calls = await fixture.calls
    await model.refreshDevices(silent: true)
    #expect(await fixture.calls == calls)
    #expect(model.devices.first?.id == 10)
    model.busy = false
    await model.refreshDevices(silent: true)
    #expect(model.devices.first?.id == 11 && !model.idleAcknowledged && !model.canReadDevice)
    model.idleAcknowledged = true
    await fixture.set([11], blocked: true)
    await model.refreshDevices(silent: true)
    #expect(model.reconnectRequired && !model.idleAcknowledged && !model.canReadDevice)
    await fixture.set([])
    await model.refreshDevices(silent: true)
    #expect(model.connectionLabel == "Not connected" && !model.canReadDevice)
}

@Test @MainActor func dropdownPreparesLocallyWithoutApplyingOrDiscardingEdits() throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let model = AppModel(directory: folder, inventory: { [] }, reconnect: { _ in false })
    model.chooseDeviceLens("contax-zeiss-50-f1-4")
    #expect(model.preparedLensID == "contax-zeiss-50-f1-4")
    #expect(model.appliedLens == nil && model.pendingUpdate == nil && !model.canApplyLens)
    #expect(try PreparedLensStore(directory: folder).load(in: model.library) == model.preparedLensID)
    model.busy = true
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(model.preparedLensID == "contax-zeiss-50-f1-4")
    model.busy = false
    model.draft?.name = "Unsaved name"
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(model.isDirty && model.preparedLensID == "contax-zeiss-50-f1-4")
    model.revert()
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(model.preparedLensID == "contax-zeiss-85-f1-4")
    let zoom = try #require(model.library.profiles.first { $0.kind == .zoom })
    model.chooseDeviceLens(zoom.id)
    #expect(model.preparedLensIssue != nil && !model.canApplyLens)
}

@Test @MainActor func refreshSeesLocalVerificationAndKeepsTheInstalledAFVariant() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture()
    await fixture.set([21])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens == nil)
    let device = try #require(model.devices.first)
    let profile = try #require(model.library.profiles.first { $0.id == "contax-zeiss-50-f1-4" })
    let setting = try AdapterLensSetting(profile: profile)
    let journal = UpdateStore(directory: folder)
    for variant in [FirmwareVariant.autofocusExperimental, .autofocusReconciled, .autofocusHardened, .autofocusFactoryBaseline, .autofocusFactoryRefined, .autofocusAuditedAperture, .autofocusPolished, .autofocusObservedMotion, .autofocusServicedCamera, .autofocusArbitratedCamera] {
        let image = try ApplicationImage.personalized(profile, variant: variant)
        try journal.saveApplied(AppliedLens(device: device, setting: setting, firmwareVersion: variant.versionString,
                                           imageSHA256: digest(image.data), verifiedAt: Date()))
        try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: variant.versionString))
        // A CLI publishes new local files while the window is already open.
        await model.refreshDevices(silent: true)
        #expect(model.currentAppliedLens?.firmwareVersion == variant.versionString)
        #expect(model.firmwareObservation?.version == variant.versionString)
        #expect(model.variantForLensChanges == variant && model.usesExperimentalAF)
        model.chooseDeviceLens("contax-zeiss-85-f1-4")
        #expect(model.variantForLensChanges == variant)
    }
    await fixture.set([])
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens == nil && !model.canChangeFirmware)
}

@Test @MainActor func monitoringRefreshesAndCancelsWithoutUSBOperations() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture()
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    let monitor = Task { await model.monitorDevices() }
    for _ in 0..<100 {
        if await fixture.calls > 0 { break }
        try await Task.sleep(for: .milliseconds(10))
    }
    await fixture.set([12])
    for _ in 0..<300 {
        if model.devices.first?.id == 12 { break }
        try await Task.sleep(for: .milliseconds(10))
    }
    #expect(model.devices.first?.id == 12)
    #expect(await fixture.calls >= 2)
    monitor.cancel(); await monitor.value
    let calls = await fixture.calls
    try await Task.sleep(for: .milliseconds(2100))
    #expect(await fixture.calls == calls)
    #expect(!model.idleAcknowledged && model.pendingUpdate == nil && model.appliedLens == nil)
}

@Test @MainActor func missingLensHistoryCannotSilentlyDowngradeKnownAF() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([41])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first)
    try UpdateStore(directory: folder).saveQualification(device: device, transactionID: UUID())
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "2.2.0"))
    await model.refreshDevices(silent: true)
    model.chooseDeviceLens("contax-zeiss-85-f1-4"); model.idleAcknowledged = true
    #expect(model.canReadDevice && model.stockUploadQualified)
    #expect(model.primaryLensAction == .read && model.variantForLensChanges == nil)
    #expect(!model.canApplyLens && model.currentAppliedLens == nil)
    model.applyLens() // Must stop before presenting an upload or reaching native HID.
    #expect(!model.busy && model.pendingUpdate == nil)
    let image = try ApplicationImage.personalized(try #require(model.preparedLens), variant: .autofocusReconciled)
    try UpdateStore(directory: folder).saveApplied(AppliedLens(device: device, setting: try #require(image.setting),
        firmwareVersion: "2.2.0", imageSHA256: digest(image.data), verifiedAt: Date()))
    await model.refreshDevices(silent: true)
    #expect(model.variantForLensChanges == .autofocusReconciled)
    #expect(model.primaryLensAction == .upToDate)
}

@Test @MainActor func newerStockObservationHidesOldAFProfile() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([42])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first)
    let profile = try #require(model.library.profiles.first { $0.id == "contax-zeiss-50-f1-4" })
    let image = try ApplicationImage.personalized(profile, variant: .autofocusReconciled)
    try UpdateStore(directory: folder).saveApplied(AppliedLens(device: device, setting: try #require(image.setting),
        firmwareVersion: "2.2.0", imageSHA256: digest(image.data), verifiedAt: Date().addingTimeInterval(-60)))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "1.8.0"))
    await model.refreshDevices(silent: true)
    #expect(model.appliedLens != nil && model.currentAppliedLens == nil)
    #expect(model.variantForLensChanges == .metadataOnly && !model.usesExperimentalAF)
}

@Test @MainActor func sameSecondVersionHistoryCannotLeaveAStaleLensVisible() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([45])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first)
    let profile = try #require(model.library.profiles.first { $0.id == "contax-zeiss-50-f1-4" })
    let image = try ApplicationImage.personalized(profile, variant: .autofocusReconciled)
    let verified = Date(timeIntervalSince1970: floor(Date().timeIntervalSince1970) - 5 + 0.75)
    try UpdateStore(directory: folder).saveApplied(AppliedLens(device: device, setting: try #require(image.setting),
        firmwareVersion: "2.2.0", imageSHA256: digest(image.data), verifiedAt: verified))
    let history = FirmwareObservationStore(directory: folder)
    try history.save(FirmwareObservation(device: device, version: "1.8.0", readAt: verified.addingTimeInterval(0.1)))
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens == nil)
    // Clearly older observations do not supersede a newer verified image.
    try history.save(FirmwareObservation(device: device, version: "1.8.0", readAt: verified.addingTimeInterval(-2)))
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens?.firmwareVersion == "2.2.0")
    #expect(model.variantForLensChanges == .autofocusReconciled)
}

@Test @MainActor func unfinishedOtherUnitUpdateExplainsTheDisabledVerification() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([43])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    var other = try #require(model.devices.first); other.serial = "OTHER-WORKFLOW-TEST"
    let profile = try #require(model.library.profiles.first { $0.id == "contax-zeiss-50-f1-4" })
    let image = try ApplicationImage.personalized(profile, variant: .autofocusReconciled)
    var metadata = Data(repeating: 0, count: 58); metadata.replaceSubrange(0..<3, with: image.version)
    try UpdateStore(directory: folder).save(PendingUpdate(transactionID: UUID(), device: other,
        backupURL: folder.appendingPathComponent("synthetic-unused.ea9backup"), image: image.data, version: image.version,
        setting: image.setting, createdAt: Date(), uploadedAt: Date(), verifiedAt: nil,
        imageSHA256: digest(image.data), expectedMetadata: metadata))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.waitingForVerification && !model.canVerifyUpdate && !model.pendingBelongsToConnectedAdapter)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "Another adapter has an unfinished update")
    model.performPrimaryLensAction()
    #expect(model.showDeviceTools && !model.busy)
}

@Test @MainActor func workflowExplainsZoomEditsAndReconnect() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([44])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    model.chooseDeviceLens(try #require(model.library.profiles.first { $0.kind == .zoom }).id)
    #expect(model.workflowTitle == "Finish this lens profile" && !model.canApplyLens)
    model.draft?.name = "Unsaved lens edit"
    #expect(model.workflowTitle == "Save your lens edits")
    model.revert(); await fixture.set([44], blocked: true)
    await model.refreshDevices(silent: true)
    #expect(model.workflowTitle == "Reconnect the USB cap" && !model.canPerformPrimaryLensAction)
}

@Test @MainActor func upstreamBaselineKeepsCompiledLensAndDoesNotOfferProfileApply() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([81])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first)
    let profile = try #require(model.library.profiles.first { $0.id == "contax-zeiss-50-f1-4" })
    let image = try ApplicationImage.personalized(profile, variant: .autofocusUpstreamBaseline)
    let store = UpdateStore(directory: folder)
    let failed = try ApplicationImage.personalized(profile, variant: .autofocusArbitratedCamera)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(failed.setting), firmwareVersion: "3.0.0", imageSHA256: digest(failed.data), verifiedAt: Date()))
    try store.saveQualification(device: device, transactionID: UUID())
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.0.0"))
    model.chooseDeviceLens(profile.id)
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.installedCameraFailureHold && !model.canApplyLens)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "AF 3.0 camera testing held")
    #expect(!model.canInstallUpstreamBaseline && model.workflowSymbol == "exclamationmark.triangle.fill")
    #expect(model.canInstallStartupDiagnostic)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(image.setting), firmwareVersion: "3.1.0", imageSHA256: digest(image.data), verifiedAt: Date()))
    try store.saveQualification(device: device, transactionID: UUID())
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.1.0"))
    model.chooseDeviceLens(profile.id)
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(!model.canInstallUpstreamBaseline && model.preparedMatchesApplied)
    #expect(model.installedCameraFailureHold && !model.canApplyLens && model.primaryLensAction == .tools)
    #expect(model.workflowTitle == "AF 3.1 camera testing held")
    #expect(model.workflowDetail.contains("Shutdown worked") && model.firmwareBehaviorNote.contains("shutter-release failure"))
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(model.variantForLensChanges == .autofocusUpstreamBaseline)
    #expect(!model.canApplyLens && !model.canInstallUpstreamBaseline)
    #expect(!model.canInstallStartupDiagnostic)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "AF 3.1 camera testing held")
    #expect(model.currentAppliedLens?.setting.id == profile.id && model.pendingUpdate == nil)
    let diagnostic = try ApplicationImage.personalized(profile, variant: .autofocusStartupDiagnostic)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(diagnostic.setting), firmwareVersion: "3.2.0", imageSHA256: digest(diagnostic.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.2.0"))
    model.chooseDeviceLens(profile.id)
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallStartupDiagnostic)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "Startup diagnostic candidate")
    #expect(model.workflowDetail.contains("read-only backup") && model.firmwareBehaviorNote.contains("unqualified"))
    #expect(model.canInstallHardenedUpstream)
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallHardenedUpstream)
    model.chooseDeviceLens(profile.id)
    let hardened = try ApplicationImage.personalized(profile, variant: .autofocusUpstreamHardened)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(hardened.setting), firmwareVersion: "3.3.0", imageSHA256: digest(hardened.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.3.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallHardenedUpstream)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "Upstream hardening candidate")
    #expect(model.workflowDetail.contains("read-only backup") && model.firmwareBehaviorNote.contains("unqualified"))
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    #expect(model.canInstallBoundedUpstream)
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallBoundedUpstream)
    model.chooseDeviceLens(profile.id)
    let bounded = try ApplicationImage.personalized(profile, variant: .autofocusBoundedUpstream)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(bounded.setting), firmwareVersion: "3.4.0", imageSHA256: digest(bounded.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.4.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallBoundedUpstream)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "Bounded upstream candidate")
    #expect(model.workflowDetail.contains("read-only backup") && model.firmwareBehaviorNote.contains("unqualified"))
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    #expect(model.canInstallAbsoluteUpstream)
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallAbsoluteUpstream)
    model.chooseDeviceLens(profile.id)
    let absolute = try ApplicationImage.personalized(profile, variant: .autofocusAbsoluteUpstream)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(absolute.setting), firmwareVersion: "3.5.0", imageSHA256: digest(absolute.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.5.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallAbsoluteUpstream)
    #expect(model.primaryLensAction == .tools && model.workflowTitle == "Upstream AF candidate")
    #expect(model.workflowDetail.contains("read-only backup") && model.firmwareBehaviorNote.contains("unqualified"))
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    #expect(!model.canInstallStartupHandoff) // Known 3.6 camera failure blocks a new install, too.
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallStartupHandoff)
    model.chooseDeviceLens(profile.id)
    let handoff = try ApplicationImage.personalized(profile, variant: .autofocusStartupHandoff)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(handoff.setting), firmwareVersion: "3.6.0", imageSHA256: digest(handoff.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.6.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallStartupHandoff)
    #expect(model.installedCameraFailureHold && model.workflowTitle == "AF 3.6 camera testing held")
    #expect(model.primaryLensAction == .tools && model.canReadDevice)
    #expect(model.workflowDetail.contains("shutter press") && model.firmwareBehaviorNote.contains("held"))
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    // Both images have failed camera testing. Neither may be offered as a new
    // install, including while another failed image is currently installed.
    #expect(!model.canInstallTargetedTrace && !model.canInstallStartupHandoff && !model.canApplyLens)
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallTargetedTrace)
    model.chooseDeviceLens(profile.id)
    let targeted = try ApplicationImage.personalized(profile, variant: .autofocusTargetedTrace)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(targeted.setting), firmwareVersion: "3.7.0", imageSHA256: digest(targeted.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.7.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallTargetedTrace)
    #expect(model.installedCameraFailureHold && model.primaryLensAction == .tools && model.canReadDevice)
    #expect(model.workflowTitle == "AF 3.7 camera testing held" && model.workflowDetail.contains("freeze"))
    #expect(model.firmwareBehaviorNote.contains("held") && model.firmwareBehaviorNote.contains("Do not retry"))
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    #expect(!model.canInstallReadiness && !model.canInstallTargetedTrace && !model.canApplyLens)
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallReadiness)
    model.chooseDeviceLens(profile.id)
    let readiness = try ApplicationImage.personalized(profile, variant: .autofocusReadiness)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(readiness.setting), firmwareVersion: "3.8.0", imageSHA256: digest(readiness.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.8.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallReadiness)
    #expect(model.installedCameraFailureHold && model.primaryLensAction == .tools && model.canReadDevice)
    #expect(model.workflowTitle == "AF 3.8 camera testing held" && model.workflowDetail.contains("normal shutdown"))
    #expect(model.firmwareBehaviorNote.contains("drive-phase") && model.firmwareBehaviorNote.contains("Do not retry"))
    #expect(!model.canInstallTargetedTrace && !model.canInstallStartupHandoff)
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    // Every failed camera image is held, including installation from another version.
    #expect(!model.canInstallHomingDiagnostic && !model.canInstallReadiness)
    model.idleAcknowledged = false
    #expect(!model.canInstallHomingDiagnostic)
    model.idleAcknowledged = true
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallHomingDiagnostic)
    model.chooseDeviceLens(profile.id)
    let homing = try ApplicationImage.personalized(profile, variant: .autofocusHomingDiagnostic)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(homing.setting), firmwareVersion: "3.9.0", imageSHA256: digest(homing.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "3.9.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallHomingDiagnostic)
    #expect(model.installedCameraFailureHold && model.primaryLensAction == .tools && model.canReadDevice)
    #expect(model.workflowTitle == "AF 3.9 camera testing held")
    #expect(model.workflowDetail.contains("blocked further capture") && model.workflowDetail.contains("normal shutdown"))
    #expect(model.firmwareBehaviorNote.contains("held") && model.firmwareBehaviorNote.contains("Do not retry"))
    #expect(!model.canInstallReadiness && !model.canInstallTargetedTrace && !model.canInstallStartupHandoff)
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    // A new unqualified candidate is explicit, fixed-profile, and consent-gated.
    #expect(model.canInstallReferenceQualified)
    model.idleAcknowledged = false
    #expect(!model.canInstallReferenceQualified)
    model.idleAcknowledged = true
    model.chooseDeviceLens("contax-zeiss-85-f1-4")
    #expect(!model.canInstallReferenceQualified)
    model.chooseDeviceLens(profile.id)
    let reference = try ApplicationImage.personalized(profile, variant: .autofocusReferenceQualified)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(reference.setting), firmwareVersion: "4.0.0", imageSHA256: digest(reference.data), verifiedAt: Date()))
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "4.0.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.preparedMatchesApplied && !model.canApplyLens && !model.canInstallReferenceQualified)
    #expect(!model.installedCameraFailureHold && model.primaryLensAction == .tools)
    #expect(model.workflowTitle == "Reference qualification candidate")
    #expect(model.workflowDetail.contains("unqualified") && model.firmwareBehaviorNote.contains("unqualified"))
    #expect(model.currentAppliedLens?.setting.actualAperture == nil)
    #expect(!model.canInstallHomingDiagnostic && !model.canInstallReadiness && !model.canInstallTargetedTrace)

}
