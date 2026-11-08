import Foundation
import Testing
import LensCore
@testable import DeviceKit

private func bankDevice(_ id: UInt64 = 500,_ serial: String = "SIMULATED-BANK") -> DeviceIdentity {
    DeviceIdentity(id: id,product: "LM-EA9",manufacturer: "TECHART",serial: serial,location: 0,qualifiedDescriptor: true)
}
private func bankLens(_ id: String = "zeiss-jena-biotar-55-f2") throws -> LensProfile {
    try #require(LensLibrary.seeds().profiles.first { $0.id == id })
}
private final class BankLoader: ReadOnlyTransport,UploadTransport {
    var flash = Data(repeating: 255,count: 0x20000)
    var armed = false,pointer = 0x5000,starts = 0,pages = 0,readsWhileArmed = 0
    var failAt: Int?,cancelAt: Int?,token: CancellationToken?
    var userChange = false,lockChange = false,journalLocked = false
    init() throws {
        flash.replaceSubrange(0x5000..<0xa000,with: try ApplicationImage.wideCameraAperture().data)
        for i in 0..<58 { flash[0x4000+i] = UInt8((i*17+9)%251) }
        flash.replaceSubrange(0x4000..<0x4003,with: [4,6,0])
        for i in 0xa000..<0x10000 { flash[i] = UInt8(i%251) }
    }
    func send(_ report: UploadReport) throws -> Data {
        let bytes = try report.encoded()
        switch report {
        case .start:
            #expect(!armed); armed = true; starts += 1
            flash.replaceSubrange(0x4000..<0x403a,with: bytes[6..<64])
            flash.replaceSubrange(0x403a..<0x4040,with: [0,0,0,0,0x44,0])
        case .page:
            #expect(armed); pages += 1; flash.replaceSubrange(pointer..<(pointer+64),with: bytes); pointer += 64
        }
        if starts+pages == cancelAt { token?.cancel() }
        if starts+pages == failAt { throw DeviceError.failure("Simulated ACK loss after write") }
        return bytes
    }
    func exchange(_ request: ReadOnlyRequest) throws -> Data {
        if armed { readsWhileArmed += 1; throw DeviceError.failure("Forbidden report while armed") }
        switch request {
        case .check:
            var data = try request.encoded(); data.replaceSubrange(6..<9,with: flash[0x4000..<0x4003]); return data
        case .flashBlock(let a): return Data(flash[Int(a)..<(Int(a)+64)])
        case .snapshot(let region):
            var data = Data(repeating: 0,count: 64)
            if region == .deviceID { data.replaceSubrange(0..<4,with: [0x0b,3,1,0x10]) }
            if region == .nvm { data.replaceSubrange(8..<12,with: [0,8,3,0]); data[32] = lockChange ? 0 : 255; data[33] = journalLocked ? 253 : 255 }
            if region == .userRow { data[0] = userChange ? 1 : 7 }
            return data
        }
    }
    func reconnect() { armed = false; pointer = 0x5000; starts = 0; pages = 0; failAt = nil; cancelAt = nil }
}
private struct BankFixture {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent("bank-test-"+UUID().uuidString)
    let loader: BankLoader
    let store: BankStore
    init() throws {
        loader = try BankLoader()
        try FileManager.default.createDirectory(at: folder,withIntermediateDirectories: true)
        store = BankStore(directory: folder,expectedBootHash: digest(Data(loader.flash.prefix(0x4000))))
    }
    func snapshot(_ name: String,_ id: UInt64 = 500,_ serial: String = "SIMULATED-BANK") throws -> VerifiedBackup {
        let url = folder.appendingPathComponent(name)
        _ = try BackupEngine(expectedBootHash: store.expectedBootHash).run(transport: loader,identity: bankDevice(id,serial),
            destination: url,cancellation: CancellationToken(),progress: { _ in })
        return try VerifiedBackup(url: url,device: bankDevice(id,serial),expectedBootHash: store.expectedBootHash)
    }
    func send(_ plan: BankPlan,_ before: VerifiedBackup) throws -> BankTransaction {
        let pending = try BankCoordinator.send(plan: plan,approvedDigest: plan.preview.approvalDigest,before: before,store: store,
            transport: loader,cancellation: CancellationToken(),progress: { _ in })
        return try #require(pending)
    }
    func install() throws -> BankObservation {
        let before = try snapshot("legacy"),plan = try BankPlan.install(before,profile: bankLens())
        let pending = try send(plan,before); loader.reconnect()
        return try BankCoordinator.verify(record: pending,current: snapshot("installed",501),store: store)
    }
    func remove() { try? FileManager.default.removeItem(at: folder) }
}

