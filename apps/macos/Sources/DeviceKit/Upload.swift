import Foundation

/// Separate from ReadOnlyRequest so backup code cannot construct a write.
enum UploadReport {
    case start(metadata: Data, version: [UInt8])
    case page(Data)
    func encoded() throws -> Data {
        switch self {
        case .start(let metadata, let version):
            guard metadata.count == 58, version == [1,8,0] || FirmwareVariant.from(version: version) != nil else { throw DeviceError.failure("Invalid START metadata.") }
            var data = Data([0x95,0x27,0x68,0x18,1,1]); data.append(metadata)
            data.replaceSubrange(6..<9, with: version)
            return data
        case .page(let data):
            guard data.count == 64 else { throw DeviceError.failure("Invalid upload page length.") }
            return data
        }
    }
}
protocol UploadTransport { func send(_ report: UploadReport) throws -> Data }

struct USBSessionPhase {
    private(set) var armed = false
    func requireIdle() throws {
        guard !armed else { throw DeviceError.failure("The loader is armed. No read or control report may be sent until physical reconnect.") }
    }
    mutating func prepare(_ report: UploadReport) throws {
        switch report {
        case .start:
            try requireIdle(); armed = true // Before the transport attempts the write.
        case .page:
            guard armed else { throw DeviceError.failure("No upload START was sent.") }
        }
    }
}

struct UploadEngine {
    func run(transport: any UploadTransport, image: ApplicationImage, metadata: Data,
             cancellation: CancellationToken, progress: @Sendable (BackupProgress) -> Void) throws {
        guard image.data.count > 0, image.data.count % 256 == 0,
              image.data.count <= 0x1b000 else { throw DeviceError.failure("Image exceeds the application flash range or row alignment.") }
        try cancellation.check()
        let start = UploadReport.start(metadata: metadata, version: image.version)
        guard try transport.send(start) == start.encoded() else { throw DeviceError.failure("START acknowledgement mismatch. Reconnect before recovery; no retry was sent.") }
        for offset in stride(from: 0, to: image.data.count, by: 64) {
            try cancellation.check()
            let data = Data(image.data[offset..<(offset+64)])
            guard try transport.send(.page(data)) == data else {
                throw DeviceError.failure("Firmware acknowledgement mismatch. Reconnect before recovery; no retry was sent.")
            }
            if offset % 1024 == 0 { progress(.init(phase: "Applying lens to adapter", completed: offset+64, total: image.data.count)) }
        }
        // The loader remains armed. No CHECK, READ, end marker, retry or extra padding.
        progress(.init(phase: "Unplug and reconnect to verify", completed: image.data.count, total: image.data.count))
    }
}

public struct PendingUpdate: Codable, Sendable {
    public let transactionID: UUID
    public let device: DeviceIdentity
    public let backupURL: URL
    public let image: Data
    public let version: [UInt8]
    public let setting: AdapterLensSetting?
    public let createdAt: Date
    public var uploadedAt: Date?
    public var verifiedAt: Date?
    public let imageSHA256: String
    public let expectedMetadata: Data
    public var needsVerification: Bool { verifiedAt == nil }
}

public struct AppliedLens: Codable, Sendable {
    public let device: DeviceIdentity
    public let setting: AdapterLensSetting
    public let firmwareVersion: String
    public let imageSHA256: String
    public let verifiedAt: Date
    public func belongs(to current: DeviceIdentity) -> Bool {
        !device.serial.isEmpty && device.serial == current.serial && current.qualifiedDescriptor
    }
}

struct StockUploadQualification: Codable {
    let serial: String
    let bootCodeSHA256: String
    let transactionID: UUID
    let verifiedAt: Date
}

