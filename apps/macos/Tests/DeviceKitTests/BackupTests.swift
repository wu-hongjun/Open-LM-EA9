import Foundation
import Testing
@testable import DeviceKit

private final class SimulatedAdapter: ReadOnlyTransport {
    let flash = Data((0..<0x20000).map { UInt8(truncatingIfNeeded: ($0 / 64) ^ $0) })
    var requests = 0
    var firstFlashReads = 0
    var corruptSecondPass = false
    var wrongVersion = false
    var shortReply = false
    var wrongGeometry = false
    var failAt: Int?
    var cancelAt: Int?
    var cancellation: CancellationToken?
    func exchange(_ request: ReadOnlyRequest) throws -> Data {
        requests += 1
        if requests == failAt { throw DeviceError.failure("Simulated timeout") }
        if requests == cancelAt { cancellation?.cancel() }
        if shortReply { return Data(repeating: 0, count: 63) }
        switch request {
        case .check:
            var data = try ReadOnlyRequest.check.encoded()
            data[6] = wrongVersion ? 0 : 1; data[7] = wrongVersion ? 0 : 8
            return data
        case .flashBlock(let address):
            firstFlashReads += 1
            var data = flash.subdata(in: Int(address)..<Int(address) + 64)
            if corruptSecondPass && firstFlashReads > 256 + 2048 && address == 0x5000 { data[0] ^= 1 }
            return data
        case .snapshot(let window):
            var data = Data(repeating: 0, count: 64)
            if window == .deviceID { data.replaceSubrange(0..<4, with: [0x0B, 0x03, 0x01, 0x10]) }
            if window == .nvm { data.replaceSubrange(8..<12, with: wrongGeometry ? [0,0,0,0] : [0,8,3,0]) }
            if window == .userRow { data[0] = 7 }
            if window == .calibration { data[32] = 5 }
            return data
        }
    }
}

private let identity = DeviceIdentity(id: 42, product: "LM-EA9", manufacturer: "TECHART", serial: "SIMULATED", location: 0, qualifiedDescriptor: true)
private func destination() throws -> URL {
    let parent = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-backup-tests-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: parent, withIntermediateDirectories: false)
    return parent.appendingPathComponent("test.ea9backup")
}
private func run(_ adapter: SimulatedAdapter, to url: URL, token: CancellationToken = CancellationToken()) throws -> BackupResult {
    try BackupEngine(expectedBootHash: digest(adapter.flash.prefix(0x4000))).run(transport: adapter, identity: identity,
        destination: url, cancellation: token, progress: { _ in })
}

@Test func commandWhitelistAndGoldenBytes() throws {
    let check = try ReadOnlyRequest.check.encoded()
    #expect(check.count == 64)
    #expect(check.prefix(6) == Data([0x95,0x27,0x68,0x18,2,2]))
    #expect(check.dropFirst(6).allSatisfy { $0 == 0 })
    let read = try ReadOnlyRequest.flashBlock(0x5000).encoded()
    #expect(read.prefix(10) == Data([0x95,0x27,0x68,0x18,3,3,0,0x50,0,0]))
    #expect(try ReadOnlyRequest.snapshot(.deviceID).encoded().subdata(in: 6..<10) == Data([0x18,0x20,0,0x41]))
    for address: UInt32 in [1, 0x20000, UInt32.max, 0x41002010] {
        #expect(throws: DeviceError.self) { try ReadOnlyRequest.flashBlock(address).encoded() }
    }
    _ = try ReadOnlyRequest.flashBlock(0x1FFC0).encoded()
}

@Test func verifiedBackupPublishesCompleteHashedPrivateFiles() throws {
    let url = try destination()
    defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
    let adapter = SimulatedAdapter()
    let result = try run(adapter, to: url)
    #expect(result.manifest.reportExchanges == 4359)
    #expect(result.manifest.flashReadPasses == 2 && !result.manifest.restorationQualified)
    #expect(try Data(contentsOf: url.appendingPathComponent("flash.bin")) == adapter.flash)
    for (name, expected) in result.manifest.files {
        let data = try Data(contentsOf: url.appendingPathComponent(name))
        #expect(data.count == expected.bytes && digest(data) == expected.sha256)
    }
    let permissions = try FileManager.default.attributesOfItem(atPath: url.path)[.posixPermissions] as? NSNumber
    #expect(permissions?.intValue == 0o700)
    let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
    let manifest = try decoder.decode(BackupManifest.self, from: Data(contentsOf: url.appendingPathComponent("manifest.json")))
    #expect(manifest.device.serial == "SIMULATED" && manifest.files.count == 5)
    #expect(try FileManager.default.contentsOfDirectory(atPath: url.deletingLastPathComponent().path) == ["test.ea9backup"])
}

@Test func mismatchingSecondPassNeverPublishes() throws {
    let url = try destination()
    defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
    let adapter = SimulatedAdapter(); adapter.corruptSecondPass = true
    #expect(throws: DeviceError.self) { try run(adapter, to: url) }
    #expect(!FileManager.default.fileExists(atPath: url.path))
    #expect(adapter.requests == 4355)
    #expect(try FileManager.default.contentsOfDirectory(atPath: url.deletingLastPathComponent().path).isEmpty)
}

@Test func qualificationFailsBeforeRegisterOrFurtherReads() throws {
    let url = try destination()
    defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
    let wrongVersion = SimulatedAdapter(); wrongVersion.wrongVersion = true
    #expect(throws: DeviceError.self) { try run(wrongVersion, to: url) }
    #expect(wrongVersion.requests == 1)
    let wrongBoot = SimulatedAdapter()
    #expect(throws: DeviceError.self) {
        try BackupEngine().run(transport: wrongBoot, identity: identity, destination: url, cancellation: CancellationToken(), progress: { _ in })
    }
    #expect(wrongBoot.requests == 257)
    let wrongGeometry = SimulatedAdapter(); wrongGeometry.wrongGeometry = true
    #expect(throws: DeviceError.self) { try run(wrongGeometry, to: url) }
    #expect(wrongGeometry.requests == 259)
}

@Test func timeoutCancellationAndShortReportStopWithoutRetry() throws {
    let url = try destination()
    defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
    let timeout = SimulatedAdapter(); timeout.failAt = 12
    #expect(throws: DeviceError.self) { try run(timeout, to: url) }
    #expect(timeout.requests == 12)
    let short = SimulatedAdapter(); short.shortReply = true
    #expect(throws: DeviceError.self) { try run(short, to: url) }
    #expect(short.requests == 1)
    let token = CancellationToken(), cancelled = SimulatedAdapter()
    cancelled.cancelAt = 10; cancelled.cancellation = token
    #expect(throws: DeviceError.self) { try run(cancelled, to: url, token: token) }
    #expect(cancelled.requests == 10)
    #expect(!FileManager.default.fileExists(atPath: url.path))
}

@Test func existingBackupIsNeverOverwrittenOrAccessedByUSB() throws {
    let url = try destination()
    defer { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
    let prior = Data("preserved".utf8)
    try prior.write(to: url)
    let adapter = SimulatedAdapter()
    #expect(throws: DeviceError.self) { try run(adapter, to: url) }
    #expect(adapter.requests == 0)
    #expect(try Data(contentsOf: url) == prior)
}