@Test func bankInstallerMergesOpaqueGapSeedsSelectionAndPreservesRollbackMetadata() throws {
    let f = try BankFixture(); defer { f.remove() }
    let before = try f.snapshot("before"),plan = try BankPlan.install(before,profile: bankLens("contax-zeiss-50-f1-4"))
    #expect(plan.image.count == 0xf000 && plan.version == [4,8,0])
    #expect(plan.image[(0xa000-0x5000)..<(0x10000-0x5000)] == before.flash[0xa000..<0x10000])
    #expect(plan.metadata[3..<32] == before.flash[0x4003..<0x4020])
    #expect(plan.metadata[32..<58] != before.flash[0x4020..<0x403a])
    let record = try f.send(plan,before)
    #expect(f.loader.starts == 1 && f.loader.pages == 960 && f.loader.pointer == 0x14000 && f.loader.readsWhileArmed == 0)
    #expect(throws: DeviceError.self) { try f.store.requireNoPending() }
    f.loader.reconnect()
    let current = try f.snapshot("current",501)
    let read = try BankCoordinator.verify(record: record,current: current,store: f.store)
    #expect(read.state?.configured.id == "contax-zeiss-50-f1-4" && read.state?.pendingCameraBoot == false)
    #expect(read.state?.setting.generation == 1) // first boot will not program settings
    #expect(try f.store.qualified(device: bankDevice(501)) == false)
    #expect(try f.store.installationSource(device: bankDevice(501)).flash == before.flash)
    #expect(try f.store.latestRead()?.state == read.state)
    #expect(throws: DeviceError.self) { _ = try BankPlan.install(current,profile: bankLens()) }
}

@Test func metadataSwitchSendsOneReportVerifiesPendingAndCancelsWithoutReflash() throws {
    let f = try BankFixture(); defer { f.remove() }; _ = try f.install()
    let bank = try ProfileBank(),before = try f.snapshot("select-before",501)
    let target = try bankLens("contax-zeiss-35-f1-4"),plan = try BankPlan.select(before,profile: target)
    let record = try f.send(plan,before)
    #expect(f.loader.starts == 1 && f.loader.pages == 0 && f.loader.pointer == 0x5000 && f.loader.readsWhileArmed == 0)
    #expect(f.loader.flash[0x4040..<0x20000] == before.flash[0x4040..<0x20000])
    f.loader.reconnect()
    let after = try f.snapshot("select-after",502)
    let observed = try BankCoordinator.verify(record: record,current: after,store: f.store)
    #expect(observed.state?.pendingCameraBoot == true && observed.state?.committed.id == "zeiss-jena-biotar-55-f2")
    #expect(observed.state?.configured.id == target.id)
    #expect(try f.store.qualified(device: bankDevice(502)))
    #expect(try f.store.qualified(device: bankDevice(502,"OTHER-UNIT")) == false)
    let noop = try BankPlan.select(after,profile: target)
    #expect(!noop.requiresWrite && noop.image.isEmpty)
    let cancelled = try BankPlan.select(after,profile: bankLens())
    #expect(cancelled.requiresWrite)
    #expect(try bank.decodeMailbox(cancelled.metadata).generation == 3)
    // Simulate exactly the journal record the application would commit on camera boot.
    f.loader.flash.replaceSubrange(0x13100..<0x13140,with: try bank.setting(slot: 1,sequence: 2,generation: 2))
    let consumed = try bank.inspect(flash: f.snapshot("consumed",503).flash)
    #expect(!consumed.pendingCameraBoot && consumed.committed.id == target.id)
}

@Test func migrationRefusesOccupiedOrModifiedSourcesAndMissingBankLens() throws {
    let f = try BankFixture(); defer { f.remove() }
    f.loader.flash[0x10004] = 0
    #expect(throws: DeviceError.self) { _ = try BankPlan.install(f.snapshot("occupied"),profile: bankLens()) }
    f.loader.flash[0x10004] = 255; f.loader.flash[0x500c] ^= 1
    #expect(throws: DeviceError.self) { _ = try BankPlan.install(f.snapshot("modified"),profile: bankLens()) }
    #expect(f.loader.starts == 0)
    var lens = try bankLens(); lens.displayName = "Edited Biotar"
    #expect(throws: DeviceError.self) { _ = try ProfileBank().slot(for: lens) }
    #expect(throws: DeviceError.self) { _ = try ProfileBank().slot(for: bankLens("contax-zeiss-28-70-f3-5")) }
    lens = try bankLens(); lens.revision += 1
    #expect(try ProfileBank().slot(for: lens) == 6) // note-only/local revision changes do not require a bank update
}

