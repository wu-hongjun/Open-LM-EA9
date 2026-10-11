import Foundation
import CryptoKit

public enum DeviceError: LocalizedError, Sendable {
    case failure(String)
    public var errorDescription: String? { switch self { case .failure(let text): text } }
}

public struct DeviceIdentity: Codable, Equatable, Identifiable, Sendable {
    public var id: UInt64
    public var product: String
    public var manufacturer: String
    public var serial: String
    public var location: UInt32
    public var qualifiedDescriptor: Bool
}

public final class CancellationToken: @unchecked Sendable {
    private let lock = NSLock()
    private var cancelled = false
    public init() {}
    public func cancel() { lock.withLock { cancelled = true } }
    public func check() throws {
        if lock.withLock({ cancelled }) { throw DeviceError.failure("USB operation cancelled. Reconnect the USB cap before another USB operation.") }
    }
}

public struct BackupProgress: Sendable {
    public let phase: String
    public let completed: Int
    public let total: Int
    public var fraction: Double { Double(completed) / Double(max(total, 1)) }
}

public struct BackupManifest: Codable, Sendable {
    public let schemaVersion: Int
    public let applicationVersion: String
    public let createdAt: Date
    public let device: DeviceIdentity
    public let reportedFirmwareVersion: String
    public let chip: String
    public let deviceID: String
    public let flashBytes: Int
    public let flashReadPasses: Int
    public let auxiliaryReadPasses: Int
    public let reportExchanges: Int
    public let bootCodeSHA256: String
    public let files: [String: FileDigest]
    public let scope: String
    public let restorationQualified: Bool
}

public struct FileDigest: Codable, Sendable {
    public let bytes: Int
    public let sha256: String
}

public struct BackupResult: Sendable {
    public let url: URL
    public let manifest: BackupManifest
}

enum Snapshot: UInt32, Sendable {
    // Deliberately starts after DSU's read-sensitive debug mailboxes.
    case deviceID = 0x41002018, nvm = 0x41004000
    case userRow = 0x00804000, calibration = 0x00806000
}

/// Closed set of read-only requests. There is no raw-report or write operation.
enum ReadOnlyRequest: Sendable {
    case check, flashBlock(UInt32), snapshot(Snapshot)
    func encoded() throws -> Data {
        var bytes = [UInt8](repeating: 0, count: 64)
        bytes.replaceSubrange(0..<4, with: [0x95, 0x27, 0x68, 0x18])
        switch self {
        case .check: bytes[4] = 2; bytes[5] = 2
        case .flashBlock(let address):
            guard address % 64 == 0, address <= 0x20000 - 64 else {
                throw DeviceError.failure("Flash READ is outside the qualified aligned 128 KiB range.")
            }
            bytes[4] = 3; bytes[5] = 3
            for index in 0..<4 { bytes[6 + index] = UInt8(truncatingIfNeeded: address >> (8 * index)) }
        case .snapshot(let window):
            bytes[4] = 3; bytes[5] = 3
            for index in 0..<4 { bytes[6 + index] = UInt8(truncatingIfNeeded: window.rawValue >> (8 * index)) }
        }
        return Data(bytes)
    }
}

protocol ReadOnlyTransport {
    func exchange(_ request: ReadOnlyRequest) throws -> Data
}

func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }

func little32(_ data: Data, _ offset: Int) -> UInt32 {
    (0..<4).reduce(0) { $0 | UInt32(data[offset + $1]) << ($1 * 8) }
}

struct BackupEngine {
    static let qualifiedBootHash = "8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895"
    // Internal injection for simulated tests; real service always uses the pinned default.
    var expectedBootHash = Self.qualifiedBootHash
    var allowRecoveryVersion = false

