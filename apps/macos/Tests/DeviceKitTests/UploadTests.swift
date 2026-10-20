import Foundation
import Testing
import LensCore
@testable import DeviceKit

private func profile(_ id: String = "contax-zeiss-50-f1-4") throws -> LensProfile {
    try #require(LensLibrary.seeds().profiles.first { $0.id == id })
}
private func device(_ id: UInt64 = 10) -> DeviceIdentity {
    DeviceIdentity(id: id, product: "LM-EA9", manufacturer: "TECHART", serial: "SIMULATED-UPLOAD", location: 0, qualifiedDescriptor: true)
}
private final class Loader: ReadOnlyTransport, UploadTransport {
    var flash = Data(repeating: 0xff, count: 0x20000)
    var armed = false, reports = 0, readsWhileArmed = 0, failAt: Int?, cancelAt: Int?
    var token: CancellationToken?, pointer = 0x5000, userRowChanged = false
    init() { flash.replaceSubrange(0x4000..<0x4003, with: [1,8,0]) }
    func send(_ report: UploadReport) throws -> Data {
        reports += 1
        let data = try report.encoded()
        switch report {
        case .start:
            #expect(!armed); armed = true
            flash.replaceSubrange(0x4000..<0x403a, with: data[6..<64])
            flash.replaceSubrange(0x403a..<0x4040, with: [0,0,0,0,0x44,0])
        case .page:
            #expect(armed && pointer + 64 <= 0x20000)
            // Model the loader's 256-byte read/erase/rewrite, preserving its neighbors.
            let rowStart = pointer & ~255
            var row = Data(flash[rowStart..<(rowStart+256)])
            row.replaceSubrange((pointer-rowStart)..<(pointer-rowStart+64), with: data)
            flash.replaceSubrange(rowStart..<(rowStart+256), with: row)
            pointer += 64
        }
        if reports == cancelAt { token?.cancel() }
        if reports == failAt { throw DeviceError.failure("Simulated lost acknowledgement after a write") }
        return data
    }
    func exchange(_ request: ReadOnlyRequest) throws -> Data {
        if armed { readsWhileArmed += 1; throw DeviceError.failure("A read would overwrite the next page") }
        switch request {
        case .check:
            var reply = try request.encoded(); reply.replaceSubrange(6..<9, with: flash[0x4000..<0x4003]); return reply
        case .flashBlock(let address): return Data(flash[Int(address)..<(Int(address)+64)])
        case .snapshot(let snapshot):
            var reply = Data(repeating: 0, count: 64)
            if snapshot == .deviceID { reply.replaceSubrange(0..<4, with: [0x0b,3,1,0x10]) }
            if snapshot == .nvm { reply.replaceSubrange(8..<12, with: [0,8,3,0]) }
            if snapshot == .userRow { reply[0] = userRowChanged ? 6 : 7 }
            return reply
        }
    }
}

@Test func profilesEncodeKnownAperturesFocalLengthsAndRoundTrip() throws {
    for p in try LensLibrary.seeds().profiles where p.kind != .zoom {
        let setting = try AdapterLensSetting(profile: p)
        #expect(try AdapterLensSetting.decode(setting.encoded()) == setting)
        #expect(setting.focalLengthMM == p.minimumFocalLengthMM)
        #expect(setting.apertureLabel == p.maximumAperture.formatted())
        let data = try FirmwareImageBuilder.prepare(profile: p)
        #expect(data.count == 20736)
        #expect(try AdapterLensSetting.decode(Data(data.suffix(256))) == setting)
    }
    #expect(try AdapterLensSetting(profile: profile()).reportedAV == 4352) // f/1.4 nominal -> one stop
    #expect(try AdapterLensSetting(profile: profile("contax-zeiss-28-f2")).reportedAV == 4608)
}

