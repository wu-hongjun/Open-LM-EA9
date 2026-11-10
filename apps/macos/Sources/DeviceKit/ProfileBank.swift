import Foundation
import LensCore

/// Immutable 4.8 code/bank. The journal and loader metadata have separate formats.
public struct ProfileBank: Sendable {
    public static let version = "4.8.0"
    public static let motionDiagnosticVersion = "4.8.1"
    public static let applicationRange = 0x5000..<0x14000
    public static let journalRange = 0x13000..<0x14000
    static let pins = [
        "application": "201d8a52d5bcf130afe164da6215985deb30c3538f0c6464b6235cf64b92e87b",
        "extension": "463b17a13b05e72c5c032412817b7df31d034ee2fde20ca9dd40c7a27877ee41",
        "bank": "6030199e944c879579c03095cf8951680ec3c975faad1269ffb4f5f4c410cc5c",
        "settings": "792e624b04946aaaf1f941982ced204c8b77843b17477ba609c1c8cee177f762"]
    let application: Data, extensionCode: Data, bytes: Data
    public let profiles: [AdapterLensSetting]
    let fingerprint: UInt32
    public init() throws {
        func resource(_ name: String, _ size: Int) throws -> Data {
            guard let url = Bundle.module.url(forResource: "ea9-bank48-" + name, withExtension: "bin") else {
                throw DeviceError.failure("The profile-bank package is missing.")
            }
            let data = try Data(contentsOf: url)
            guard data.count == size, digest(data) == Self.pins[name] else { throw DeviceError.failure("Profile-bank package pin failed.") }
            return data
        }
        application = try resource("application", 20480)
        extensionCode = try resource("extension", 8192)
        let bankBytes = try resource("bank", 4096)
        bytes = bankBytes
        _ = try resource("settings", 4096)
        fingerprint = little32(bankBytes,20)
        profiles = try (0..<Int(bankBytes[14])).map { try AdapterLensSetting.decode(Data(bankBytes[(64+256*$0)..<(320+256*$0)])) }
    }
    public func slot(for profile: LensProfile) throws -> Int {
        let selected = try AdapterLensSetting(profile: profile)
        // Local note edits/revision bumps do not change the adapter's optical fields.
        guard let index = profiles.firstIndex(where: {
            $0.id == selected.id && $0.name == selected.name && $0.focalMM10 == selected.focalMM10 &&
                $0.maximumAV == selected.maximumAV && $0.reportedAV == selected.reportedAV
        }) else {
            throw DeviceError.failure("This lens or its edited metadata is not in the installed bank. Update the bank separately; switching never reflashes firmware.")
        }
        return index
    }
    func requireCode(in flash: Data) throws {
        guard flash.count == 0x20000, Data(flash[0x5000..<0xa000]) == application,
              Data(flash[0x10000..<0x12000]) == extensionCode, Data(flash[0x12000..<0x13000]) == bytes else {
            throw DeviceError.failure("Installed 4.8 code or bank does not match the pinned package.")
        }
    }
    func mailbox(slot: Int, generation: UInt32) throws -> Data {
        guard profiles.indices.contains(slot), generation > 0 else { throw DeviceError.failure("Invalid bank selection request.") }
        var b = Data(repeating: 0,count: 26)
        b.replaceSubrange(0..<4,with: Data("OLAC".utf8)); b[4]=1; b[5]=UInt8(slot)
        bankPut32(&b,8,fingerprint); bankPut32(&b,12,generation)
        bankPut32(&b,20,profileCRC(Data(b.prefix(20)))); b.replaceSubrange(24..<26,with: Data("OK".utf8))
        return b
    }
    func decodeMailbox(_ metadata: Data) throws -> BankRequest {
        guard metadata.count == 58 else { throw DeviceError.failure("Invalid loader metadata size.") }
        let m = Data(metadata[32..<58]), slot = Int(m[5]), generation = little32(m,12)
        guard try m == mailbox(slot: slot,generation: generation) else { throw DeviceError.failure("Unowned or invalid profile mailbox. Use the explicit bank migration.") }
        return BankRequest(slot: slot,generation: generation)
    }
    func setting(slot: Int, sequence: UInt32, generation: UInt32) throws -> Data {
        guard profiles.indices.contains(slot), sequence > 0 else { throw DeviceError.failure("Invalid bank setting.") }
        var b = Data(repeating: 0,count: 64)
        b.replaceSubrange(0..<8,with: Data("OLASET1!".utf8)); b[8]=1; b[10]=64
        bankPut32(&b,12,fingerprint); bankPut32(&b,16,sequence); bankPut32(&b,20,generation); b[24]=UInt8(slot)
        bankPut32(&b,56,profileCRC(Data(b.prefix(56)))); b.replaceSubrange(60..<64,with: Data("DONE".utf8))
        return b
    }
    func journal(slot: Int, generation: UInt32) throws -> Data {
        var data = Data(repeating: 255,count: 4096)
        data.replaceSubrange(0..<64,with: try setting(slot: slot,sequence: 1,generation: generation))
        return data
    }
    func decodeJournal(_ data: Data) throws -> BankSetting {
        guard data.count == 4096 else { throw DeviceError.failure("Invalid settings region size.") }
        var valid: [BankSetting] = []
        for row in 0..<16 {
            guard data[(row*256+64)..<(row*256+256)].allSatisfy({ $0 == 255 }) else {
                throw DeviceError.failure("Unrecognized bytes outside a settings page.")
            }
            let p = Data(data[(row*256)..<(row*256+64)])
            let sequence = little32(p,16), generation = little32(p,20), slot = Int(p[24])
            if let canonical = try? setting(slot: slot,sequence: sequence,generation: generation), canonical == p {
                valid.append(BankSetting(slot: slot,sequence: sequence,generation: generation,row: row))
            }
        }
        guard let newest = valid.max(by: { $0.sequence < $1.sequence }),
              !valid.contains(where: { $0.sequence == newest.sequence && ($0.slot != newest.slot || $0.generation != newest.generation) }) else {
            throw DeviceError.failure("No unambiguous committed profile setting. Preserve the backup for recovery.")
        }
        return newest
    }
    public func inspect(flash: Data) throws -> ProfileBankState {
        try requireCode(in: flash)
        guard flash[0x4000..<0x4003] == Data([4,8,0]) else { throw DeviceError.failure("Bank code and loader version disagree.") }
        return try inspectSettings(flash: flash)
    }
    func inspectSettings(flash: Data) throws -> ProfileBankState {
        let setting = try decodeJournal(Data(flash[Self.journalRange]))
        let request = try decodeMailbox(Data(flash[0x4000..<0x403a]))
        guard request.generation >= setting.generation,
              request.generation != setting.generation || request.slot == setting.slot else {
            throw DeviceError.failure("Mailbox and committed journal disagree. No profile change was prepared.")
        }
        return ProfileBankState(committed: profiles[setting.slot],configured: profiles[request.slot],
            pendingCameraBoot: request.generation > setting.generation,setting: setting,request: request)
    }
}

public struct BankSetting: Codable, Equatable, Sendable { public let slot: Int; public let sequence, generation: UInt32; public let row: Int }
public struct BankRequest: Codable, Equatable, Sendable { public let slot: Int; public let generation: UInt32 }
public struct ProfileBankState: Codable, Equatable, Sendable {
    public let committed, configured: AdapterLensSetting
    public let pendingCameraBoot: Bool
    public let setting: BankSetting
    public let request: BankRequest
}
func bankPut32(_ b: inout Data,_ offset: Int,_ value: UInt32) {
    for i in 0..<4 { b[offset+i] = UInt8(truncatingIfNeeded: value >> (8*i)) }
}
