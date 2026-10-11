import Foundation
import Testing
@testable import DeviceKit

@Test func alternateLibraryDoesNotRelocateHardwareSafety() {
    let first = DeviceService(stateDirectory: URL(fileURLWithPath: "/tmp/ea9-library-one"))
    let second = DeviceService(stateDirectory: URL(fileURLWithPath: "/tmp/ea9-library-two"))
    #expect(first.safety.file == second.safety.file)
    #expect(first.safety.directory == USBConnectionSafety.canonicalDirectory)
}

@Test func blockedConnectionStopsAlternateClientBeforeNativeAccess() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-safety-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    let safety = USBConnectionSafety(directory: directory.appendingPathComponent("shared"))
    try safety.writeBlocked([42])
    let service = DeviceService(stateDirectory: directory.appendingPathComponent("alternate-library"), safety: safety)
    let device = DeviceIdentity(id: 42, product: "LM-EA9", manufacturer: "TECHART", serial: "SIMULATED", location: 0, qualifiedDescriptor: true)
    await #expect(throws: DeviceError.self) {
        try await service.readFirmware(device: device, idleAcknowledged: true, cancellation: CancellationToken())
    }
    #expect(try await service.reconnectRequired(for: 42))
    #expect(try service.pendingUpdate() == nil)
    #expect(try safety.blocked() == [42])
    #expect(!FileManager.default.fileExists(atPath: directory.appendingPathComponent("alternate-library").path))
}

@Test func sharedLockRejectsSecondClientAndReloadsArmedStateAfterRelease() async throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-lock-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    let first = USBConnectionSafety(directory: directory), second = USBConnectionSafety(directory: directory)
    let held = try first.acquire()
    #expect(try second.blocked().isEmpty)
    #expect(throws: DeviceError.self) { try second.acquire() }
    let service = DeviceService(stateDirectory: directory.appendingPathComponent("library"), safety: second)
    let device = DeviceIdentity(id: 43, product: "LM-EA9", manufacturer: "TECHART", serial: "SIMULATED", location: 0, qualifiedDescriptor: true)
    await #expect(throws: DeviceError.self) {
        try await service.readFirmware(device: device, idleAcknowledged: true, cancellation: CancellationToken())
    }
    try first.writeBlocked([43])
    held.release()
    await #expect(throws: DeviceError.self) {
        try await service.readFirmware(device: device, idleAcknowledged: true, cancellation: CancellationToken())
    }
    #expect(try second.blocked() == [43])
    let next = try second.acquire(); next.release()
}

@Test func safetyRecordCorruptionFailsClosedAndDurableReplacementIsPrivate() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-corrupt-safety-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    let safety = USBConnectionSafety(directory: directory)
    try safety.writeBlocked([44])
    let permissions = try FileManager.default.attributesOfItem(atPath: safety.file.path)[.posixPermissions] as? NSNumber
    #expect(permissions?.intValue == 0o600)
    try Data("invalid".utf8).write(to: safety.file)
    #expect(throws: (any Error).self) { try safety.blocked() }
    try safety.writeBlocked([44,45])
    #expect(try safety.blocked() == [44,45])
    #expect(try FileManager.default.contentsOfDirectory(atPath: directory.path) == ["usb-reconnect-required.json"])
}

@Test func stockRecoveryPreservesCorruptJournalAndOptionalHistory() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-recovery-records-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let store = UpdateStore(directory: directory)
    let originals = [store.file, store.appliedFile, store.qualificationFile]
    for original in originals { try Data("corrupt-\(original.lastPathComponent)".utf8).write(to: original) }
    try store.preserveBeforeRecovery()
    let preserved = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        .filter { $0.lastPathComponent.hasPrefix("recovery-source-") }
    #expect(preserved.count == 3)
    for original in originals {
        let copy = try #require(preserved.first { $0.lastPathComponent.hasSuffix(original.lastPathComponent) })
        #expect(try Data(contentsOf: copy) == Data(contentsOf: original))
        #expect((try FileManager.default.attributesOfItem(atPath: copy.path)[.posixPermissions] as? NSNumber)?.intValue == 0o600)
    }
}
