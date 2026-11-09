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
            let preview = try service.previewBank(operation: operation,profile: operation == .rollback ? nil : profile(args[2]),device: read.device)
            print("Offline plan · \(operation.rawValue) · \(preview.profile?.name ?? "Pre-bank restore")\nApplication bytes: \(preview.applicationBytes)\nWrite needed: \(preview.requiresWrite)\nApproval: \(preview.approvalDigest)\nNo USB access. 4.8 hardware qualification remains pending.")
            return
        }
        let test = args.contains("--experimental"),clean = args.filter { $0 != "--experimental" }
        let operation: BankOperation?
        switch clean.first {
        case "bank-install": operation = .install
        case "bank-switch": operation = .select
        case "bank-rollback": operation = .rollback
        default: operation = nil
        }
        let valid = clean == ["bank-verify","--idle"] ||
            (clean.count == 3 && clean[0] == "bank-resolve-consumed" && clean[2] == "--idle") ||
            (operation == .rollback && clean.count == 3 && clean.last == "--idle") ||
            ((operation == .install || operation == .select) && clean.count == 4 && clean.last == "--idle")
        guard valid else { throw DeviceError.failure("Usage: bank-plan install|select|rollback PROFILE_ID|- (offline); bank-install|bank-switch PROFILE_ID APPROVAL --idle [--experimental]; bank-rollback APPROVAL --idle; bank-verify --idle; bank-resolve-consumed REVIEWED.ea9backup --idle") }
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
            let record = try await service.performBank(operation: operation,profile: operation == .rollback ? nil : profile(clean[1]),
                approvedDigest: clean[operation == .rollback ? 1 : 2],experimentalAcknowledged: test,device: device,
                idleAcknowledged: true,cancellation: token,progress: progress)
            print(record == nil ? "Already configured; no write." : "Sent. Physically unplug/reconnect, then run bank-verify --idle. No follow-up reports sent.")
        }
    }
}
