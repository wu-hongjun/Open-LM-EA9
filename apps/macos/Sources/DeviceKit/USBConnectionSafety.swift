import Foundation
import Darwin

/// Hardware safety belongs to the user, independently of the selected lens library.
struct USBConnectionSafety: Sendable {
    static var canonicalDirectory: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("org.openlmea9.prototype", isDirectory: true)
    }
    let directory: URL
    var file: URL { directory.appendingPathComponent("usb-reconnect-required.json") }
    func blocked() throws -> Set<UInt64> {
        guard FileManager.default.fileExists(atPath: file.path) else { return [] }
        let handle = try FileHandle(forReadingFrom: file)
        defer { try? handle.close() }
        let data = try handle.read(upToCount: 65_537) ?? Data()
        guard data.count <= 65_536 else { throw DeviceError.failure("USB safety record is too large. No reports were sent.") }
        return try JSONDecoder().decode(Set<UInt64>.self, from: data)
    }
    func writeBlocked(_ ids: Set<UInt64>) throws {
        try DurableFile.write(JSONEncoder().encode(ids), to: file)
    }
    func acquire() throws -> USBOperationLock { try USBOperationLock(directory: directory) }
}

/// A separate app/CLI instance cannot clear another instance's armed marker.
final class USBOperationLock {
    private var descriptor: Int32
    init(directory: URL) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        descriptor = open(directory.appendingPathComponent("usb-operation.lock").path, O_CREAT | O_RDWR | O_CLOEXEC | O_NOFOLLOW, 0o600)
        guard descriptor >= 0 else { throw DeviceError.failure("Cannot open the shared USB operation lock. No reports were sent.") }
        guard flock(descriptor, LOCK_EX | LOCK_NB) == 0 else {
            close(descriptor); descriptor = -1
            throw DeviceError.failure("Another app or CLI instance is using the adapter. No reports were sent.")
        }
    }
    func release() {
        if descriptor >= 0 { flock(descriptor, LOCK_UN); close(descriptor); descriptor = -1 }
    }
    deinit { release() }
}

/// Publish a private file only after synchronizing its contents and directory entry.
enum DurableFile {
    static func write(_ data: Data, to destination: URL) throws {
        let directory = destination.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        let temporary = directory.appendingPathComponent(".ea9-durable-\(UUID().uuidString)")
        let descriptor = open(temporary.path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0o600)
        guard descriptor >= 0 else { throw DeviceError.failure("Cannot create the recovery record.") }
        defer { close(descriptor); unlink(temporary.path) }
        try data.withUnsafeBytes { bytes in
            var offset = 0
            while offset < bytes.count {
                let count = Darwin.write(descriptor, bytes.baseAddress!.advanced(by: offset), bytes.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw DeviceError.failure("Cannot write the recovery record.") }
                offset += count
            }
        }
        guard fcntl(descriptor, F_FULLFSYNC) == 0 else { throw DeviceError.failure("Cannot synchronize the recovery record. USB operation stopped.") }
        guard rename(temporary.path, destination.path) == 0 else { throw DeviceError.failure("Cannot publish the recovery record.") }
        try synchronizeDirectories(from: directory)
    }

    static func synchronizeExisting(_ url: URL) throws {
        let descriptor = open(url.path, O_RDWR | O_CLOEXEC | O_NOFOLLOW)
        guard descriptor >= 0 else { throw DeviceError.failure("Cannot open backup evidence for synchronization.") }
        defer { close(descriptor) }
        guard fcntl(descriptor, F_FULLFSYNC) == 0 else { throw DeviceError.failure("Cannot synchronize backup evidence. No START was sent.") }
    }

    static func synchronizeDirectories(from directory: URL) throws {
        // Include newly created ancestors so an otherwise durable file is reachable.
        var current = directory.resolvingSymlinksInPath().standardizedFileURL
        while true {
            // macOS exposes /var and some home paths through legitimate aliases.
            // Directory synchronization may follow these; data-file opens may not.
            let descriptor = open(current.path, O_RDONLY | O_CLOEXEC)
            guard descriptor >= 0 else { throw DeviceError.failure("Cannot open the recovery directory for synchronization (\(errno)).") }
            let result = fsync(descriptor)
            close(descriptor)
            guard result == 0 else { throw DeviceError.failure("Cannot synchronize the recovery directory. USB operation stopped.") }
            if current.path == "/" { break }
            let parent = current.deletingLastPathComponent()
            if parent.path.isEmpty || parent.path == current.path { break }
            current = parent
        }
    }
}
