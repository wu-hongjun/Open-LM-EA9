import Foundation
import LensCore

public enum BankOperation: String, Codable, Sendable { case install, select, rollback }
public struct BankPreview: Sendable {
    public let operation: BankOperation
    public let profile: AdapterLensSetting?
    public let applicationBytes: Int
    public let requiresWrite: Bool
    public let approvalDigest: String
}

/// Pure, reconstructed from a unit-bound backup. No transport or arbitrary image input.
struct BankPlan: Sendable {
    let operation: BankOperation
    let image: Data
    let metadata: Data
    let before: Data
    let selected: AdapterLensSetting?
    let requiresWrite: Bool
    let auxiliaryBinding: Data
    let sourceDevice: DeviceIdentity
    private init(operation: BankOperation,image: Data,metadata: Data,before: Data,selected: AdapterLensSetting?,
                 requiresWrite: Bool,auxiliaryBinding: Data,sourceDevice: DeviceIdentity) {
        self.operation = operation; self.image = image; self.metadata = metadata; self.before = before
        self.selected = selected; self.requiresWrite = requiresWrite; self.auxiliaryBinding = auxiliaryBinding
        self.sourceDevice = sourceDevice
    }
    var version: [UInt8] { Array(metadata.prefix(3)) }
    var preview: BankPreview {
        var bound = Data(operation.rawValue.utf8); bound.append(before); bound.append(metadata); bound.append(image); bound.append(auxiliaryBinding)
        bound.append(Data("|connection=\(sourceDevice.id)".utf8))
        return BankPreview(operation: operation,profile: selected,applicationBytes: image.count,
                           requiresWrite: requiresWrite,approvalDigest: digest(bound))
    }
    static func requireLegacySource(_ snapshot: VerifiedBackup) throws {
        let v = snapshot.result.manifest.reportedFirmwareVersion
        if v == "1.8.0" {
            try requireStock(snapshot)
        } else {
            guard let variant = try ApplicationImage.installedVariant(snapshot.flash),v == variant.versionString else {
                throw DeviceError.failure("Only an exact supported source can migrate to the lens bank.")
            }
        }
    }
    private static func requireStock(_ snapshot: VerifiedBackup) throws {
        guard digest(Data(snapshot.flash[0x5000..<(0x5000+20172)])) == "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564" else {
            throw DeviceError.failure("Stock application bytes do not match the original pin.")
        }
    }
    static func install(_ snapshot: VerifiedBackup, profile: LensProfile) throws -> Self {
        try install(snapshot,slot: ProfileBank().slot(for: profile))
    }
    static func install(_ snapshot: VerifiedBackup, slot: Int) throws -> Self {
        try requireLegacySource(snapshot)
        try requireWritable(snapshot,applicationBytes: 0xf000,journal: true)
        guard snapshot.flash[0x10000..<0x14000].allSatisfy({ $0 == 255 }) else {
            throw DeviceError.failure("The proposed bank region contains data. Preserve the backup; migration will not claim it.")
        }
        let bank = try ProfileBank()
        guard bank.profiles.indices.contains(slot) else { throw DeviceError.failure("Unknown bank slot.") }
        var metadata = Data(snapshot.flash[0x4000..<0x403a])
        metadata.replaceSubrange(0..<3,with: [4,8,0])
        metadata.replaceSubrange(32..<58,with: try bank.mailbox(slot: slot,generation: 1))
        var full = snapshot.flash
        full.replaceSubrange(0x5000..<0xa000,with: bank.application)
        full.replaceSubrange(0x10000..<0x12000,with: bank.extensionCode)
        full.replaceSubrange(0x12000..<0x13000,with: bank.bytes)
        // Seed the selected profile and the matching consumed request together.
        // Initial camera startup performs validation/application but no settings write.
        full.replaceSubrange(ProfileBank.journalRange,with: try bank.journal(slot: slot,generation: 1))
        return Self(operation: .install,image: Data(full[ProfileBank.applicationRange]),metadata: metadata,
                    before: snapshot.flash,selected: bank.profiles[slot],requiresWrite: true,auxiliaryBinding: try binding(snapshot),sourceDevice: snapshot.result.manifest.device)
    }
    static func select(_ snapshot: VerifiedBackup, profile: LensProfile) throws -> Self {
        try select(snapshot,slot: ProfileBank().slot(for: profile))
    }
    static func select(_ snapshot: VerifiedBackup, slot: Int) throws -> Self {
        let bank = try ProfileBank(),state = try bank.inspect(flash: snapshot.flash)
        guard bank.profiles.indices.contains(slot) else { throw DeviceError.failure("Unknown bank slot.") }
        var metadata = Data(snapshot.flash[0x4000..<0x403a])
        let changed = slot != state.request.slot
        if changed {
            try requireWritable(snapshot,applicationBytes: 0,journal: true)
            guard state.request.generation < UInt32.max,state.setting.sequence < UInt32.max else {
                throw DeviceError.failure("Settings counters are exhausted. Preserve the backup for an explicit migration.")
            }
            metadata.replaceSubrange(32..<58,with: try bank.mailbox(slot: slot,generation: state.request.generation+1))
        }
        return Self(operation: .select,image: Data(),metadata: metadata,before: snapshot.flash,
                    selected: bank.profiles[slot],requiresWrite: changed,auxiliaryBinding: try binding(snapshot),sourceDevice: snapshot.result.manifest.device)
    }
    static func rollback(_ snapshot: VerifiedBackup, installationSource original: VerifiedBackup) throws -> Self {
        try ProfileBank().requireCode(in: snapshot.flash)
        try requireLegacySource(original)
        guard snapshot.result.manifest.device.serial == original.result.manifest.device.serial,
              snapshot.flash.prefix(0x4000) == original.flash.prefix(0x4000),
              snapshot.flash[0x4040..<0x5000] == original.flash[0x4040..<0x5000] else {
            throw DeviceError.failure("Pre-bank recovery does not match this unit's protected data.")
        }
        try requireAuxiliaryInvariant(snapshot,original)
        try requireWritable(snapshot,applicationBytes: 0x1b000,journal: false)
        return Self(operation: .rollback,image: Data(original.flash[0x5000..<0x20000]),
                    metadata: Data(original.flash[0x4000..<0x403a]),before: snapshot.flash,
                    selected: nil,requiresWrite: true,auxiliaryBinding: try binding(snapshot),sourceDevice: snapshot.result.manifest.device)
    }
    private static func binding(_ snapshot: VerifiedBackup) throws -> Data {
        let nvm = try Data(contentsOf: snapshot.result.url.appendingPathComponent("nvm-status.bin"))
        let values = [snapshot.result.manifest.device.serial] + ["device-id.bin","user-row.bin","calibration.bin"].map {
            snapshot.result.manifest.files[$0]!.sha256
        } + [String(little32(nvm,8)),String(u16(nvm,32))]
        return Data(values.joined(separator: "|").utf8)
    }
    func requireSnapshot(_ snapshot: VerifiedBackup) throws {
        guard before == snapshot.flash,sourceDevice == snapshot.result.manifest.device,
              auxiliaryBinding == (try Self.binding(snapshot)) else { throw DeviceError.failure("Plan and fresh recovery snapshot differ.") }
    }
    private static func requireWritable(_ snapshot: VerifiedBackup,applicationBytes: Int,journal: Bool) throws {
        let nvm = try Data(contentsOf: snapshot.result.url.appendingPathComponent("nvm-status.bin"))
        var mask: UInt16 = (1 << 2) | (1 << 1) // metadata: actual 8 KiB region and pinned loader's 16 KiB check
        if applicationBytes > 0 {
            for address in stride(from: 0x5000,to: 0x5000+applicationBytes,by: 64) {
                mask |= UInt16(1) << (address/8192)
                mask |= UInt16(1) << (address/16384)
            }
        }
        if journal { mask |= 1 << 9 }
        guard u16(nvm,32) & mask == mask else { throw DeviceError.failure("A required flash region is locked. No unlock or migration was attempted.") }
    }
    func verify(_ current: VerifiedBackup, original: VerifiedBackup) throws {
        var expected = before
        expected.replaceSubrange(0x4000..<0x403a,with: metadata)
        expected.replaceSubrange(0x5000..<(0x5000+image.count),with: image)
        let actual = current.flash
        guard actual.count == expected.count, actual.prefix(0x403a) == expected.prefix(0x403a),
              actual[0x4040..<0x20000] == expected[0x4040..<0x20000],
              current.result.manifest.reportedFirmwareVersion == version.map(String.init).joined(separator: ".") else {
            throw DeviceError.failure("Bank transaction readback differs from the complete plan. Preserve both backups; do not use the camera.")
        }
        try Self.requireAuxiliaryInvariant(current,original)
        if operation != .rollback { _ = try ProfileBank().inspect(flash: actual) }
        else { try Self.requireLegacySource(current) }
    }
    private static func requireAuxiliaryInvariant(_ a: VerifiedBackup,_ b: VerifiedBackup) throws {
        for name in ["device-id.bin","user-row.bin","calibration.bin"] {
            guard a.result.manifest.files[name]?.sha256 == b.result.manifest.files[name]?.sha256 else {
                throw DeviceError.failure("Protected auxiliary data changed: \(name)")
            }
        }
        let x = try Data(contentsOf: a.result.url.appendingPathComponent("nvm-status.bin"))
        let y = try Data(contentsOf: b.result.url.appendingPathComponent("nvm-status.bin"))
        guard little32(x,8) == little32(y,8),u16(x,32) == u16(y,32) else { throw DeviceError.failure("Flash geometry or lock state changed.") }
    }
}

/// Separate from image uploads: exactly one START and zero application reports.
struct BankSelectionEngine {
    func run(transport: any UploadTransport,plan: BankPlan,cancellation: CancellationToken) throws {
        guard plan.operation == .select,plan.image.isEmpty,plan.requiresWrite,plan.version == [4,8,0] else {
            throw DeviceError.failure("Invalid metadata-only plan.")
        }
        try cancellation.check()
        let report = UploadReport.start(metadata: plan.metadata,version: plan.version)
        guard try transport.send(report) == report.encoded() else {
            throw DeviceError.failure("Selection acknowledgement mismatch. Reconnect; no retry or query was sent.")
        }
        // No cancellation query, CHECK, READ, END, retry or padding after START.
    }
}