@Test func profileRejectsCorruptionUnsupportedStringsZoomAndPrecision() throws {
    let setting = try AdapterLensSetting(profile: profile())
    var bytes = try setting.encoded(); bytes[12] ^= 1
    #expect(throws: DeviceError.self) { try AdapterLensSetting.decode(bytes) }
    var p = try profile(); p.displayName = "Lens 🥨"
    #expect(throws: DeviceError.self) { try AdapterLensSetting(profile: p) }
    p = try profile(); p.minimumFocalLengthMM = 50.01; p.maximumFocalLengthMM = 50.01
    #expect(throws: DeviceError.self) { try AdapterLensSetting(profile: p) }
    let zoom = try #require(LensLibrary.seeds().profiles.first { $0.kind == .zoom })
    #expect(throws: DeviceError.self) { try AdapterLensSetting(profile: zoom) }
    var selectedZoom = zoom; selectedZoom.activeFocalLengthMM = 70
    #expect(try AdapterLensSetting(profile: selectedZoom).focalMM10 == 700)
    p = try profile(); p.currentAperture = 5.6
    #expect(try AdapterLensSetting(profile: p).reportedAV == 5376)
}

@Test func savedCameraApertureNeverBecomesPhysicalAperture() throws {
    var p = try profile()
    let open = try AdapterLensSetting(profile: p)
    #expect(open.apertureLabel == "1.4" && open.actualAperture == nil)
    p.currentAperture = 4
    let stoppedDownMetadata = try AdapterLensSetting(profile: p)
    #expect(stoppedDownMetadata.apertureLabel == "4")
    let readBack = try AdapterLensSetting.decode(stoppedDownMetadata.encoded())
    #expect(readBack.actualAperture == nil && readBack.actualApertureLabel == "Unknown")
    #expect(readBack.maximumAV == open.maximumAV && readBack.reportedAV != open.reportedAV)
}

@Test func sessionRejectsReadsAndRepeatedStartOnceArmed() throws {
    var phase = USBSessionPhase()
    #expect(throws: DeviceError.self) { try phase.prepare(.page(Data(repeating: 0, count: 64))) }
    try phase.requireIdle()
    try phase.prepare(.start(metadata: Data(repeating: 0, count: 58), version: [2,0,0]))
    #expect(phase.armed)
    #expect(throws: DeviceError.self) { try phase.requireIdle() }
    #expect(throws: DeviceError.self) { try phase.prepare(.start(metadata: Data(repeating: 0, count: 58), version: [2,0,0])) }
    try phase.prepare(.page(Data(repeating: 0, count: 64)))
}

