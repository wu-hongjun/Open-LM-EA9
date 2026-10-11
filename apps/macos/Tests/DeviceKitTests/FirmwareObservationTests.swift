import Foundation
import Testing
@testable import DeviceKit

private func testDevice(id: UInt64 = 42, serial: String = "SIMULATED", qualified: Bool = true) -> DeviceIdentity {
    DeviceIdentity(id: id, product: "LM-EA9", manufacturer: "TECHART", serial: serial,
                   location: 0, qualifiedDescriptor: qualified)
}

@Test func firmwareCheckRejectsEchoShortAndUnqualifiedVersion() throws {
    var reply = try ReadOnlyRequest.check.encoded()
    #expect(throws: DeviceError.self) { try qualifiedFirmwareVersion(reply) }
    reply[6] = 1; reply[7] = 8
    #expect(try qualifiedFirmwareVersion(reply) == "1.8.0")
    #expect(throws: DeviceError.self) { try qualifiedFirmwareVersion(reply.dropLast()) }
    reply[7] = 9
    #expect(throws: DeviceError.self) { try qualifiedFirmwareVersion(reply) }
}

@Test func cachedFirmwareFollowsSerialAcrossReconnectAndNeverAnonymousDevices() {
    let observation = FirmwareObservation(device: testDevice(), version: "1.8.0")
    #expect(observation.belongs(to: testDevice(id: 123)))
    #expect(!observation.belongs(to: testDevice(serial: "OTHER")))
    #expect(!observation.belongs(to: testDevice(qualified: false)))
    let anonymous = FirmwareObservation(device: testDevice(serial: ""), version: "1.8.0")
    #expect(!anonymous.belongs(to: testDevice(serial: "")))
}

@Test func firmwareHistoryRoundTripsAndRejectsInvalidOrOversizedRecords() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-firmware-history-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    let store = FirmwareObservationStore(directory: directory)
    #expect(try store.load() == nil)
    let date = Date(timeIntervalSince1970: 1_700_000_000)
    try store.save(FirmwareObservation(device: testDevice(), version: "1.8.0", readAt: date))
    let restored = try #require(try store.load())
    #expect(restored.version == "1.8.0" && restored.readAt == date && restored.device == testDevice())
    let permissions = try FileManager.default.attributesOfItem(atPath: store.fileURL.path)[.posixPermissions] as? NSNumber
    #expect(permissions?.intValue == 0o600)
    #expect(throws: DeviceError.self) { try store.save(FirmwareObservation(device: testDevice(), version: "9.9.9")) }
    #expect(throws: DeviceError.self) {
        try store.save(FirmwareObservation(device: testDevice(), version: "1.8.0", readAt: Date().addingTimeInterval(3_600)))
    }
    let original = try Data(contentsOf: store.fileURL)
    let unsupported = String(decoding: original, as: UTF8.self).replacingOccurrences(of: "\"schemaVersion\" : 1", with: "\"schemaVersion\" : 2")
    #expect(unsupported != String(decoding: original, as: UTF8.self))
    try Data(unsupported.utf8).write(to: store.fileURL)
    #expect(throws: DeviceError.self) { try store.load() }
    try Data(repeating: 0, count: 65_537).write(to: store.fileURL)
    #expect(throws: DeviceError.self) { try store.load() }
}

@Test func unacknowledgedFirmwareReadStopsBeforeNativeAccessOrStateMutation() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-unacknowledged-read-\(UUID().uuidString)")
    let service = DeviceService(stateDirectory: directory)
    await #expect(throws: DeviceError.self) {
        try await service.readFirmware(device: testDevice(), idleAcknowledged: false, cancellation: CancellationToken())
    }
    #expect(!FileManager.default.fileExists(atPath: directory.path))
}
