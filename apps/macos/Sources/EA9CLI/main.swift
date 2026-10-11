import Foundation
import DeviceKit
import LensCore

@main struct EA9CLI {
    static func main() async {
        do {
            var args = Array(CommandLine.arguments.dropFirst())
            var state = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("org.openlmea9.prototype", isDirectory: true)
            if let index = args.firstIndex(of: "--state-directory"), index + 1 < args.count {
                state = URL(fileURLWithPath: args[index + 1], isDirectory: true)
                args.removeSubrange(index...index + 1)
            }
            let service = DeviceService(stateDirectory: state)
            let usage = "Usage: ea9ctl [--state-directory PATH] inventory | backup NEW.ea9backup --idle | apply PROFILE-ID --idle | apply-af PROFILE-ID --idle | qualify-stock --idle | verify --idle | inspect --idle | restore-stock ORIGINAL.ea9backup --idle | prepare PROFILE-ID NEW.bin | prepare-af PROFILE-ID NEW.bin"
            guard args == ["inventory"] || (args.count == 3 && ["backup","apply","apply-af","restore-stock"].contains(args[0]) && args[2] == "--idle")
                || (args.count == 2 && ["verify","inspect","qualify-stock"].contains(args[0]) && args[1] == "--idle")
                || (args.count == 3 && ["prepare","prepare-af"].contains(args[0])) else { throw DeviceError.failure(usage) }
            if ["prepare","prepare-af"].contains(args[0]) {
                let library = try LibraryStore(directory: state).loadOrSeed()
                guard let profile = library.profiles.first(where: { $0.id == args[1] }) else { throw DeviceError.failure("Unknown lens profile.") }
                let data = try FirmwareImageBuilder.prepare(profile: profile, variant: args[0] == "prepare-af" ? .autofocusReconciled : .metadataOnly)
                try data.write(to: URL(fileURLWithPath: args[2]), options: .withoutOverwriting)
                print("Prepared application image: \(data.count) bytes. No USB reports sent.")
                return
            }
            let devices = try await service.inventory()
            if args[0] == "inventory" {
                // Inventory never sends CHECK; omit serial/location from terminal output.
                for device in devices { print("\(device.product) · connection \(device.id) · descriptor \(device.qualifiedDescriptor ? "qualified" : "unrecognized")") }
                print("\(devices.count) matching adapter(s); no reports sent.")
                return
            }
            guard devices.count == 1 else { throw DeviceError.failure("Connect exactly one adapter.") }
            let device = devices[0], token = CancellationToken()
            let reportProgress: @Sendable (BackupProgress) -> Void = { p in
                if p.completed == 0 || p.completed == p.total || p.completed % 8192 == 64 {
                    FileHandle.standardError.write(Data("\(p.phase) · \(Int(p.fraction * 100))%\n".utf8))
                }
            }
            switch args[0] {
            case "qualify-stock":
                let pending = try await service.qualifyStockUpload(device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
                print("Stock application re-uploaded: \(pending.image.count) bytes.\nBackup: \(pending.backupURL.path)\nPhysically unplug and reconnect, then run verify --idle. This does not qualify bootloader restoration or power-loss recovery.")
            case "apply", "apply-af":
                let library = try LibraryStore(directory: state).loadOrSeed()
                guard let profile = library.profiles.first(where: { $0.id == args[1] }) else { throw DeviceError.failure("Unknown lens profile.") }
                let pending = try await service.apply(profile: profile, variant: args[0] == "apply-af" ? .autofocusReconciled : .metadataOnly, device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
                print("Firmware: \(pending.version.map(String.init).joined(separator: "."))\nUploaded \(pending.image.count) bytes for \(profile.displayName).\nSHA-256: \(pending.imageSHA256)\nBackup: \(pending.backupURL.path)\nPhysically unplug and reconnect the adapter, then run verify --idle. No read-back yet.")
            case "verify", "inspect":
                let applied = args[0] == "verify" ?
                    try await service.verifyUpdate(device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress) :
                    try await service.readLens(device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
                if let applied {
                    print("USB byte verification complete: \(applied.setting.name) · \(applied.setting.focalLengthMM) mm · reported AV \(applied.setting.reportedAV)\nFirmware: \(applied.firmwareVersion)\nSHA-256: \(applied.imageSHA256)\nCamera behavior still needs a physical camera check.")
                } else { print(args[0] == "verify" ? "Stock restoration verified." : "No supported custom lens profile found.") }
            case "restore-stock":
                let pending = try await service.restoreStock(backupURL: URL(fileURLWithPath: args[1]), device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
                print("Stock application uploaded: \(pending.image.count) bytes. Physically reconnect, then run verify --idle.")
            default:
                let result = try await service.backup(device: device, to: URL(fileURLWithPath: args[1]), idleAcknowledged: true,
                                                     cancellation: token, progress: reportProgress)
                print("Verified backup: \(result.url.path)\nFlash: \(result.manifest.flashBytes) bytes · 2 matching passes\nSHA-256: \(result.manifest.files["flash.bin"]!.sha256)\nExchanges: \(result.manifest.reportExchanges)")
            }
        } catch {
            FileHandle.standardError.write(Data("\(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }
}