@Test(arguments: FirmwareVariant.allCases) func uploadWritesExactBoundedImageAndNeverSendsPostUploadCommands(variant: FirmwareVariant) throws {
    let loader = Loader(), image = try ApplicationImage.personalized(profile(), variant: variant)
    let before = loader.flash
    try UploadEngine().run(transport: loader, image: image, metadata: Data(before[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    #expect(loader.reports == 1 + variant.applicationBytes/64 && loader.readsWhileArmed == 0 && loader.armed)
    #expect(loader.pointer == variant.applicationEnd)
    #expect(loader.flash[ApplicationImage.base..<variant.applicationEnd] == image.data)
    #expect(loader.flash.prefix(0x4000) == before.prefix(0x4000))
    #expect(loader.flash[0x4040..<0x5000] == before[0x4040..<0x5000])
    #expect(loader.flash[variant.applicationEnd...] == before[variant.applicationEnd...])
    #expect(loader.flash[0x4000..<0x4003] == Data(image.version))
}

@Test(arguments: FirmwareVariant.allCases) func uploadStopsAtLostAcknowledgementOrCancellationWithoutRetry(variant: FirmwareVariant) throws {
    let image = try ApplicationImage.personalized(profile(), variant: variant)
    let loader = Loader(); loader.failAt = 9
    #expect(throws: DeviceError.self) {
        try UploadEngine().run(transport: loader, image: image, metadata: Data(loader.flash[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    }
    #expect(loader.reports == 9 && loader.armed && loader.readsWhileArmed == 0)
    let cancelled = Loader(), token = CancellationToken(); cancelled.cancelAt = 12; cancelled.token = token
    #expect(throws: DeviceError.self) {
        try UploadEngine().run(transport: cancelled, image: image, metadata: Data(cancelled.flash[0x4000..<0x403a]), cancellation: token, progress: { _ in })
    }
    #expect(cancelled.reports == 12 && cancelled.armed && cancelled.readsWhileArmed == 0)
    let invalid = ApplicationImage(data: Data(repeating: 0, count: 0x1b100), version: image.version, setting: nil)
    let unopened = Loader()
    #expect(throws: DeviceError.self) { try UploadEngine().run(transport: unopened, image: invalid, metadata: Data(repeating: 0, count: 58), cancellation: CancellationToken(), progress: { _ in }) }
    #expect(unopened.reports == 0)
}

@Test(arguments: [FirmwareVariant.autofocusReconciled, .autofocusHardened])
func reconciledLayoutStopsBeforeRetainedFactoryRegionAndIgnoresLegacyProfile(variant: FirmwareVariant) throws {
    let loader = Loader()
    // Synthetic retained header/copy bytes, deliberately non-FF. Never embed unit data.
    let retained = Data((0..<0x5080).map { UInt8(truncatingIfNeeded: $0 * 17 + 3) })
    loader.flash.replaceSubrange(0xa000..<0xf080, with: retained)
    let image = try ApplicationImage.personalized(profile("contax-zeiss-85-f1-4"), variant: variant)
    #expect(image.data.count == 20480 && variant.profileAddress == 0x9f00)
    try UploadEngine().run(transport: loader, image: image, metadata: Data(loader.flash[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    #expect(loader.pointer == 0xa000 && loader.reports == 321 && loader.readsWhileArmed == 0)
    #expect(loader.flash[0xa000..<0xf080] == retained)
    #expect(try ApplicationImage.installedVariant(loader.flash) == variant)
    #expect(try ApplicationImage.installedSetting(loader.flash)?.id == "contax-zeiss-85-f1-4")
    // An older installation may leave its different lens at a000. Newer variants decode 9f00.
    let legacy = try ApplicationImage.personalized(profile(), variant: .autofocusExperimental)
    loader.flash.replaceSubrange(0xa000..<0xa100, with: legacy.data.suffix(256))
    #expect(try ApplicationImage.installedSetting(loader.flash)?.id == "contax-zeiss-85-f1-4")
    #expect(try ApplicationImage.template(.autofocusExperimental).count == 20736)
    #expect(try ApplicationImage.template(.metadataOnly).count == 20736)
}

@Test func stockSizedUploadEndsAtLastFlashByteWithoutExtraPadding() throws {
    let loader = Loader()
    let data = Data(repeating: 0x33, count: 0x1b000)
    let image = ApplicationImage(data: data, version: [1,8,0], setting: nil)
    try UploadEngine().run(transport: loader, image: image, metadata: Data(loader.flash[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    #expect(loader.pointer == 0x20000 && loader.reports == 1729)
    #expect(loader.flash[0x5000...] == data && loader.readsWhileArmed == 0)
}

@Test func unqualifiedApplyAndSameConnectionVerificationStopBeforeNativeAccess() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: directory) }
    let service = DeviceService(stateDirectory: directory)
    await #expect(throws: DeviceError.self) {
        try await service.apply(profile: profile(), device: device(), idleAcknowledged: true, cancellation: CancellationToken(), progress: { _ in })
    }
    #expect(!FileManager.default.fileExists(atPath: directory.path))
    let image = try ApplicationImage.personalized(profile())
    var metadata = Data(repeating: 0, count: 58); metadata.replaceSubrange(0..<3, with: [2,0,0])
    let pending = PendingUpdate(transactionID: UUID(), device: device(), backupURL: directory.appendingPathComponent("missing"),
                                image: image.data, version: [2,0,0], setting: image.setting, createdAt: Date(), uploadedAt: Date(),
                                verifiedAt: nil, imageSHA256: digest(image.data), expectedMetadata: metadata)
    try UpdateStore(directory: directory).save(pending)
    await #expect(throws: DeviceError.self) {
        try await service.verifyUpdate(device: device(), idleAcknowledged: true, cancellation: CancellationToken(), progress: { _ in })
    }
    #expect(!FileManager.default.fileExists(atPath: directory.appendingPathComponent("usb-reconnect-required.json").path))
    #expect(try service.pendingUpdate()?.needsVerification == true)
}

@Test func stockUploadQualificationIsBoundToUnitAndLoader() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: directory) }
    let store = UpdateStore(directory: directory)
    #expect(try !store.qualified(for: device()))
    try store.saveQualification(device: device(), transactionID: UUID())
    #expect(try store.qualified(for: device(11)))
    var other = device(); other.serial = "DIFFERENT"
    #expect(try !store.qualified(for: other))
    var object = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: store.qualificationFile)) as? [String: Any])
    object["bootCodeSHA256"] = "wrong"
    try JSONSerialization.data(withJSONObject: object).write(to: store.qualificationFile)
    #expect(try !store.qualified(for: device()))
}

