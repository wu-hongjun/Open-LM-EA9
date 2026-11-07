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

@Test @MainActor func verifiedBaselineUsesDeviceHomeAndSeparatesLocalLensSelection() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([71])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first), image = try ApplicationImage.cameraDialAperture()
    let store = UpdateStore(directory: folder)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(image.setting), firmwareVersion: "4.5.0", imageSHA256: digest(image.data), verifiedAt: Date()))
    try store.saveQualification(device: device, transactionID: UUID())
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "4.5.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.selectedTab == .device && model.currentFirmwareVariant == .cameraDialAperture)
    #expect(model.workflowTitle == "Your adapter is ready" && !model.needsWorkflowBanner)
    #expect(model.canInstallWideAperture && !model.canInstallBaseline && !model.canApplyLens)
    let setting = try #require(model.currentAppliedLens?.setting)
    #expect(model.cameraMetadataSummary(setting).contains("startup f/2"))
    #expect(setting.actualAperture == nil)
    model.chooseDeviceLens("contax-zeiss-50-f1-4")
    #expect(model.preparedLensID == "contax-zeiss-50-f1-4" && model.currentAppliedLens?.setting == setting)
    #expect(!model.canApplyLens)
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "1.8.0", readAt: Date().addingTimeInterval(1)))
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens == nil && !model.canInstallWideAperture)
}

@Test @MainActor func wideCandidateAndCorruptHistoryCannotMasqueradeAsWorkingBaseline() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([71])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first), image = try ApplicationImage.wideCameraAperture()
    let store = UpdateStore(directory: folder)
    try store.saveApplied(AppliedLens(device: device, setting: try #require(image.setting), firmwareVersion: "4.6.0", imageSHA256: digest(image.data), verifiedAt: Date()))
    try store.saveQualification(device: device, transactionID: UUID())
    let history = FirmwareObservationStore(directory: folder)
    try history.save(FirmwareObservation(device: device, version: "4.6.0"))
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.currentFirmwareVariant == .wideCameraAperture && model.canInstallBaseline)
    #expect(!model.canInstallWideAperture && model.firmwareBehaviorNote.contains("pending"))
    #expect(model.currentAppliedLens?.setting.maximumAV == 4608) // Nominal Biotar f/2, separate from virtual range.
    #expect(FirmwareVariant.wideCameraAperture.apertureRangeLabel == "f/1.2–f/22")
    let corrupt = Data("{}".utf8); try corrupt.write(to: history.fileURL)
    await model.refreshDevices(silent: true)
    #expect(model.updateStateError != nil && model.currentAppliedLens == nil)
    #expect(!model.canInstallBaseline && !model.canInstallWideAperture)
    #expect(try Data(contentsOf: history.fileURL) == corrupt)
}

@Test @MainActor func previewCannotOpenUSBAndArchivedVersionsOfferNoInstallAction() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([71])
    let model = AppModel(directory: folder, preview: true, inventory: { await fixture.inventory() }, reconnect: { _ in false })
    await model.refreshDevices(silent: true); model.idleAcknowledged = true
    #expect(model.adapterConnected && !model.canReadDevice && !model.canChangeFirmware)
    let device = try #require(model.devices.first)
    try FirmwareObservationStore(directory: folder).save(FirmwareObservation(device: device, version: "4.1.0"))
    await model.refreshDevices(silent: true)
    #expect(model.isArchivedFirmware && model.workflowTitle == "Archived firmware detected")
    #expect(!model.canInstallBaseline && !model.canInstallWideAperture)
}

@Test @MainActor func versionReadIsNotLabelledVerifiedAndNewObservationsHideOlderAppliedData() async throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let fixture = DiscoveryFixture(); await fixture.set([71])
    let model = AppModel(directory: folder, inventory: { await fixture.inventory() }, reconnect: { await fixture.reconnect($0) })
    #expect(model.emptyLensMessage.contains("Connect"))
    await model.refreshDevices(silent: true)
    let device = try #require(model.devices.first)
    let history = FirmwareObservationStore(directory: folder)
    try history.save(FirmwareObservation(device: device, version: "4.5.0"))
    await model.refreshDevices(silent: true)
    #expect(model.firmwareHistoryCaption?.hasPrefix("Read ") == true)
    #expect(model.emptyLensMessage.contains("Read"))
    let image = try ApplicationImage.cameraDialAperture()
    let now = Date()
    try UpdateStore(directory: folder).saveApplied(AppliedLens(device: device, setting: try #require(image.setting), firmwareVersion: "4.5.0", imageSHA256: digest(image.data), verifiedAt: now))
    try history.save(FirmwareObservation(device: device, version: "4.4.0", readAt: now.addingTimeInterval(-10)))
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens?.firmwareVersion == "4.5.0" && model.firmwareHistoryCaption?.hasPrefix("Verified ") == true)
    try history.save(FirmwareObservation(device: device, version: "4.4.0", readAt: now.addingTimeInterval(1)))
    await model.refreshDevices(silent: true)
    #expect(model.currentAppliedLens == nil && model.firmwareHistoryCaption?.hasPrefix("Read ") == true)
    model.busy = true; model.isUploadingFirmware = false; #expect(model.canCancelRead)
    model.isUploadingFirmware = true; #expect(!model.canCancelRead)
}