@Test func originalStockIsAnAdmittedMigrationSourceOnlyWhenItsCodeMatches() throws {
    let f = try BankFixture(); defer { f.remove() }
    var root = URL(fileURLWithPath: #filePath)
    for _ in 0..<5 { root.deleteLastPathComponent() }
    let stock = try Data(contentsOf: root.appendingPathComponent("firmware/recovery/stock-1.8.0/application.bin"))
    f.loader.flash.replaceSubrange(0x5000..<0xa000,with: stock+Data(repeating: 255,count: 0x5000-stock.count))
    f.loader.flash.replaceSubrange(0x4000..<0x4003,with: [1,8,0])
    let source = try f.snapshot("stock")
    #expect(try BankPlan.install(source,profile: bankLens()).image.count == 0xf000)
    f.loader.flash[0x5010] ^= 1
    #expect(throws: DeviceError.self) { _ = try BankPlan.install(f.snapshot("changed-stock"),profile: bankLens()) }
    #expect(f.loader.starts == 0)
}

@Test func bankSelectionLostAckKeepsDurableIntentAndNeverRetriesOrReads() throws {
    let f = try BankFixture(); defer { f.remove() }; _ = try f.install()
    let before = try f.snapshot("lost-before",501),plan = try BankPlan.select(before,profile: bankLens("contax-zeiss-50-f1-4"))
    f.loader.failAt = 1
    #expect(throws: DeviceError.self) { _ = try f.send(plan,before) }
    let pending = try #require(try f.store.load())
    #expect(pending.sentAt == nil && pending.needsVerification && f.loader.starts == 1 && f.loader.pages == 0)
    #expect(f.loader.readsWhileArmed == 0)
    f.loader.reconnect()
    let after = try f.snapshot("lost-after",502)
    _ = try BankCoordinator.verify(record: pending,current: after,store: f.store)
    #expect(try f.store.qualified(device: bankDevice(502)))
}

@Test func staleApprovalAndCancellationPublishNoWriteAndPartialInstallStaysUnverified() throws {
    let f = try BankFixture(); defer { f.remove() }
    let before = try f.snapshot("before"),plan = try BankPlan.install(before,profile: bankLens())
    #expect(throws: DeviceError.self) {
        _ = try BankCoordinator.send(plan: plan,approvedDigest: String(repeating: "0",count: 64),before: before,
            store: f.store,transport: f.loader,cancellation: CancellationToken(),progress: { _ in })
    }
    let token = CancellationToken(); token.cancel()
    #expect(throws: (any Error).self) {
        _ = try BankCoordinator.send(plan: plan,approvedDigest: plan.preview.approvalDigest,before: before,
            store: f.store,transport: f.loader,cancellation: token,progress: { _ in })
    }
    #expect(f.loader.starts == 0)
    #expect(try f.store.load() == nil)
    f.loader.failAt = 20
    #expect(throws: DeviceError.self) { _ = try f.send(plan,before) }
    let record = try #require(try f.store.load()); f.loader.reconnect()
    #expect(throws: DeviceError.self) { _ = try BankCoordinator.verify(record: record,current: f.snapshot("partial",501),store: f.store) }
    #expect(try f.store.load()?.needsVerification == true)
}

@Test func strictVerificationRejectsEveryRegionTamperingAuxChangesAndSameConnection() throws {
    let f = try BankFixture(); defer { f.remove() }; _ = try f.install()
    let before = try f.snapshot("before",501),plan = try BankPlan.select(before,profile: bankLens("contax-zeiss-50-f1-4"))
    let record = try f.send(plan,before); f.loader.reconnect(); let good = f.loader.flash
    #expect(throws: DeviceError.self) { _ = try BankCoordinator.verify(record: record,current: f.snapshot("same-id",501),store: f.store) }
    for offset in [0x100,0x4010,0x4024,0x4042,0x4100,0x5abc,0xa111,0x10030,0x12020,0x13000,0x14000,0x1ffff] {
        f.loader.flash = good; f.loader.flash[offset] ^= 1
        // Boot damage is rejected by the backup engine itself.
        #expect(throws: (any Error).self) {
            _ = try BankCoordinator.verify(record: record,current: f.snapshot("damaged-\(offset)",502),store: f.store)
        }
    }
    f.loader.flash = good; f.loader.userChange = true
    #expect(throws: DeviceError.self) { _ = try BankCoordinator.verify(record: record,current: f.snapshot("aux",502),store: f.store) }
    f.loader.userChange = false; f.loader.lockChange = true
    #expect(throws: DeviceError.self) { _ = try BankCoordinator.verify(record: record,current: f.snapshot("lock",502),store: f.store) }
    #expect(try f.store.load()?.needsVerification == true)
}