private func fixture(_ loader: Loader, _ directory: URL, _ name: String, id: UInt64) throws -> VerifiedBackup {
    let hash = digest(Data(loader.flash.prefix(0x4000)))
    let url = directory.appendingPathComponent(name)
    _ = try BackupEngine(expectedBootHash: hash).run(transport: loader, identity: device(id), destination: url, cancellation: CancellationToken(), progress: { _ in })
    return try VerifiedBackup(url: url, device: device(id), expectedBootHash: hash)
}

@Test func reviewedStockResolutionAcceptsOnlyKnownMotionBytesAndStableFreshEvidence() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader(), store = UpdateStore(directory: directory)
    let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    let stock = try Data(contentsOf: root.appendingPathComponent("firmware/recovery/stock-1.8.0/application.bin"))
    loader.flash.replaceSubrange(0x5000..<(0x5000 + stock.count), with: stock)
    let original = try fixture(loader, directory, "original", id: 10)
    let image = try ApplicationImage.stockRestoration(original)
    let pending = PendingUpdate(transactionID: UUID(), device: device(), backupURL: original.result.url,
        image: image.data, version: image.version, setting: nil, createdAt: Date.distantPast,
        uploadedAt: Date.distantPast, verifiedAt: nil, imageSHA256: digest(image.data),
        expectedMetadata: Data(original.flash[0x4000..<0x403a]))
    try store.save(pending)
    // Each record byte is classified independently; padding/origin/config/flags
    // cannot become a blanket exception for the whole 44-byte record.
    for address in 0x4100..<0x412c {
        loader.flash = original.flash; loader.flash[address] ^= 1
        let reviewed = try fixture(loader, directory, "review-\(address)", id: 11)
        let fresh = try fixture(loader, directory, "fresh-\(address)", id: 12)
        #expect(throws: DeviceError.self) { try VerificationEngine().verify(pending: pending, current: fresh, original: original) }
        if StockRestoreReview.motionRanges.contains(where: { $0.contains(address) }) {
            let resolution = try StockRestoreReview.assess(pending: pending, original: original, reviewed: reviewed, fresh: fresh)
            #expect(resolution.changedMotionAddresses == [address] && !resolution.strictVerificationPassed)
        } else {
            #expect(throws: DeviceError.self) { try StockRestoreReview.assess(pending: pending, original: original, reviewed: reviewed, fresh: fresh) }
        }
    }
    loader.flash = original.flash; loader.flash[0x4100] ^= 1
    let reviewed = try fixture(loader, directory, "reviewed", id: 11)
    let same = try fixture(loader, directory, "same-connection", id: 11)
    #expect(throws: DeviceError.self) { try StockRestoreReview.assess(pending: pending, original: original, reviewed: reviewed, fresh: same) }
    loader.flash[0x4106] ^= 1
    let changedAgain = try fixture(loader, directory, "changed-again", id: 12)
    #expect(throws: DeviceError.self) { try StockRestoreReview.assess(pending: pending, original: original, reviewed: reviewed, fresh: changedAgain) }
    for address in [0x4030,0x4040,0x40ff,0x412c,0x4fff,0x6000,0xa000,0x1ffff] {
        loader.flash = original.flash; loader.flash[0x4100] ^= 1; loader.flash[address] ^= 1
        let bad = try fixture(loader, directory, "outside-review-\(address)", id: 11)
        let fresh = try fixture(loader, directory, "outside-fresh-\(address)", id: 12)
        #expect(throws: DeviceError.self) { try StockRestoreReview.assess(pending: pending, original: original, reviewed: bad, fresh: fresh) }
    }
    loader.flash = reviewed.flash; loader.userRowChanged = true
    let factoryChanged = try fixture(loader, directory, "changed-factory", id: 12)
    #expect(throws: DeviceError.self) { try StockRestoreReview.assess(pending: pending, original: original, reviewed: reviewed, fresh: factoryChanged) }
    loader.userRowChanged = false
    let fresh = try fixture(loader, directory, "accepted-fresh", id: 12)
    let resolution = try StockRestoreReview.assess(pending: pending, original: original, reviewed: reviewed, fresh: fresh)
    try store.closeReviewedStockRestore(pending, resolution: resolution)
    #expect(try store.load() == nil)
    let history = directory.appendingPathComponent("UpdateHistory/\(pending.transactionID).json")
    let retained = try JSONDecoder().decode(PendingUpdate.self, from: Data(contentsOf: history))
    #expect(retained.verifiedAt == nil && retained.image == pending.image && retained.needsVerification)
    let receipts = try FileManager.default.contentsOfDirectory(at: directory.appendingPathComponent("RestoreResolutions"), includingPropertiesForKeys: nil)
    #expect(receipts.count == 1)
    #expect((try FileManager.default.attributesOfItem(atPath: receipts[0].path)[.posixPermissions] as? NSNumber)?.intValue == 0o600)
    #expect(!loader.armed && loader.reports == 0)
}

