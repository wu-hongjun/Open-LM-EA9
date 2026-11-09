import Foundation

/// Durable evidence for a selection consumed before USB-only verification.
/// This receipt is separate from strict verification and transport proof.
struct BankSelectionResolution: Encodable {
    let policy = "reviewed-consumed-bank-selection-v1"
    let pending: BankTransaction
    let reviewedBackupURL: URL
    let freshBackupURL: URL
    let resolvedAt: Date
    let committed: BankSetting
    let strictVerificationPassed = false

    static func assess(pending: BankTransaction,store: BankStore,reviewed: VerifiedBackup,
                       fresh: VerifiedBackup) throws -> Self {
        let first = reviewed.result.manifest, second = fresh.result.manifest
        // Backup manifests store whole UTC seconds. An ACK in that same second is valid.
        guard pending.operation == .select,pending.needsVerification,let sentAt = pending.sentAt,
              first.createdAt.addingTimeInterval(1) > sentAt,second.createdAt >= first.createdAt,
              first.device.serial == pending.device.serial,second.device.serial == pending.device.serial,
              Set([pending.device.id,first.device.id,second.device.id]).count == 3 else {
            throw DeviceError.failure("Review requires an acknowledged selection and a fresh connection after the reviewed readback.")
        }
        guard fresh.flash == reviewed.flash else {
            throw DeviceError.failure("Fresh flash differs from the reviewed readback. The selection remains pending.")
        }
        let original = try VerifiedBackup(url: pending.beforeURL,device: pending.device,expectedBootHash: store.expectedBootHash)
        let plan = try store.plan(for: pending)
        let committed = try plan.verifyConsumedSelection(reviewed,original: original)
        _ = try plan.verifyConsumedSelection(fresh,original: original)
        return Self(pending: pending,reviewedBackupURL: reviewed.result.url,freshBackupURL: fresh.result.url,
                    resolvedAt: Date(),committed: committed)
    }
}