@Test func preBankRollbackRestoresFullOriginalUpperFlashAndOpaqueMetadata() throws {
    let f = try BankFixture(); defer { f.remove() }; _ = try f.install()
    let original = try f.store.installationSource(device: bankDevice(501))
    let before = try f.snapshot("rollback-before",501),plan = try BankPlan.rollback(before,installationSource: original)
    #expect(plan.image.count == 0x1b000 && plan.metadata == original.flash[0x4000..<0x403a])
    let record = try f.send(plan,before); f.loader.reconnect()
    let after = try f.snapshot("rollback-after",502)
    let observed = try BankCoordinator.verify(record: record,current: after,store: f.store)
    #expect(observed.version == "4.6.0" && observed.state == nil)
    #expect(after.flash[0x4040..<0x20000] == original.flash[0x4040..<0x20000])
    #expect(after.flash[0x4000..<0x403a] == original.flash[0x4000..<0x403a])
    #expect(f.loader.readsWhileArmed == 0)
}

@Test func bankHistoryTamperingCannotQualifyOrResumeAWrite() throws {
    let f = try BankFixture(); defer { f.remove() }
    let before = try f.snapshot("before"),plan = try BankPlan.install(before,profile: bankLens())
    _ = try f.send(plan,before)
    let original = try #require(JSONSerialization.jsonObject(with: Data(contentsOf: f.store.pendingFile)) as? [String: Any])
    var object = original
    object["slot"] = 2
    try JSONSerialization.data(withJSONObject: object).write(to: f.store.pendingFile)
    #expect(throws: DeviceError.self) { _ = try f.store.load() }
    #expect(throws: DeviceError.self) { try f.store.requireNoPending() }
    #expect(FileManager.default.fileExists(atPath: f.store.pendingFile.path))
    object = original; object["schemaVersion"] = 2
    try JSONSerialization.data(withJSONObject: object).write(to: f.store.pendingFile)
    #expect(throws: DeviceError.self) { _ = try f.store.load() }
    object = original
    var wrongConnection = try #require(object["device"] as? [String: Any]); wrongConnection["id"] = 501
    object["device"] = wrongConnection
    try JSONSerialization.data(withJSONObject: object).write(to: f.store.pendingFile)
    #expect(throws: DeviceError.self) { _ = try f.store.load() }
}

@Test func bankWriteReadinessAndSnapshotBindingFailBeforeStart() throws {
    let f = try BankFixture(); defer { f.remove() }
    f.loader.journalLocked = true
    #expect(throws: DeviceError.self) { _ = try BankPlan.install(f.snapshot("locked"),profile: bankLens()) }
    f.loader.journalLocked = false
    let before = try f.snapshot("before"),plan = try BankPlan.install(before,profile: bankLens())
    let reconnected = try f.snapshot("new-connection",501)
    #expect(try BankPlan.install(reconnected,profile: bankLens()).preview.approvalDigest != plan.preview.approvalDigest)
    #expect(throws: DeviceError.self) { _ = try f.send(plan,reconnected) }
    f.loader.userChange = true
    let differentAux = try f.snapshot("changed-aux")
    #expect(throws: DeviceError.self) { _ = try f.send(plan,differentAux) }
    #expect(f.loader.starts == 0)
}

@Test func noOpAndForgedVerificationDoNotWriteOrReleasePendingState() throws {
    let f = try BankFixture(); defer { f.remove() }; _ = try f.install()
    let before = try f.snapshot("noop",501),plan = try BankPlan.select(before,profile: bankLens())
    let history = try Data(contentsOf: f.store.pendingFile)
    let result = try BankCoordinator.send(plan: plan,approvedDigest: plan.preview.approvalDigest,before: before,
        store: f.store,transport: f.loader,cancellation: CancellationToken(),progress: { _ in })
    #expect(result == nil && f.loader.starts == 0 && f.loader.pages == 0)
    #expect(try Data(contentsOf: f.store.pendingFile) == history)
    let changed = try BankPlan.select(before,profile: bankLens("contax-zeiss-50-f1-4"))
    let pending = try f.send(changed,before)
    var forged = pending; forged.verifiedAt = Date(); forged.verifiedBackupURL = before.result.url
    try f.store.save(forged)
    #expect(throws: DeviceError.self) { _ = try f.store.load() }
    #expect(throws: DeviceError.self) { try f.store.requireNoPending() }
}