@Test func inspectionReplacesStaleCustomHistoryWithStockOrUnsupportedReadback() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader(), store = UpdateStore(directory: directory)
    let image = try ApplicationImage.personalized(profile(), variant: .autofocusReconciled)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: image.version)
    loader.flash.replaceSubrange(ApplicationImage.base..<FirmwareVariant.autofocusReconciled.applicationEnd, with: image.data)
    let custom = try fixture(loader, directory, "custom", id: 51)
    #expect(try LensInspection.publish(custom, to: store)?.firmwareVersion == "2.2.0")
    let originalHistory = try Data(contentsOf: store.appliedFile)
    // The committed official application is the same pinned oracle used by REA.
    let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    let stock = try Data(contentsOf: root.appendingPathComponent("firmware/recovery/stock-1.8.0/application.bin"))
    loader.flash.replaceSubrange(ApplicationImage.base..<(ApplicationImage.base + stock.count), with: stock)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [1,8,0])
    let stockRead = try fixture(loader, directory, "stock", id: 52)
    #expect(try LensInspection.publish(stockRead, to: store) == nil)
    #expect(try store.loadApplied() == nil)
    #expect(try FirmwareObservationStore(directory: directory).load()?.version == "1.8.0")
    let archived = try FileManager.default.contentsOfDirectory(at: directory.appendingPathComponent("InspectionHistory"), includingPropertiesForKeys: nil)
    try #require(archived.count == 1)
    let archivedBytes = try Data(contentsOf: archived[0])
    #expect(archivedBytes == originalHistory)
    _ = try #require(try LensInspection.publish(custom, to: store))
    loader.flash.replaceSubrange(0x4000..<0x4003, with: image.version)
    loader.flash[0x6000] ^= 1
    let unsupported = try fixture(loader, directory, "unsupported", id: 53)
    #expect(throws: DeviceError.self) { try LensInspection.publish(unsupported, to: store) }
    #expect(try store.loadApplied() == nil)
    #expect(try FirmwareObservationStore(directory: directory).load()?.version == "2.2.0")
}
@Test(arguments: FirmwareVariant.allCases)
func profileChangeChecksFreshFirmwareInsteadOfCachedVersion(variant: FirmwareVariant) throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader(), image = try ApplicationImage.personalized(profile(), variant: variant)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: image.version)
    loader.flash.replaceSubrange(ApplicationImage.base..<variant.applicationEnd, with: image.data)
    let current = try fixture(loader, directory, "supported", id: 61)
    try ApplicationImage.requirePreservedFirmware(variant, in: current)
    let other = try #require(FirmwareVariant.allCases.first { $0 != variant })
    #expect(throws: DeviceError.self) { try ApplicationImage.requirePreservedFirmware(other, in: current) }
    loader.flash[0x6000] ^= 1 // A version string cannot admit altered code.
    let altered = try fixture(loader, directory, "altered-code", id: 62)
    #expect(throws: DeviceError.self) { try ApplicationImage.requirePreservedFirmware(variant, in: altered) }
    loader.flash[0x6000] ^= 1; loader.flash[variant.supportsLensProfileChanges ? variant.profileAddress + 12 : variant.applicationEnd - 12] ^= 1
    let damaged = try fixture(loader, directory, "damaged-profile", id: 63)
    #expect(throws: DeviceError.self) { try ApplicationImage.requirePreservedFirmware(variant, in: damaged) }
    #expect(loader.reports == 0 && !loader.armed)
}

