import Foundation

/// Explicit reviewed closure, distinct from strict upload verification. The
/// failed journal and both reads remain private evidence; no flag is rewritten.
public struct StockRestoreResolution: Codable, Sendable {
    public let policy: String
    public let transactionID: UUID
    public let resolvedAt: Date
    public let reviewedBackupURL: URL
    public let freshBackupURL: URL
    public let freshFlashSHA256: String
    public let applicationSlotSHA256: String
    public let changedMotionAddresses: [Int]
    public let strictVerificationPassed: Bool
}

enum StockRestoreReview {
    // Recovered semantic writers: raw sample, protocol position, relative
    // position, velocity, target, direction and timeout. Origin, configuration,
    // live enable flags, unassigned bytes and all other gap bytes stay exact.
    static let motionRanges = [0x4100..<0x4102, 0x4106..<0x4108, 0x410c..<0x4112,
                               0x4114..<0x4116, 0x411c..<0x411d, 0x4120..<0x4122]
    static func assess(pending: PendingUpdate, original: VerifiedBackup,
                       reviewed: VerifiedBackup, fresh: VerifiedBackup) throws -> StockRestoreResolution {
        guard pending.version == [1,8,0], pending.setting == nil,
              pending.image.count == 0x1b000, pending.verifiedAt == nil,
              let uploaded = pending.uploadedAt,
              digest(pending.image) == pending.imageSHA256,
              digest(Data(pending.image.prefix(20172))) == "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564",
              reviewed.result.manifest.createdAt >= uploaded,
              fresh.result.manifest.createdAt >= reviewed.result.manifest.createdAt else {
            throw DeviceError.failure("Only an uploaded pinned stock restoration with a later reviewed readback can be resolved.")
        }
        for backup in [original, reviewed, fresh] {
            guard backup.result.manifest.device.serial == pending.device.serial,
                  !pending.device.serial.isEmpty else { throw DeviceError.failure("Stock review evidence belongs to another adapter.") }
        }
        guard reviewed.result.manifest.device.id != pending.device.id,
              fresh.result.manifest.device.id != pending.device.id,
              fresh.result.manifest.device.id != reviewed.result.manifest.device.id,
              reviewed.result.manifest.reportedFirmwareVersion == "1.8.0",
              fresh.result.manifest.reportedFirmwareVersion == "1.8.0" else {
            throw DeviceError.failure("Reconnect the same adapter after the reviewed stock readback.")
        }
        let actual = fresh.flash, before = original.flash
        guard actual == reviewed.flash,
              actual[0x5000..<0x20000] == pending.image,
              actual.prefix(0x4000) == before.prefix(0x4000),
              actual[0x4000..<0x403a] == pending.expectedMetadata else {
            throw DeviceError.failure("Fresh stock code, metadata or full-flash read differs from the reviewed evidence. The pending restore remains unresolved.")
        }
        let changes = (0x4040..<0x5000).filter { actual[$0] != before[$0] }
        guard !changes.isEmpty, changes.allSatisfy({ address in motionRanges.contains { $0.contains(address) } }) else {
            throw DeviceError.failure("Stock gap changes exceed the explicitly reviewed motion fields. Strict verification is unchanged.")
        }
        for name in ["user-row.bin", "calibration.bin", "device-id.bin", "nvm-status.bin"] {
            guard fresh.result.manifest.files[name]?.sha256 == reviewed.result.manifest.files[name]?.sha256 else {
                throw DeviceError.failure("Fresh stock auxiliary evidence differs from the reviewed readback.")
            }
            if name != "nvm-status.bin" {
                guard fresh.result.manifest.files[name]?.sha256 == original.result.manifest.files[name]?.sha256 else {
                    throw DeviceError.failure("Factory data differs from the pre-restore backup.")
                }
            }
        }
        return StockRestoreResolution(policy: "reviewed-stock-camera-motion-v1", transactionID: pending.transactionID,
            resolvedAt: Date(), reviewedBackupURL: reviewed.result.url, freshBackupURL: fresh.result.url,
            freshFlashSHA256: digest(actual), applicationSlotSHA256: digest(pending.image),
            changedMotionAddresses: changes, strictVerificationPassed: false)
    }
}

extension UpdateStore {
    func closeReviewedStockRestore(_ pending: PendingUpdate, resolution: StockRestoreResolution) throws {
        // Publish the complete receipt before removing only the active pointer.
        // A disk failure leaves either a pending journal or a durable receipt.
        struct Receipt: Encodable { let pending: PendingUpdate; let resolution: StockRestoreResolution }
        let history = directory.appendingPathComponent("RestoreResolutions", isDirectory: true)
        try FileManager.default.createDirectory(at: history, withIntermediateDirectories: true,
                                               attributes: [.posixPermissions: 0o700])
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        try DurableFile.write(encoder.encode(Receipt(pending: pending, resolution: resolution)),
                              to: history.appendingPathComponent("\(pending.transactionID)-\(UUID().uuidString).json"))
        try FileManager.default.removeItem(at: file)
        try DurableFile.synchronizeDirectories(from: directory)
    }
}
