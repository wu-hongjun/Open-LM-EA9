import Foundation
import DeviceKit

@main struct EA9CLI {
    static func main() async {
        do {
            var args = Array(CommandLine.arguments.dropFirst())
            var state = AdapterStorage.defaultDirectory
            if let index = args.firstIndex(of: "--state-directory"), index + 1 < args.count {
                state = URL(fileURLWithPath: args[index + 1], isDirectory: true)
                args.removeSubrange(index...index + 1)
            }
            let prepare: [String: () throws -> Data] = [
                "prepare-camera-aperture": FirmwareImageBuilder.prepareCameraDialAperture,
                "prepare-wide-aperture": FirmwareImageBuilder.prepareWideCameraAperture,
                "prepare-upstream-stock-speed": FirmwareImageBuilder.prepareUpstreamStockSpeed]
            if args.count == 2, let builder = prepare[args[0]] {
                let data = try builder()
                try data.write(to: URL(fileURLWithPath: args[1]), options: .withoutOverwriting)
                print("Prepared pinned image: \(data.count) bytes. No USB access.")
                return
            }
            let simple = ["verify","inspect","qualify-stock","apply-camera-aperture","apply-wide-aperture","apply-upstream-stock-speed"]
            let fileCommands = ["backup","restore-stock","resolve-stock-after-camera"]
            guard args == ["inventory"] || (args.count == 2 && simple.contains(args[0]) && args[1] == "--idle") ||
                    (args.count == 3 && fileCommands.contains(args[0]) && args[2] == "--idle") else {
                throw DeviceError.failure("Usage: ea9ctl [--state-directory PATH] inventory | inspect --idle | backup NEW.ea9backup --idle | apply-camera-aperture --idle | apply-wide-aperture --idle | apply-upstream-stock-speed --idle | verify --idle | qualify-stock --idle | restore-stock ORIGINAL.ea9backup --idle | prepare-camera-aperture NEW.bin | prepare-wide-aperture NEW.bin | prepare-upstream-stock-speed NEW.bin")
            }
            let service = DeviceService(stateDirectory: state)
            let devices = try await service.inventory()
            if args[0] == "inventory" {
                print("\(devices.count) matching adapter(s); no reports sent.")
                return
            }
            guard devices.count == 1 else { throw DeviceError.failure("Connect exactly one adapter.") }
            let device = devices[0], token = CancellationToken()
            let progress: @Sendable (BackupProgress) -> Void = { p in
                if p.completed == 0 || p.completed == p.total || p.completed % 8192 == 64 {
                    FileHandle.standardError.write(Data("\(p.phase) · \(Int(p.fraction * 100))%\n".utf8))
                }
            }
            var pending: PendingUpdate?
            switch args[0] {
            case "apply-camera-aperture": pending = try await service.applyCameraDialAperture(device: device, idleAcknowledged: true, cancellation: token, progress: progress)
            case "apply-wide-aperture": pending = try await service.applyWideCameraAperture(device: device, idleAcknowledged: true, cancellation: token, progress: progress)
            case "apply-upstream-stock-speed": pending = try await service.applyUpstreamStockSpeed(device: device, idleAcknowledged: true, cancellation: token, progress: progress)
            case "qualify-stock": pending = try await service.qualifyStockUpload(device: device, idleAcknowledged: true, cancellation: token, progress: progress)
            case "restore-stock": pending = try await service.restoreStock(backupURL: URL(fileURLWithPath: args[1]), device: device, idleAcknowledged: true, cancellation: token, progress: progress)
            case "verify", "inspect":
                let applied = args[0] == "verify" ?
                    try await service.verifyUpdate(device: device, idleAcknowledged: true, cancellation: token, progress: progress) :
                    try await service.readLens(device: device, idleAcknowledged: true, cancellation: token, progress: progress)
                if let applied {
                    print("Firmware: \(applied.firmwareVersion)\nLens: \(applied.setting.name)\nStartup report: \(applied.setting.focalLengthMM) mm · f/\(applied.setting.apertureLabel)\nSHA-256: \(applied.imageSHA256)")
                } else { print("Read complete; no supported custom lens setting.") }
            case "backup":
                let result = try await service.backup(device: device, to: URL(fileURLWithPath: args[1]), idleAcknowledged: true, cancellation: token, progress: progress)
                print("Backup verified: \(result.url.path)")
            case "resolve-stock-after-camera":
                let result = try await service.resolveStockAfterCamera(reviewedBackupURL: URL(fileURLWithPath: args[1]), device: device, idleAcknowledged: true, cancellation: token, progress: progress)
                print("Reviewed stock resolution saved; strict verification remains recorded separately. Changed motion bytes: \(result.changedMotionAddresses.count). No writes sent.")
            default: break
            }
            if let pending {
                print("Uploaded \(pending.image.count) bytes. Firmware: \(pending.version.map(String.init).joined(separator: "."))\nSHA-256: \(pending.imageSHA256)\nBackup: \(pending.backupURL.path)\nPhysically unplug/reconnect, then run verify --idle. No post-upload reports sent.")
            }
        } catch {
            FileHandle.standardError.write(Data("Stopped: \(error.localizedDescription)\n".utf8))
            exit(1)
        }
    }
}