@Test func firstStockProfileChangeRequiresThePinnedStockImage() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader()
    let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    let stock = try Data(contentsOf: root.appendingPathComponent("firmware/recovery/stock-1.8.0/application.bin"))
    loader.flash.replaceSubrange(ApplicationImage.base..<(ApplicationImage.base + stock.count), with: stock)
    let current = try fixture(loader, directory, "stock", id: 64)
    try ApplicationImage.requirePreservedFirmware(.metadataOnly, in: current)
    #expect(throws: DeviceError.self) { try ApplicationImage.requirePreservedFirmware(.autofocusHardened, in: current) }
    loader.flash[0x6000] ^= 1
    let altered = try fixture(loader, directory, "altered-stock", id: 65)
    #expect(throws: DeviceError.self) { try ApplicationImage.requirePreservedFirmware(.metadataOnly, in: altered) }
    #expect(loader.reports == 0 && !loader.armed)
}

@Test(arguments: FirmwareVariant.allCases) func reconnectVerificationRejectsSameConnectionWrongBytesAndChangedFactoryData(variant: FirmwareVariant) throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader(), image = try ApplicationImage.personalized(profile(), variant: variant)
    let original = try fixture(loader, directory, "original", id: 10)
    var expected = Data(loader.flash[0x4000..<0x403a]); expected.replaceSubrange(0..<3, with: image.version)
    let pending = PendingUpdate(transactionID: UUID(), device: device(), backupURL: original.result.url, image: image.data,
                                version: image.version, setting: image.setting, createdAt: Date(), uploadedAt: nil, verifiedAt: nil,
                                imageSHA256: digest(image.data), expectedMetadata: expected)
    try UploadEngine().run(transport: loader, image: image, metadata: Data(original.flash[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    loader.armed = false
    let same = try fixture(loader, directory, "same", id: 10)
    #expect(throws: DeviceError.self) { try VerificationEngine().verify(pending: pending, current: same, original: original) }
    let current = try fixture(loader, directory, "current", id: 11)
    #expect(try VerificationEngine().verify(pending: pending, current: current, original: original)?.setting == image.setting)
    if [.autofocusStartupDiagnostic, .autofocusUpstreamHardened, .autofocusBoundedUpstream, .autofocusAbsoluteUpstream, .autofocusStartupHandoff, .autofocusTargetedTrace, .autofocusReadiness, .autofocusHomingDiagnostic].contains(variant) {
        loader.flash[0x9c00] = 0
        let nonblankLog = try fixture(loader, directory, "unexpected-log-before-camera", id: 11)
        #expect(throws: DeviceError.self) { try VerificationEngine().verify(pending: pending, current: nonblankLog, original: original) }
        loader.flash[0x9c00] = 0xff
    }
    loader.flash[0x6000] ^= 1
    let badImage = try fixture(loader, directory, "bad-image", id: 11)
    #expect(throws: DeviceError.self) { try VerificationEngine().verify(pending: pending, current: badImage, original: original) }
    loader.flash[0x6000] ^= 1; loader.flash[0xa200] ^= 1
    let outside = try fixture(loader, directory, "outside", id: 11)
    #expect(throws: DeviceError.self) { try VerificationEngine().verify(pending: pending, current: outside, original: original) }
    loader.flash[0xa200] ^= 1; loader.userRowChanged = true
    let factory = try fixture(loader, directory, "factory", id: 11)
    #expect(throws: DeviceError.self) { try VerificationEngine().verify(pending: pending, current: factory, original: original) }
}

@Test(arguments: FirmwareVariant.allCases) func journalSurvivesArmedCrashAndRejectsImageTampering(variant: FirmwareVariant) throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: directory) }
    let store = UpdateStore(directory: directory), image = try ApplicationImage.personalized(profile(), variant: variant)
    var metadata = Data(repeating: 0, count: 58); metadata.replaceSubrange(0..<3, with: image.version)
    let pending = PendingUpdate(transactionID: UUID(), device: device(), backupURL: directory.appendingPathComponent("original.ea9backup"),
                                image: image.data, version: image.version, setting: image.setting, createdAt: Date(), uploadedAt: nil, verifiedAt: nil,
                                imageSHA256: digest(image.data), expectedMetadata: metadata)
    try store.save(pending)
    #expect(try store.load()?.needsVerification == true)
    #expect(try store.load()?.uploadedAt == nil)
    let attrs = try FileManager.default.attributesOfItem(atPath: store.file.path)
    #expect((attrs[.posixPermissions] as? NSNumber)?.intValue == 0o600)
    var object = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: store.file)) as? [String: Any])
    var bytes = image.data; bytes[100] ^= 1; object["image"] = bytes.base64EncodedString()
    object["imageSHA256"] = digest(bytes)
    try JSONSerialization.data(withJSONObject: object).write(to: store.file)
    #expect(throws: DeviceError.self) { try store.load() }
}

