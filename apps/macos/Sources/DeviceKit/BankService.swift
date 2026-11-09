import Foundation
import LensCore

extension DeviceService {
    public func pendingBankTransaction() throws -> BankTransaction? { try BankStore(directory: stateDirectory).load() }
    public func bankObservation() throws -> BankObservation? { try BankStore(directory: stateDirectory).latestRead() }
    public func bankTransportQualified(for device: DeviceIdentity) throws -> Bool { try BankStore(directory: stateDirectory).qualified(device: device) }

    /// Disk-only concrete preview. A new connection needs an explicit complete Read first.
    public func previewBank(operation: BankOperation,profile: LensProfile?,device: DeviceIdentity) throws -> BankPreview {
        let store = BankStore(directory: stateDirectory)
        try store.requireNoPending()
        guard try UpdateStore(directory: stateDirectory).load()?.needsVerification != true,
              let observation = try store.latestRead(),observation.belongs(to: device),observation.device.id == device.id else {
            throw DeviceError.failure("Read this USB connection before reviewing a bank change.")
        }
        let before = try VerifiedBackup(url: observation.backupURL,device: device)
        return try BankCoordinator.plan(operation: operation,profile: profile,before: before,store: store).preview
    }
    /// First install / first metadata switch require an explicit experimental test acknowledgment.
    /// Merely choosing a dropdown, preparing a preview, or reading status never calls this API.
    public func performBank(operation: BankOperation,profile: LensProfile?,approvedDigest: String,
        experimentalAcknowledged: Bool,device: DeviceIdentity,idleAcknowledged: Bool,cancellation: CancellationToken,
        progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> BankTransaction? {
        guard try stockUploadQualified(for: device) else { throw DeviceError.failure("Verify this adapter's stock upload path first.") }
        if operation != .rollback && !experimentalAcknowledged {
            guard operation == .select,try bankTransportQualified(for: device) else {
                throw DeviceError.failure("This bank operation needs a separately coordinated experimental test.")
            }
        }
        return try await withIdleDevice(device: device,idleAcknowledged: idleAcknowledged,cancellation: cancellation) { transport in
            let store = BankStore(directory: self.stateDirectory)
            guard try self.stockUploadQualified(for: device) else { throw DeviceError.failure("Upload qualification changed.") }
            if operation == .select && !experimentalAcknowledged {
                guard try store.qualified(device: device) else { throw DeviceError.failure("Metadata transport proof changed.") }
            }
            try store.requireNoPending()
            guard try UpdateStore(directory: self.stateDirectory).load()?.needsVerification != true else { throw DeviceError.failure("Verify the legacy upload first.") }
            let backup = try self.bankBackup(transport: transport,device: device,prefix: "before-bank",cancellation: cancellation,progress: progress)
            let plan = try BankCoordinator.plan(operation: operation,profile: profile,before: backup,store: store)
            guard plan.preview.approvalDigest == approvedDigest else { throw DeviceError.failure("The complete plan changed since review. No START was sent.") }
            if !plan.requiresWrite { _ = try store.publish(backup); return nil }
            guard try transport.exchange(.flashBlock(0)) == backup.flash.prefix(64) else { throw DeviceError.failure("Final idle preflight did not match.") }
            return try BankCoordinator.send(plan: plan,approvedDigest: approvedDigest,before: backup,store: store,
                                            transport: transport,cancellation: cancellation,progress: progress)
        }
    }
    public func verifyBank(device: DeviceIdentity,idleAcknowledged: Bool,cancellation: CancellationToken,
                           progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> BankObservation {
        let store = BankStore(directory: stateDirectory)
        guard let record = try store.load(),record.needsVerification,record.device.id != device.id,
              record.device.serial == device.serial else { throw DeviceError.failure("Physically reconnect the same adapter before bank verification.") }
        return try await withIdleDevice(device: device,idleAcknowledged: idleAcknowledged,cancellation: cancellation) { transport in
            // Recheck while holding the shared USB/process lock.
            guard try UpdateStore(directory: self.stateDirectory).load()?.needsVerification != true else { throw DeviceError.failure("Verify the legacy recovery upload first.") }
            guard let locked = try store.load(),locked.id == record.id,locked.needsVerification else { throw DeviceError.failure("The bank transaction changed.") }
            let backup = try self.bankBackup(transport: transport,device: device,prefix: "after-bank",cancellation: cancellation,progress: progress)
            return try BankCoordinator.verify(record: locked,current: backup,store: store)
        }
    }
    /// Close a reviewed selection after one exact journal commit and a second
    /// identical readback on a new connection. This path sends only reads.
    public func resolveConsumedBankSelection(reviewedBackupURL: URL,device: DeviceIdentity,idleAcknowledged: Bool,
        cancellation: CancellationToken,progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> BankObservation {
        let store = BankStore(directory: stateDirectory)
        guard let pending = try store.load(),pending.operation == .select,pending.needsVerification,pending.sentAt != nil,
              pending.device.serial == device.serial else {
            throw DeviceError.failure("No acknowledged selection is pending for this adapter.")
        }
        let reviewed = try VerifiedBackup(url: reviewedBackupURL,device: device)
        guard Set([pending.device.id,reviewed.result.manifest.device.id,device.id]).count == 3 else {
            throw DeviceError.failure("Physically reconnect the cap after the reviewed readback.")
        }
        let original = try VerifiedBackup(url: pending.beforeURL,device: device)
        _ = try store.plan(for: pending).verifyConsumedSelection(reviewed,original: original)
        return try await withIdleDevice(device: device,idleAcknowledged: idleAcknowledged,cancellation: cancellation) { transport in
            guard try UpdateStore(directory: self.stateDirectory).load()?.needsVerification != true,
                  let locked = try store.load(),locked.id == pending.id,locked.needsVerification else {
                throw DeviceError.failure("The pending transaction changed. Review it again.")
            }
            let fresh = try self.bankBackup(transport: transport,device: device,prefix: "reviewed-bank",cancellation: cancellation,progress: progress)
            let resolution = try BankSelectionResolution.assess(pending: locked,store: store,reviewed: reviewed,fresh: fresh)
            try reviewed.synchronizeRecoveryEvidence()
            try fresh.synchronizeRecoveryEvidence()
            _ = try LensInspection.publish(fresh,to: UpdateStore(directory: store.directory))
            try store.closeReviewedSelection(resolution)
            guard let observation = try store.latestRead() else { throw DeviceError.failure("Missing reviewed bank observation.") }
            return observation
        }
    }
    private func bankBackup(transport: NativeTransport,device: DeviceIdentity,prefix: String,cancellation: CancellationToken,
                            progress: @Sendable (BackupProgress) -> Void) throws -> VerifiedBackup {
        let folder = stateDirectory.appendingPathComponent("USBBackups",isDirectory: true)
        try FileManager.default.createDirectory(at: folder,withIntermediateDirectories: true,attributes: [.posixPermissions: 0o700])
        let url = folder.appendingPathComponent("\(prefix)-\(UUID().uuidString).ea9backup")
        _ = try BackupEngine().run(transport: transport,identity: device,destination: url,cancellation: cancellation,progress: progress)
        return try VerifiedBackup(url: url,device: device)
    }
}