/// Private journal survives a crash between START and the final acknowledgement.
struct UpdateStore: Sendable {
    let directory: URL
    var file: URL { directory.appendingPathComponent("pending-update.json") }
    var appliedFile: URL { directory.appendingPathComponent("applied-lens.json") }
    var qualificationFile: URL { directory.appendingPathComponent("stock-upload-qualification.json") }
    func qualified(for device: DeviceIdentity) throws -> Bool {
        guard FileManager.default.fileExists(atPath: qualificationFile.path) else { return false }
        let data = try Data(contentsOf: qualificationFile)
        guard data.count <= 4096 else { throw DeviceError.failure("Stock-upload qualification record too large.") }
        let value = try JSONDecoder().decode(StockUploadQualification.self, from: data)
        return !device.serial.isEmpty && value.serial == device.serial && device.qualifiedDescriptor
            && value.bootCodeSHA256 == BackupEngine.qualifiedBootHash && value.verifiedAt <= Date()
    }
    func saveQualification(device: DeviceIdentity, transactionID: UUID) throws {
        try saveJSON(StockUploadQualification(serial: device.serial, bootCodeSHA256: BackupEngine.qualifiedBootHash,
                                             transactionID: transactionID, verifiedAt: Date()), to: qualificationFile)
    }
    func load() throws -> PendingUpdate? {
        guard FileManager.default.fileExists(atPath: file.path) else { return nil }
        let data = try Data(contentsOf: file)
        guard data.count <= 262144 else { throw DeviceError.failure("Update journal exceeds its size limit.") }
        let record = try JSONDecoder().decode(PendingUpdate.self, from: data)
        guard record.image.count > 0, record.image.count % 256 == 0, record.image.count <= 0x1b000,
              digest(record.image) == record.imageSHA256, record.device.qualifiedDescriptor,
              !record.device.serial.isEmpty, record.expectedMetadata.count == 58,
              record.expectedMetadata.prefix(3) == Data(record.version),
              record.version == [1,8,0] || FirmwareVariant.from(version: record.version) != nil else {
            throw DeviceError.failure("Invalid update journal. Preserve it and its backup for recovery.")
        }
        if let variant = FirmwareVariant.from(version: record.version) {
            guard record.image.count == variant.applicationBytes,
                  record.image.prefix(variant.profileOffset) == (try ApplicationImage.template(variant)).prefix(variant.profileOffset),
                  try AdapterLensSetting.decode(Data(record.image.suffix(256))) == record.setting else {
                throw DeviceError.failure("Update journal contains an unrecognized application.")
            }
        } else {
            guard record.setting == nil, record.image.count == 0x1b000,
                  digest(Data(record.image.prefix(20172))) == "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564" else {
                throw DeviceError.failure("Invalid stock restoration journal.")
            }
        }
        return record
    }
    func save(_ record: PendingUpdate) throws {
        let history = directory.appendingPathComponent("UpdateHistory", isDirectory: true)
        try FileManager.default.createDirectory(at: history, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        try saveJSON(record, to: history.appendingPathComponent("\(record.transactionID).json"))
        try saveJSON(record, to: file)
    }
    func saveApplied(_ record: AppliedLens) throws { try saveJSON(record, to: appliedFile) }
    func archiveAppliedBeforeInspection() throws {
        guard FileManager.default.fileExists(atPath: appliedFile.path) else { return }
        let history = directory.appendingPathComponent("InspectionHistory", isDirectory: true)
        try FileManager.default.createDirectory(at: history, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        let archived = history.appendingPathComponent("\(UUID().uuidString)-applied-lens.json")
        try FileManager.default.moveItem(at: appliedFile, to: archived)
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: archived.path)
        try DurableFile.synchronizeExisting(archived)
        try DurableFile.synchronizeDirectories(from: history)
    }
    func preserveBeforeRecovery() throws {
        for source in [file, appliedFile, qualificationFile] where FileManager.default.fileExists(atPath: source.path) {
            let url = directory.appendingPathComponent("recovery-source-\(UUID().uuidString)-\(source.lastPathComponent)")
            try FileManager.default.copyItem(at: source, to: url)
            try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
            try DurableFile.synchronizeExisting(url)
        }
        try DurableFile.synchronizeDirectories(from: directory)
    }
    func loadApplied() throws -> AppliedLens? {
        guard FileManager.default.fileExists(atPath: appliedFile.path) else { return nil }
        let data = try Data(contentsOf: appliedFile)
        guard data.count <= 16384 else { throw DeviceError.failure("Applied-lens history is too large.") }
        let value = try JSONDecoder().decode(AppliedLens.self, from: data)
        _ = try value.setting.encoded()
        guard FirmwareVariant.allCases.contains(where: { $0.versionString == value.firmwareVersion }), value.device.qualifiedDescriptor, !value.device.serial.isEmpty,
              value.imageSHA256.count == 64 else { throw DeviceError.failure("Invalid applied-lens history.") }
        return value
    }
    private func saveJSON<T: Encodable>(_ value: T, to url: URL) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try DurableFile.write(encoder.encode(value), to: url)
    }
}