@Test func recoveryCanReadUnknownVersionOnlyWithPinnedLoader() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader(); loader.flash[0x4000] = 0xff
    let url = directory.appendingPathComponent("backup")
    let hash = digest(Data(loader.flash.prefix(0x4000)))
    #expect(throws: DeviceError.self) { try BackupEngine(expectedBootHash: hash).run(transport: loader, identity: device(), destination: url, cancellation: CancellationToken(), progress: { _ in }) }
    _ = try BackupEngine(expectedBootHash: hash, allowRecoveryVersion: true).run(transport: loader, identity: device(), destination: url, cancellation: CancellationToken(), progress: { _ in })
    #expect(try VerifiedBackup(url: url, device: device(), expectedBootHash: hash, allowRecoveryVersion: true).result.manifest.reportedFirmwareVersion == "255.8.0")
    #expect(throws: DeviceError.self) { try VerifiedBackup(url: url, device: device(), expectedBootHash: "wrong", allowRecoveryVersion: true) }
}

@Test func afVersionCannotMasqueradeAsMetadataAndHistoryRetainsVersion() throws {
    let image = try ApplicationImage.personalized(profile(), variant: .autofocusExperimental)
    let loader = Loader()
    loader.flash.replaceSubrange(0x5000..<0xa100, with: image.data)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: image.version)
    #expect(try ApplicationImage.installedVariant(loader.flash) == .autofocusExperimental)
    #expect(try ApplicationImage.installedSetting(loader.flash) == image.setting)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,0,0])
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,3,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "2.3.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil) // Version alone cannot admit another image.
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,5,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "2.5.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,6,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "2.6.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,7,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "2.7.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,8,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "2.8.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,9,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "2.9.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,0,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.0.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,1,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.1.0")
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,2,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.2.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,3,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.3.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,4,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.4.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,5,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.5.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,6,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.6.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,7,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.7.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,8,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.8.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,9,0])
    #expect(try qualifiedFirmwareVersion(loader.exchange(.check)) == "3.9.0")
    #expect(try ApplicationImage.installedSetting(loader.flash) == nil)
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [3,10,0])
    #expect(throws: DeviceError.self) { try qualifiedFirmwareVersion(loader.exchange(.check)) }
    loader.flash.replaceSubrange(0x4000..<0x4003, with: [2,10,0])
    #expect(throws: DeviceError.self) { try qualifiedFirmwareVersion(loader.exchange(.check)) }
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: directory) }
    let store = UpdateStore(directory: directory)
    let applied = AppliedLens(device: device(), setting: try #require(image.setting), firmwareVersion: "2.1.0", imageSHA256: digest(image.data), verifiedAt: Date())
    try store.saveApplied(applied)
    #expect(try store.loadApplied()?.firmwareVersion == "2.1.0")
    let history = FirmwareObservationStore(directory: directory)
    try history.save(FirmwareObservation(device: device(), version: "2.1.0"))
    #expect(try history.load()?.version == "2.1.0")
}

