import Foundation

/// A dated CHECK result, separate from USB descriptor version and installed-image verification.
public struct FirmwareObservation: Codable, Sendable {
    public let device: DeviceIdentity
    public let version: String
    public let readAt: Date
    public init(device: DeviceIdentity, version: String, readAt: Date = Date()) {
        self.device = device; self.version = version; self.readAt = readAt
    }
    public func belongs(to current: DeviceIdentity) -> Bool {
        // Registry IDs change on reconnect. Never associate an anonymous device's cached identity.
        !current.serial.isEmpty && device.serial == current.serial && device.product == current.product
            && device.manufacturer == current.manufacturer && device.qualifiedDescriptor && current.qualifiedDescriptor
    }
}

/// Private, bounded local history. It never substitutes for a new CHECK or loader qualification.
public struct FirmwareObservationStore: Sendable {
    public let fileURL: URL
    private struct Document: Codable { let schemaVersion: Int; let observation: FirmwareObservation }
    public init(directory: URL) { fileURL = directory.appendingPathComponent("last-firmware-observation.json") }
    public func load() throws -> FirmwareObservation? {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return nil }
        let handle = try FileHandle(forReadingFrom: fileURL)
        defer { try? handle.close() }
        let data = try handle.read(upToCount: 65_537) ?? Data()
        guard data.count <= 65_536 else { throw DeviceError.failure("Firmware history is too large.") }
        let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
        let document = try decoder.decode(Document.self, from: data)
        guard document.schemaVersion == 1 else { throw DeviceError.failure("Unsupported firmware history format.") }
        try validate(document.observation)
        return document.observation
    }
    public func save(_ observation: FirmwareObservation) throws {
        try validate(observation)
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(Document(schemaVersion: 1, observation: observation))
        guard data.count <= 65_536 else { throw DeviceError.failure("Firmware history is too large.") }
        try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: fileURL, options: .atomic)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: fileURL.path)
    }
    private func validate(_ observation: FirmwareObservation) throws {
        guard observation.version == "1.8.0" || FirmwareVariant.allCases.contains(where: { $0.versionString == observation.version }), observation.device.qualifiedDescriptor,
              observation.device.product == "LM-EA9", observation.device.manufacturer == "TECHART",
              observation.readAt > Date(timeIntervalSince1970: 0), observation.readAt <= Date().addingTimeInterval(60) else {
            throw DeviceError.failure("Invalid firmware history.")
        }
    }
}

func qualifiedFirmwareVersion(_ reply: Data, allowRecoveryVersion: Bool = false) throws -> String {
    guard reply.count == 64, reply.prefix(6) == Data([0x95, 0x27, 0x68, 0x18, 2, 2]) else {
        throw DeviceError.failure("The adapter did not return an idle CHECK response. Reconnect the USB cap.")
    }
    let version = Array(reply[6..<9])
    guard allowRecoveryVersion || version == [1,8,0] || FirmwareVariant.from(version: version) != nil else {
        throw DeviceError.failure("Unrecognized firmware version. No memory reads were sent. Reconnect the USB cap.")
    }
    return version.map(String.init).joined(separator: ".")
}
