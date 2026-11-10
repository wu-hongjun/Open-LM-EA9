import Foundation
import DeviceKit
import LensCore

enum BankCLI {
    static func run(_ args: [String],state: URL) async throws {
        let service = DeviceService(stateDirectory: state)
        func profile(_ id: String) throws -> LensProfile {
            guard let value = try LibraryStore(directory: state).loadOrSeed().profiles.first(where: { $0.id == id }) else {
                throw DeviceError.failure("Choose a saved lens ID.")
            }
            return value
        }
        if args.count == 3,args[0] == "bank-plan",let operation = BankOperation(rawValue: args[1]) {
            guard let read = try service.bankObservation() else { throw DeviceError.failure("An explicit adapter Read is required before a bank plan.") }
            let needsProfile = operation == .install || operation == .select
            guard needsProfile || args[2] == "-" else { throw DeviceError.failure("This plan takes '-' and preserves the stored profile for the diagnostic.") }
            let preview = try service.previewBank(operation: operation,profile: needsProfile ? profile(args[2]) : nil,device: read.device)
            print("Offline plan · \(operation.rawValue) · \(preview.profile?.name ?? "Pre-bank restore")\nApplication bytes: \(preview.applicationBytes)\nWrite needed: \(preview.requiresWrite)\nApproval: \(preview.approvalDigest)\nNo USB access.")
            return
        }
        let test = args.contains("--experimental"),clean = args.filter { $0 != "--experimental" }
        let operation: BankOperation?
        switch clean.first {
        case "bank-install": operation = .install
        case "bank-switch": operation = .select
        case "bank-rollback": operation = .rollback
        case "bank-motion-diagnostic": operation = .motionDiagnostic
        default: operation = nil
        }
        let valid = clean == ["bank-verify","--idle"] ||
            (clean.count == 3 && clean[0] == "bank-resolve-consumed" && clean[2] == "--idle") ||
            (operation == .rollback && clean.count == 3 && clean.last == "--idle") ||
            (operation == .motionDiagnostic && test && clean.count == 3 && clean.last == "--idle") ||
            ((operation == .install || operation == .select) && clean.count == 4 && clean.last == "--idle")
        guard valid else { throw DeviceError.failure("Usage: bank-plan install|select|rollback|motion-diagnostic PROFILE_ID|- (offline); bank-install|bank-switch PROFILE_ID APPROVAL --idle [--experimental]; bank-rollback APPROVAL --idle; bank-motion-diagnostic APPROVAL --idle --experimental; bank-verify --idle; bank-resolve-consumed REVIEWED.ea9backup --idle") }
        // Inventory/report access exists only after an explicitly requested hardware command.
        let devices = try await service.inventory()
        guard devices.count == 1,let device = devices.first else { throw DeviceError.failure("Connect exactly one adapter.") }
        let token = CancellationToken(),progress: @Sendable (BackupProgress) -> Void = { value in
            if value.completed == value.total { print(value.phase) }
        }
        if clean[0] == "bank-verify" {
            let observation = try await service.verifyBank(device: device,idleAcknowledged: true,cancellation: token,progress: progress)
            print("Verified \(observation.version). \(observation.state?.configured.name ?? "Pre-bank firmware")\(observation.state?.pendingCameraBoot == true ? " · pending camera power-on" : "")")
        } else if clean[0] == "bank-resolve-consumed" {
            let observed = try await service.resolveConsumedBankSelection(reviewedBackupURL: URL(fileURLWithPath: clean[1]),
                device: device,idleAcknowledged: true,cancellation: token,progress: progress)
            print("Reviewed journal commit: \(observed.state?.committed.name ?? "Unknown"). USB-only verification remains separate.")
        } else if let operation {
            let needsProfile = operation == .install || operation == .select
            let record = try await service.performBank(operation: operation,profile: needsProfile ? profile(clean[1]) : nil,
                approvedDigest: clean[needsProfile ? 2 : 1],experimentalAcknowledged: test,device: device,
                idleAcknowledged: true,cancellation: token,progress: progress)
            print(record == nil ? "Already configured; no write." : "Sent. Physically unplug/reconnect, then run bank-verify --idle. No follow-up reports sent.")
        }
    }
}
