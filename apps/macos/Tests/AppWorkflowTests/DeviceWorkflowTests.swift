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
    for variant in [FirmwareVariant.autofocusExperimental, .autofocusReconciled] {
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