@Test func afBackupIsReadableButCannotBeUsedAsOriginalStockSource() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: directory) }
    let loader = Loader(), image = try ApplicationImage.personalized(profile(), variant: .autofocusExperimental)
    let before = try fixture(loader, directory, "stock", id: 10)
    try UploadEngine().run(transport: loader, image: image, metadata: Data(before.flash[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    loader.armed = false
    let af = try fixture(loader, directory, "af", id: 11)
    #expect(af.result.manifest.reportedFirmwareVersion == "2.1.0")
    #expect(throws: DeviceError.self) { try ApplicationImage.stockRestoration(af) }
    // Metadata-only fallback uses the same protected loader and reconnect rules.
    let fallback = try ApplicationImage.personalized(profile())
    loader.pointer = 0x5000
    var expected = Data(af.flash[0x4000..<0x403a]); expected.replaceSubrange(0..<3, with: fallback.version)
    let pending = PendingUpdate(transactionID: UUID(), device: device(11), backupURL: af.result.url, image: fallback.data, version: fallback.version, setting: fallback.setting, createdAt: Date(), uploadedAt: nil, verifiedAt: nil, imageSHA256: digest(fallback.data), expectedMetadata: expected)
    try UploadEngine().run(transport: loader, image: fallback, metadata: Data(af.flash[0x4000..<0x403a]), cancellation: CancellationToken(), progress: { _ in })
    #expect(loader.armed && loader.readsWhileArmed == 0 && loader.pointer == 0xa100)
    loader.armed = false
    let after = try fixture(loader, directory, "fallback", id: 12)
    #expect(try VerificationEngine().verify(pending: pending, current: after, original: af)?.firmwareVersion == "2.0.0")
}

@Test(arguments: [FirmwareVariant.autofocusUpstreamBaseline, .autofocusStartupDiagnostic, .autofocusUpstreamHardened, .autofocusBoundedUpstream, .autofocusAbsoluteUpstream, .autofocusStartupHandoff, .autofocusTargetedTrace, .autofocusReadiness, .autofocusHomingDiagnostic])
func upstreamBaselineIsAFullPinnedImageWithFixedCompiledSettings(variant: FirmwareVariant) throws {
    let image = try ApplicationImage.personalized(profile(), variant: variant)
    #expect(image.data == (try ApplicationImage.template(variant)))
    #expect(image.data.count == 20480 && variant.applicationEnd == 0xa000)
    #expect(!variant.supportsLensProfileChanges)
    #expect(throws: DeviceError.self) { try ApplicationImage.personalized(profile("contax-zeiss-85-f1-4"), variant: variant) }
    var edited = try profile(); edited.currentAperture = 2
    #expect(throws: DeviceError.self) { try ApplicationImage.personalized(edited, variant: variant) }
    edited = try profile(); edited.displayName = "Renamed"
    #expect(throws: DeviceError.self) { try ApplicationImage.personalized(edited, variant: variant) }
    var flash = Data(repeating: 0xff, count: 0x20000)
    flash.replaceSubrange(0x4000..<0x4003, with: image.version)
    flash.replaceSubrange(0x5000..<0xa000, with: image.data)
    #expect(try ApplicationImage.installedSetting(flash) == image.setting)
    flash[0x9ffc] ^= 1
    #expect(try ApplicationImage.installedVariant(flash) == nil)
}