    func run(transport: any ReadOnlyTransport, identity: DeviceIdentity, destination: URL,
             cancellation: CancellationToken, progress: @Sendable (BackupProgress) -> Void) throws -> BackupResult {
        let fm = FileManager.default
        guard !fm.fileExists(atPath: destination.path) else { throw DeviceError.failure("Choose a new backup name. Existing backups are preserved.") }
        guard fm.fileExists(atPath: destination.deletingLastPathComponent().path) else { throw DeviceError.failure("The backup parent folder does not exist.") }
        var exchanges = 0
        func request(_ command: ReadOnlyRequest) throws -> Data {
            try cancellation.check()
            let data = try transport.exchange(command)
            exchanges += 1
            guard data.count == 64 else { throw DeviceError.failure("Unexpected report length. Reconnect the USB cap.") }
            return data
        }
        func flash(_ bytes: Int, phase: String) throws -> Data {
            var data = Data(capacity: bytes)
            for address in stride(from: 0, to: bytes, by: 64) {
                data.append(try request(.flashBlock(UInt32(address))))
                if address % 1024 == 0 { progress(.init(phase: phase, completed: address + 64, total: bytes)) }
            }
            progress(.init(phase: phase, completed: bytes, total: bytes))
            return data
        }
        progress(.init(phase: "Checking adapter", completed: 0, total: 1))
        let check = try request(.check)
        let version = try qualifiedFirmwareVersion(check, allowRecoveryVersion: allowRecoveryVersion)
        let code = try flash(0x4000, phase: "Qualifying bootloader")
        guard digest(code) == expectedBootHash else {
            throw DeviceError.failure("Unrecognized bootloader. Register reads and backup were stopped; this prototype is qualified for the inspected loader only.")
        }
        let did = try request(.snapshot(.deviceID))
        let nvm = try request(.snapshot(.nvm))
        guard little32(did, 0) == 0x1001030B else { throw DeviceError.failure("Unexpected MCU identity. Backup stopped.") }
        let parameter = little32(nvm, 8)
        guard parameter & 0xFFFF == 2048, (parameter >> 16) & 7 == 3 else {
            throw DeviceError.failure("Unexpected flash geometry. Backup stopped.")
        }
        let first = try flash(0x20000, phase: "Reading flash · pass 1 of 2")
        let second = try flash(0x20000, phase: "Verifying flash · pass 2 of 2")
        guard first == second, first.prefix(0x4000) == code else { throw DeviceError.failure("Flash reads did not match. No backup was published.") }
        var files = ["flash.bin": first, "device-id.bin": did, "nvm-status.bin": nvm]
        for (snapshot, name) in [(Snapshot.userRow, "user-row.bin"), (.calibration, "calibration.bin")] {
            let a = try request(.snapshot(snapshot))
            let b = try request(.snapshot(snapshot))
            guard a == b else { throw DeviceError.failure("Auxiliary reads did not match. No backup was published.") }
            files[name] = a
        }
        try cancellation.check()
        progress(.init(phase: "Saving verified backup", completed: 0, total: 1))
        let manifest = BackupManifest(schemaVersion: 1, applicationVersion: "0.7.0-prototype", createdAt: Date(),
            device: identity, reportedFirmwareVersion: version, chip: "ATSAMD21E17A revision D", deviceID: "0x1001030B",
            flashBytes: first.count, flashReadPasses: 2, auxiliaryReadPasses: 2, reportExchanges: exchanges,
            bootCodeSHA256: digest(code), files: files.mapValues { FileDigest(bytes: $0.count, sha256: digest($0)) },
            scope: "Complete main flash; 64-byte user row and AUX1 calibration window. Excludes other factory auxiliary rows, unique-ID words and live lock-state restoration. Register snapshots are bytewise and non-atomic. Contains device serial and unit-specific data; keep private.",
            restorationQualified: false)
        let stage = destination.deletingLastPathComponent().appendingPathComponent(".ea9-partial-\(UUID().uuidString)", isDirectory: true)
        try fm.createDirectory(at: stage, withIntermediateDirectories: false, attributes: [.posixPermissions: 0o700])
        defer { try? fm.removeItem(at: stage) }
        for (name, data) in files {
            let url = stage.appendingPathComponent(name)
            try data.write(to: url, options: .withoutOverwriting)
            try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
            guard try Data(contentsOf: url) == data else { throw DeviceError.failure("Backup disk verification failed.") }
        }
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        let json = try encoder.encode(manifest)
        let manifestURL = stage.appendingPathComponent("manifest.json")
        try json.write(to: manifestURL, options: .withoutOverwriting)
        try fm.setAttributes([.posixPermissions: 0o600], ofItemAtPath: manifestURL.path)
        guard try Data(contentsOf: manifestURL) == json else { throw DeviceError.failure("Manifest disk verification failed.") }
        try cancellation.check()
        // moveItem fails if the destination exists; the completed package appears as one operation.
        try fm.moveItem(at: stage, to: destination)
        progress(.init(phase: "Backup verified", completed: 1, total: 1))
        return BackupResult(url: destination, manifest: manifest)
    }
}