@Test func bankVersionCannotUseLegacyAppliedOrUploadHistory() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: directory) }
    let store = UpdateStore(directory: directory),bank = try ProfileBank()
    try store.saveApplied(AppliedLens(device: bankDevice(),setting: bank.profiles[0],firmwareVersion: "4.8.0",
                                    imageSHA256: String(repeating: "0",count: 64),verifiedAt: Date()))
    #expect(throws: DeviceError.self) { _ = try store.loadApplied() }
    let pending = PendingUpdate(transactionID: UUID(),device: bankDevice(),backupURL: directory,image: bank.application,
        version: [4,8,0],setting: bank.profiles[0],createdAt: Date(),imageSHA256: digest(bank.application),
        expectedMetadata: Data([4,8,0]+[UInt8](repeating: 0,count: 55)))
    try store.save(pending)
    #expect(throws: DeviceError.self) { _ = try store.load() }
}

@Test func experimentalBankWritesRequireExplicitAcknowledgmentBeforeNativeAccess() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: directory) }
    let service = DeviceService(stateDirectory: directory,safety: USBConnectionSafety(directory: directory.appendingPathComponent("safety")))
    try UpdateStore(directory: directory).saveQualification(device: bankDevice(),transactionID: UUID())
    do {
        _ = try await service.performBank(operation: .install,profile: bankLens(),approvedDigest: String(repeating: "0",count: 64),
            experimentalAcknowledged: false,device: bankDevice(),idleAcknowledged: false,
            cancellation: CancellationToken(),progress: { _ in })
        Issue.record("Unacknowledged experimental write was accepted")
    } catch { #expect(error.localizedDescription.contains("separately coordinated experimental test")) }
    #expect(!FileManager.default.fileExists(atPath: directory.appendingPathComponent("bank-transaction.json").path))
}

@Test func nativeMigrationVectorsDefineTheFirmwareStartupContract() throws {
    let f = try BankFixture(); defer { f.remove() }
    let before = try f.snapshot("vectors-before"),plan = try BankPlan.install(before,profile: bankLens("contax-zeiss-50-f1-4"))
    _ = try f.send(plan,before); f.loader.reconnect()
    let after = try f.snapshot("vectors-after",501)
    let selection = try BankPlan.select(after,profile: bankLens("contax-zeiss-35-f1-4")),bank = try ProfileBank()
    #expect(try bank.inspect(flash: after.flash).pendingCameraBoot == false)
    let slot = try bank.decodeMailbox(selection.metadata).slot
    let vectors: [String: String] = ["source": "Synthetic native migration/selection; no real adapter",
        "bankSHA256": digest(bank.bytes),"initialMetadata": plan.metadata.base64EncodedString(),
        "initialJournal": Data(plan.image[(0x13000-0x5000)..<(0x14000-0x5000)]).base64EncodedString(),
        "selectionMetadata": selection.metadata.base64EncodedString(),
        "expectedConsumedSetting": try bank.setting(slot: slot,sequence: 2,generation: 2).base64EncodedString()]
    if let name = ProcessInfo.processInfo.environment["OPENLENSADAPTER_BANK_VECTORS"] {
        let url = URL(fileURLWithPath: name).standardizedFileURL
        guard url.path.contains("/artifacts/private/") else { throw DeviceError.failure("Export test vectors only under artifacts/private.") }
        try JSONSerialization.data(withJSONObject: vectors,options: [.prettyPrinted,.sortedKeys]).write(to: url,options: .withoutOverwriting)
    }
}

@Test func failedSameVersionInspectionArchivesOldBankStateInsteadOfDisplayingIt() throws {
    let f = try BankFixture(); defer { f.remove() }; _ = try f.install()
    #expect(try f.store.latestRead()?.state != nil)
    f.loader.flash[0x500c] ^= 1
    let damaged = try f.snapshot("failed-inspection",501)
    #expect(throws: DeviceError.self) { _ = try LensInspection.publish(damaged,to: UpdateStore(directory: f.folder)) }
    #expect(try f.store.latestRead() == nil)
    let history = try FileManager.default.contentsOfDirectory(at: f.folder.appendingPathComponent("BankReadHistory"),includingPropertiesForKeys: nil)
    #expect(!history.isEmpty)
    #expect(FileManager.default.fileExists(atPath: damaged.result.url.path))
}
