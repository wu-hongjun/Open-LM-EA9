import Foundation

public struct BankTransaction: Codable, Sendable {
    public var schemaVersion = 1
    public let id: UUID
    public let operation: BankOperation
    public let device: DeviceIdentity
    public let beforeURL: URL
    public let installationSourceURL: URL?
    public let slot: Int?
    public let approvalDigest: String
    public let createdAt: Date
    public var sentAt: Date?
    public var verifiedAt: Date?
    public var verifiedBackupURL: URL?
    public var needsVerification: Bool { verifiedAt == nil }
}
public struct BankObservation: Codable, Sendable {
    public let device: DeviceIdentity
    public let version: String
    public let state: ProfileBankState?
    public let readAt: Date
    public let backupURL: URL
    public func belongs(to device: DeviceIdentity) -> Bool {
        !device.serial.isEmpty && device.serial == self.device.serial && device.qualifiedDescriptor
    }
}
private struct BankReadReceipt: Codable { var schemaVersion = 1; let device: DeviceIdentity; let backupURL: URL; let readAt: Date }

/// Files stay private and separate from legacy upload journals; every plan is reconstructed.
struct BankStore: Sendable {
    let directory: URL
    let expectedBootHash: String
    init(directory: URL,expectedBootHash: String = BackupEngine.qualifiedBootHash) {
        self.directory = directory; self.expectedBootHash = expectedBootHash
    }
    var pendingFile: URL { directory.appendingPathComponent("bank-transaction.json") }
    private var readFile: URL { directory.appendingPathComponent("bank-last-read.json") }
    private var installationFile: URL { directory.appendingPathComponent("bank-installation.json") }
    private var qualificationFile: URL { directory.appendingPathComponent("bank-transport-proof.json") }
    func save(_ transaction: BankTransaction) throws {
        try write(transaction,to: directory.appendingPathComponent("BankHistory/\(transaction.id).json"))
        try write(transaction,to: pendingFile)
    }
    func plan(for record: BankTransaction) throws -> BankPlan {
        guard record.schemaVersion == 1,record.device.qualifiedDescriptor,!record.device.serial.isEmpty,record.createdAt <= Date(),
              record.sentAt == nil || (record.sentAt! >= record.createdAt && record.sentAt! <= Date()),
              (record.verifiedAt == nil) == (record.verifiedBackupURL == nil) else { throw DeviceError.failure("Invalid bank transaction history.") }
        let before = try VerifiedBackup(url: record.beforeURL,device: record.device,expectedBootHash: expectedBootHash)
        guard before.result.manifest.device == record.device,record.createdAt >= before.result.manifest.createdAt else {
            throw DeviceError.failure("Bank intent does not match its original connection/backup.")
        }
        let plan: BankPlan
        switch record.operation {
        case .install:
            guard record.installationSourceURL == nil,let slot = record.slot else { throw DeviceError.failure("Invalid install record.") }
            plan = try .install(before,slot: slot)
        case .select:
            guard record.installationSourceURL == nil,let slot = record.slot else { throw DeviceError.failure("Invalid selection record.") }
            plan = try .select(before,slot: slot)
            guard plan.requiresWrite else { throw DeviceError.failure("A no-op cannot be a pending write.") }
        case .rollback:
            guard record.slot == nil,let url = record.installationSourceURL else { throw DeviceError.failure("Invalid rollback record.") }
            plan = try .rollback(before,installationSource: VerifiedBackup(url: url,device: record.device,expectedBootHash: expectedBootHash))
        case .motionDiagnostic:
            plan = try .motionDiagnostic(before)
            guard record.installationSourceURL == nil, let slot = record.slot,
                  try ProfileBank().profiles.firstIndex(where: { $0 == plan.selected }) == slot else {
                throw DeviceError.failure("Invalid motion diagnostic record.")
            }
        }
        guard plan.preview.approvalDigest == record.approvalDigest else { throw DeviceError.failure("Bank transaction plan no longer matches its durable record.") }
        return plan
    }
    func load() throws -> BankTransaction? {
        guard FileManager.default.fileExists(atPath: pendingFile.path) else { return nil }
        let record: BankTransaction = try read(pendingFile)
        _ = try plan(for: record)
        if record.verifiedAt != nil { try validateVerification(record) }
        return record
    }
    func requireNoPending() throws {
        if try load()?.needsVerification == true { throw DeviceError.failure("Reconnect and verify the pending bank transaction first.") }
    }
    func publish(_ backup: VerifiedBackup) throws -> BankObservation {
        let observation = try observation(backup)
        try archiveObservationBeforeInspection()
        try write(BankReadReceipt(device: observation.device,backupURL: observation.backupURL,readAt: observation.readAt),to: readFile)
        return observation
    }
    func archiveObservationBeforeInspection() throws {
        guard FileManager.default.fileExists(atPath: readFile.path) else { return }
        let history = directory.appendingPathComponent("BankReadHistory",isDirectory: true)
        try FileManager.default.createDirectory(at: history,withIntermediateDirectories: true,attributes: [.posixPermissions: 0o700])
        let destination = history.appendingPathComponent("\(UUID().uuidString).json")
        try FileManager.default.moveItem(at: readFile,to: destination)
        try DurableFile.synchronizeExisting(destination)
        try DurableFile.synchronizeDirectories(from: history)
    }
    private func observation(_ backup: VerifiedBackup) throws -> BankObservation {
        let version = backup.result.manifest.reportedFirmwareVersion
        let state: ProfileBankState?
        if version == ProfileBank.version { state = try ProfileBank().inspect(flash: backup.flash) }
        else if version == ProfileBank.motionDiagnosticVersion { state = try MotionDiagnostic().inspect(flash: backup.flash) }
        else { try BankPlan.requireLegacySource(backup); state = nil }
        return BankObservation(device: backup.result.manifest.device,version: version,state: state,
                               readAt: backup.result.manifest.createdAt,backupURL: backup.result.url)
    }
    func latestRead() throws -> BankObservation? {
        guard FileManager.default.fileExists(atPath: readFile.path) else { return nil }
        let receipt: BankReadReceipt = try read(readFile)
        let observation = try observation(VerifiedBackup(url: receipt.backupURL,device: receipt.device,expectedBootHash: expectedBootHash))
        guard receipt.schemaVersion == 1,observation.device == receipt.device,observation.readAt == receipt.readAt,receipt.readAt <= Date() else { throw DeviceError.failure("Invalid bank observation history.") }
        return observation
    }
    func installationSource(device: DeviceIdentity) throws -> VerifiedBackup {
        let record: BankTransaction = try read(installationFile)
        guard record.operation == .install,record.verifiedAt != nil else { throw DeviceError.failure("No verified pre-bank recovery source.") }
        try validateVerification(record)
        return try VerifiedBackup(url: record.beforeURL,device: device,expectedBootHash: expectedBootHash)
    }
    func qualified(device: DeviceIdentity) throws -> Bool {
        guard FileManager.default.fileExists(atPath: qualificationFile.path) else { return false }
        let record: BankTransaction = try read(qualificationFile)
        guard record.operation == .select,record.device.serial == device.serial,device.qualifiedDescriptor else { return false }
        try validateVerification(record)
        return true
    }
    func validateVerification(_ record: BankTransaction) throws {
        guard let when = record.verifiedAt,when >= record.createdAt,when <= Date(),let url = record.verifiedBackupURL else {
            throw DeviceError.failure("Bank transaction has no verified readback.")
        }
        let current = try VerifiedBackup(url: url,device: record.device,expectedBootHash: expectedBootHash)
        guard current.result.manifest.device.id != record.device.id else { throw DeviceError.failure("Bank proof lacks a new connection.") }
        try plan(for: record).verify(current,original: VerifiedBackup(url: record.beforeURL,device: record.device,expectedBootHash: expectedBootHash))
    }
    func complete(_ record: BankTransaction) throws {
        try validateVerification(record)
        try save(record)
        if record.operation == .install { try write(record,to: installationFile) }
        if record.operation == .select { try write(record,to: qualificationFile) }
    }
    func closeReviewedSelection(_ resolution: BankSelectionResolution) throws {
        guard let active = try load(),active.id == resolution.pending.id,active.needsVerification else {
            throw DeviceError.failure("The pending selection changed during review.")
        }
        let receipt = directory.appendingPathComponent("BankResolutions/\(active.id).json")
        try write(resolution,to: receipt)
        try FileManager.default.removeItem(at: pendingFile)
        try DurableFile.synchronizeDirectories(from: directory)
    }
    func archiveAfterStockRecovery(device: DeviceIdentity) throws {
        guard let pending = try load(),pending.needsVerification else { return }
        guard pending.device.serial == device.serial else { throw DeviceError.failure("A different adapter's bank transaction remains pending.") }
        let target = directory.appendingPathComponent("BankRecovery/\(pending.id)-superseded.json")
        try write(pending,to: target)
        try FileManager.default.removeItem(at: pendingFile)
        try DurableFile.synchronizeDirectories(from: directory)
    }
    private func write<T: Encodable>(_ value: T,to url: URL) throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(),withIntermediateDirectories: true,attributes: [.posixPermissions: 0o700])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted,.sortedKeys]
        try DurableFile.write(encoder.encode(value),to: url)
    }
    private func read<T: Decodable>(_ url: URL) throws -> T {
        let file = try FileHandle(forReadingFrom: url)
        defer { try? file.close() }
        let data = try file.read(upToCount: 16385) ?? Data()
        guard data.count <= 16384 else { throw DeviceError.failure("Bank history exceeds its size limit.") }
        return try JSONDecoder().decode(T.self,from: data)
    }
}
