import Foundation
import LensCore

/// Production transaction logic with injected transport; all tests use synthetic loaders.
enum BankCoordinator {
    static func plan(operation: BankOperation,profile: LensProfile?,before: VerifiedBackup,store: BankStore) throws -> BankPlan {
        switch operation {
        case .install:
            guard let profile else { throw DeviceError.failure("Choose a lens before installing the bank.") }
            return try .install(before,profile: profile)
        case .select:
            guard let profile else { throw DeviceError.failure("Choose a bank lens.") }
            return try .select(before,profile: profile)
        case .rollback: return try .rollback(before,installationSource: store.installationSource(device: before.result.manifest.device))
        }
    }
    static func send(plan: BankPlan,approvedDigest: String,before: VerifiedBackup,store: BankStore,
                     transport: any UploadTransport,cancellation: CancellationToken,
                     progress: @Sendable (BackupProgress) -> Void) throws -> BankTransaction? {
        try plan.requireSnapshot(before)
        guard plan.preview.approvalDigest == approvedDigest else { throw DeviceError.failure("The adapter changed since the preview. Read and review the plan again.") }
        try store.requireNoPending()
        let legacy = UpdateStore(directory: store.directory)
        guard try legacy.load()?.needsVerification != true else { throw DeviceError.failure("Verify the previous firmware upload first.") }
        guard plan.requiresWrite else { return nil }
        try cancellation.check()
        try before.synchronizeRecoveryEvidence()
        let bank = try ProfileBank()
        let slot = plan.selected.flatMap { bank.profiles.firstIndex(of: $0) }
        let sourceURL = plan.operation == .rollback ? try store.installationSource(device: before.result.manifest.device).result.url : nil
        var record = BankTransaction(id: UUID(),operation: plan.operation,device: before.result.manifest.device,
            beforeURL: before.result.url,installationSourceURL: sourceURL,slot: slot,
            approvalDigest: plan.preview.approvalDigest,createdAt: Date())
        _ = try store.plan(for: record) // Reopen and validate the recovery evidence before arming.
        try store.save(record) // Durable intent before even an attempted START.
        if plan.operation == .select { try BankSelectionEngine().run(transport: transport,plan: plan,cancellation: cancellation) }
        else {
            try UploadEngine().run(transport: transport,
                image: ApplicationImage(data: plan.image,version: plan.version,setting: plan.selected),metadata: plan.metadata,
                cancellation: cancellation,progress: progress)
        }
        record.sentAt = Date(); try store.save(record)
        return record
    }
    static func verify(record: BankTransaction,current: VerifiedBackup,store: BankStore) throws -> BankObservation {
        guard record.needsVerification,current.result.manifest.device.id != record.device.id,
              current.result.manifest.device.serial == record.device.serial else { throw DeviceError.failure("Physically reconnect the same adapter before verifying the bank transaction.") }
        let original = try VerifiedBackup(url: record.beforeURL,device: record.device,expectedBootHash: store.expectedBootHash)
        try store.plan(for: record).verify(current,original: original)
        try current.synchronizeRecoveryEvidence()
        var done = record; done.verifiedAt = Date(); done.verifiedBackupURL = current.result.url
        try store.complete(done)
        if record.operation == .rollback { _ = try LensInspection.publish(current,to: UpdateStore(directory: store.directory)) }
        else {
            let legacy = UpdateStore(directory: store.directory)
            try legacy.archiveAppliedBeforeInspection()
            try FirmwareObservationStore(directory: store.directory).save(FirmwareObservation(
                device: current.result.manifest.device,version: current.result.manifest.reportedFirmwareVersion,
                readAt: current.result.manifest.createdAt))
        }
        return try store.publish(current)
    }
}
