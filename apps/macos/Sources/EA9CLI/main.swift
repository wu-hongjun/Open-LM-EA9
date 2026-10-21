import Foundation
import DeviceKit
import LensCore

@main struct EA9CLI {
    private static func variant(for command: String) -> FirmwareVariant {
        switch command {
        case "prepare-crash-upstream", "apply-crash-upstream": .autofocusCrashDiagnostic
        case "prepare-reference-upstream", "apply-reference-upstream": .autofocusReferenceQualified
        case "prepare-homing-upstream", "apply-homing-upstream": .autofocusHomingDiagnostic
        case "prepare-readiness-upstream", "apply-readiness-upstream": .autofocusReadiness
        case "prepare-trace-upstream", "apply-trace-upstream": .autofocusTargetedTrace
        case "prepare-handoff-upstream", "apply-handoff-upstream": .autofocusStartupHandoff
        case "prepare-absolute-upstream", "apply-absolute-upstream": .autofocusAbsoluteUpstream
        case "prepare-bounded-upstream", "apply-bounded-upstream": .autofocusBoundedUpstream
        case "prepare-hardened-upstream", "apply-hardened-upstream": .autofocusUpstreamHardened
        case "prepare-startup", "apply-startup": .autofocusStartupDiagnostic
        case "prepare-upstream", "apply-upstream": .autofocusUpstreamBaseline
        case "prepare-af", "apply-af": .autofocusArbitratedCamera
        default: .metadataOnly
        }
    }
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
            let usage = "Crash diagnostic 4.1 (camera-unqualified): prepare-crash-upstream PROFILE-ID NEW.bin | apply-crash-upstream PROFILE-ID --idle. Reference qualification 4.0 (camera-unqualified): prepare-reference-upstream PROFILE-ID NEW.bin | apply-reference-upstream PROFILE-ID --idle. Homing diagnostic 3.9 (camera-unqualified): prepare-homing-upstream PROFILE-ID NEW.bin | apply-homing-upstream PROFILE-ID --idle. Readiness 3.8: prepare-readiness-upstream PROFILE-ID NEW.bin | apply-readiness-upstream PROFILE-ID --idle. Targeted trace 3.7: prepare-trace-upstream PROFILE-ID NEW.bin | apply-trace-upstream PROFILE-ID --idle. Startup handoff: prepare-handoff-upstream PROFILE-ID NEW.bin | apply-handoff-upstream PROFILE-ID --idle. Absolute upstream: prepare-absolute-upstream PROFILE-ID NEW.bin | apply-absolute-upstream PROFILE-ID --idle. Bounded upstream: prepare-bounded-upstream PROFILE-ID NEW.bin | apply-bounded-upstream PROFILE-ID --idle. Hardened upstream: prepare-hardened-upstream PROFILE-ID NEW.bin | apply-hardened-upstream PROFILE-ID --idle. Startup diagnostic: prepare-startup PROFILE-ID NEW.bin | apply-startup PROFILE-ID --idle. Usage: ea9ctl [--state-directory PATH] inventory | backup NEW.ea9backup --idle | apply PROFILE-ID --idle | apply-af PROFILE-ID --idle | qualify-stock --idle | verify --idle | inspect --idle | restore-stock ORIGINAL.ea9backup --idle | prepare PROFILE-ID NEW.bin | prepare-af PROFILE-ID NEW.bin | prepare-upstream PROFILE-ID NEW.bin | apply-upstream PROFILE-ID --idle"
            guard args == ["inventory"] || (args.count == 3 && ["backup","apply","apply-af","apply-upstream","apply-startup","apply-hardened-upstream","apply-bounded-upstream","apply-absolute-upstream","apply-handoff-upstream","apply-trace-upstream","apply-readiness-upstream","apply-homing-upstream","apply-reference-upstream","apply-crash-upstream","restore-stock"].contains(args[0]) && args[2] == "--idle")
                || (args.count == 2 && ["verify","inspect","qualify-stock"].contains(args[0]) && args[1] == "--idle")
                || (args.count == 3 && ["prepare","prepare-af","prepare-upstream","prepare-startup","prepare-hardened-upstream","prepare-bounded-upstream","prepare-absolute-upstream","prepare-handoff-upstream","prepare-trace-upstream","prepare-readiness-upstream","prepare-homing-upstream","prepare-reference-upstream","prepare-crash-upstream"].contains(args[0]))
                || (args.count == 3 && args[0] == "resolve-stock-after-camera" && args[2] == "--idle") else { throw DeviceError.failure(usage + " | resolve-stock-after-camera REVIEWED.ea9backup --idle") }
            if ["prepare","prepare-af","prepare-upstream","prepare-startup","prepare-hardened-upstream","prepare-bounded-upstream","prepare-absolute-upstream","prepare-handoff-upstream","prepare-trace-upstream","prepare-readiness-upstream","prepare-homing-upstream","prepare-reference-upstream","prepare-crash-upstream"].contains(args[0]) {
                let library = try LibraryStore(directory: state).loadOrSeed()
                guard let profile = library.profiles.first(where: { $0.id == args[1] }) else { throw DeviceError.failure("Unknown lens profile.") }
                let data = try FirmwareImageBuilder.prepare(profile: profile, variant: variant(for: args[0]))
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
            case "resolve-stock-after-camera":
                let result = try await service.resolveStockAfterCamera(reviewedBackupURL: URL(fileURLWithPath: args[1]),
                    device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
                print("Stock restoration resolved by explicit reviewed motion-record policy.\nStrict verification remains recorded as failed; \(result.changedMotionAddresses.count) motion bytes accepted against the retained review.\nFresh flash SHA-256: \(result.freshFlashSHA256)\nApplication slot SHA-256: \(result.applicationSlotSHA256)\nFresh backup: \(result.freshBackupURL.path)\nNo writes were sent.")
            case "qualify-stock":
                let pending = try await service.qualifyStockUpload(device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
                print("Stock application re-uploaded: \(pending.image.count) bytes.\nBackup: \(pending.backupURL.path)\nPhysically unplug and reconnect, then run verify --idle. This does not qualify bootloader restoration or power-loss recovery.")
            case "apply", "apply-af", "apply-upstream","apply-startup","apply-hardened-upstream","apply-bounded-upstream","apply-absolute-upstream","apply-handoff-upstream","apply-trace-upstream","apply-readiness-upstream","apply-homing-upstream","apply-reference-upstream","apply-crash-upstream":
                let library = try LibraryStore(directory: state).loadOrSeed()
                guard let profile = library.profiles.first(where: { $0.id == args[1] }) else { throw DeviceError.failure("Unknown lens profile.") }
                let pending = try await service.apply(profile: profile, variant: variant(for: args[0]), device: device, idleAcknowledged: true, cancellation: token, progress: reportProgress)
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