/// Checks all files, loader and unit identity before using a backup as evidence or restoration input.
struct VerifiedBackup {
    let result: BackupResult
    let flash: Data
    func synchronizeRecoveryEvidence() throws {
        for name in result.manifest.files.keys.sorted() + ["manifest.json"] {
            try DurableFile.synchronizeExisting(result.url.appendingPathComponent(name))
        }
        try DurableFile.synchronizeDirectories(from: result.url)
    }
    init(url: URL, device: DeviceIdentity, expectedBootHash: String = BackupEngine.qualifiedBootHash,
         allowRecoveryVersion: Bool = false) throws {
        let data = try Data(contentsOf: url.appendingPathComponent("manifest.json"))
        guard data.count <= 65536 else { throw DeviceError.failure("Backup manifest too large.") }
        let decoder = JSONDecoder(); decoder.dateDecodingStrategy = .iso8601
        let manifest = try decoder.decode(BackupManifest.self, from: data)
        let names: Set<String> = ["flash.bin","device-id.bin","nvm-status.bin","user-row.bin","calibration.bin"]
        guard manifest.schemaVersion == 1, manifest.flashReadPasses == 2, manifest.auxiliaryReadPasses == 2,
              manifest.flashBytes == 0x20000, manifest.bootCodeSHA256 == expectedBootHash,
              manifest.device.qualifiedDescriptor, !device.serial.isEmpty, manifest.device.serial == device.serial,
              allowRecoveryVersion || manifest.reportedFirmwareVersion == "1.8.0" || FirmwareVariant.allCases.contains(where: { $0.versionString == manifest.reportedFirmwareVersion }),
              Set(manifest.files.keys) == names else { throw DeviceError.failure("Backup format, loader or adapter identity does not match.") }
        for name in names {
            let expected = manifest.files[name]!
            let expectedSize = name == "flash.bin" ? 0x20000 : 64
            guard expected.bytes == expectedSize else { throw DeviceError.failure("Unexpected backup file size.") }
            let file = url.appendingPathComponent(name)
            guard (try FileManager.default.attributesOfItem(atPath: file.path)[.size] as? NSNumber)?.intValue == expectedSize else {
                throw DeviceError.failure("Unexpected backup file size: \(name)")
            }
            let bytes = try Data(contentsOf: file)
            guard bytes.count == expectedSize, digest(bytes) == expected.sha256 else { throw DeviceError.failure("Backup checksum failed: \(name)") }
        }
        flash = try Data(contentsOf: url.appendingPathComponent("flash.bin"))
        let did = try Data(contentsOf: url.appendingPathComponent("device-id.bin"))
        let nvm = try Data(contentsOf: url.appendingPathComponent("nvm-status.bin"))
        let parameter = little32(nvm, 8)
        guard little32(did, 0) == 0x1001030b, parameter & 0xffff == 2048, (parameter >> 16) & 7 == 3 else {
            throw DeviceError.failure("Backup MCU identity or flash geometry is inconsistent.")
        }
        let versionBytes = manifest.reportedFirmwareVersion.split(separator: ".").compactMap { UInt8($0) }
        guard versionBytes.count == 3, digest(Data(flash.prefix(0x4000))) == expectedBootHash,
              flash[0x4000..<0x4003] == Data(versionBytes) else {
            throw DeviceError.failure("Backup loader or version bytes are inconsistent.")
        }
        result = BackupResult(url: url, manifest: manifest)
    }
}

struct VerificationEngine {
    func verify(pending: PendingUpdate, current: VerifiedBackup, original: VerifiedBackup) throws -> AppliedLens? {
        let actual = current.flash, before = original.flash
        guard current.result.manifest.device.id != pending.device.id,
              current.result.manifest.device.serial == pending.device.serial else { throw DeviceError.failure("Unplug and reconnect the same adapter before verifying.") }
        let end = ApplicationImage.base + pending.image.count
        guard actual[ApplicationImage.base..<end] == pending.image else { throw DeviceError.failure("Installed application bytes do not match. Keep the backup and use recovery after reconnecting.") }
        // START rewrites 64 metadata bytes: the final six come from adjacent loader RAM.
        // Preserve and compare every other byte, including the remainder of that flash row.
        guard actual.prefix(0x4000) == before.prefix(0x4000), actual[0x4040..<0x5000] == before[0x4040..<0x5000],
              actual[end..<0x20000] == before[end..<0x20000],
              actual[0x4000..<0x403a] == pending.expectedMetadata else { throw DeviceError.failure("Unexpected flash changes outside the planned application and loader metadata.") }
        for name in ["user-row.bin", "calibration.bin", "device-id.bin"] {
            guard current.result.manifest.files[name]!.sha256 == original.result.manifest.files[name]!.sha256 else {
                throw DeviceError.failure("Factory data changed unexpectedly: \(name)")
            }
        }
        guard let setting = pending.setting else { return nil }
        guard let variant = FirmwareVariant.from(version: pending.version),
              current.result.manifest.reportedFirmwareVersion == variant.versionString,
              try ApplicationImage.installedVariant(actual) == variant,
              try ApplicationImage.installedSetting(actual) == setting else { throw DeviceError.failure("Installed lens profile failed validation.") }
        return AppliedLens(device: current.result.manifest.device, setting: setting, firmwareVersion: variant.versionString,
                           imageSHA256: pending.imageSHA256, verifiedAt: Date())
    }
}
