import Foundation
import LensCore

/// Installable images. Retired experiments have read-only compatibility pins.
public enum FirmwareVariant: String, CaseIterable, Sendable {
    case upstreamStockSpeed, cameraDialAperture, wideCameraAperture, lensProfiles
    var version: [UInt8] {
        switch self { case .upstreamStockSpeed: [4,4,0]; case .cameraDialAperture: [4,5,0]; case .wideCameraAperture: [4,6,0]; case .lensProfiles: [4,7,0] }
    }
    public var versionString: String { version.map(String.init).joined(separator: ".") }
    var resource: String {
        switch self { case .upstreamStockSpeed: "ea9-upstream-stock-speed"; case .cameraDialAperture: "ea9-biotar-camera-aperture"; case .wideCameraAperture: "ea9-biotar-wide-aperture"; case .lensProfiles: "ea9-lens-profile-template" }
    }
    public var compiledLens: AdapterLensSetting { ApplicationImage.fixedUpstreamSetting(self) }
    public var imageSHA256: String { sha256 }
    var sha256: String {
        switch self { case .upstreamStockSpeed: TrustedUpstreamStockSpeed.sha256; case .cameraDialAperture: TrustedCameraDialAperture.sha256; case .wideCameraAperture: TrustedWideCameraAperture.sha256; case .lensProfiles: LensProfileImage.sha256 }
    }
    public var apertureRangeLabel: String {
        switch self { case .upstreamStockSpeed: "f/1.8"; case .cameraDialAperture: "f/2–f/16"; case .wideCameraAperture, .lensProfiles: "f/1.2–f/22" }
    }
    public var enablesAutofocus: Bool { true }
    /// Full-image personalization, not a settings-only USB capability.
    public var supportsLensProfileChanges: Bool { self == .lensProfiles }
    var profileAddress: Int { ApplicationImage.base + profileOffset }
    var profileOffset: Int { self == .lensProfiles ? LensProfileImage.recordOffset : 0x5000 }
    var applicationBytes: Int { 0x5000 }
    var applicationEnd: Int { 0xa000 }
    static func from(version: [UInt8]) -> Self? { allCases.first { $0.version == version } }
}

public enum FirmwareImageBuilder {
    public static func prepare(profile: LensProfile, variant: FirmwareVariant = .lensProfiles) throws -> Data { try ApplicationImage.personalized(profile, variant: variant).data }
    public static func prepareUpstreamStockSpeed() throws -> Data { try ApplicationImage.upstreamStockSpeed().data }
    public static func prepareCameraDialAperture() throws -> Data { try ApplicationImage.cameraDialAperture().data }
    public static func prepareWideCameraAperture() throws -> Data { try ApplicationImage.wideCameraAperture().data }
}

/// Stored camera report settings, not a sensor reading of the attached passive lens.
public struct AdapterLensSetting: Codable, Equatable, Sendable {
    public let id: String
    public let name: String
    public let focalMM10: UInt16
    public let maximumAV: UInt16
    public let reportedAV: UInt16
    public let revision: UInt32
    public var focalLengthMM: Double { Double(focalMM10) / 10 }
    public var reportedAperture: Double { pow(2, Double(Int(reportedAV) - 4096) / 512) }
    /// A saved f-number never proves the current position of a passive iris.
    public var actualAperture: Double? { nil }
    public var actualApertureLabel: String { "Unknown" }
    public var apertureLabel: String {
        let stops: [Double] = [1,1.2,1.4,1.8,2,2.5,2.8,3.2,3.5,4,4.5,5,5.6,6.3,7.1,8,9,10,11,13,14,16,18,20,22,25,28,32,36,40,45,51,57,64,72,80,90,102,114,128]
        let nearest = stops.min { abs(log2($0 / reportedAperture)) < abs(log2($1 / reportedAperture)) }!
        let value = abs(nearest / reportedAperture - 1) < 0.025 ? nearest : reportedAperture
        return value.formatted(.number.precision(.fractionLength(0...1)))
    }

    public init(profile: LensProfile) throws {
        try profile.validate()
        let focal: Double
        if profile.kind == .zoom {
            guard let selected = profile.activeFocalLengthMM else {
                throw DeviceError.failure("Set the zoom’s current focal length before applying it. The adapter cannot measure a passive lens’s zoom position.")
            }
            focal = selected
        } else { focal = profile.minimumFocalLengthMM }
        guard abs(focal * 10 - (focal * 10).rounded()) < 0.00001 else {
            throw DeviceError.failure("Adapter focal length must use 0.1 mm increments.")
        }
        func aperture(_ f: Double) throws -> UInt16 {
            guard f >= 1 else { throw DeviceError.failure("This firmware supports reported apertures from f/1 to f/128.") }
            return UInt16(4096 + Int((16 * log2(f)).rounded()) * 32)
        }
        id = profile.id; name = profile.displayName
        focalMM10 = UInt16((focal * 10).rounded())
        maximumAV = try aperture(profile.maximumAperture)
        reportedAV = try aperture(profile.currentAperture ?? profile.maximumAperture)
        revision = UInt32(profile.revision)
        _ = try encoded()
    }
    func encoded() throws -> Data {
        var b = [UInt8](repeating: 0, count: 256)
        func string(_ value: String, at offset: Int, capacity: Int) throws {
            let bytes = Array(value.utf8)
            guard !bytes.isEmpty, bytes.count < capacity, bytes.allSatisfy({ (32...126).contains($0) }) else {
                throw DeviceError.failure("For the adapter, use an ASCII profile ID under 80 bytes and lens name under 64 bytes.")
            }
            b.replaceSubrange(offset..<(offset + bytes.count), with: bytes)
        }
        func number(_ n: UInt32, at offset: Int, count: Int) {
            for i in 0..<count { b[offset+i] = UInt8(truncatingIfNeeded: n >> (i*8)) }
        }
        guard (10...10000).contains(focalMM10), (4096...7168).contains(maximumAV),
              (maximumAV...7680).contains(reportedAV), maximumAV % 32 == 0, reportedAV % 32 == 0,
              (1...1_000_000).contains(revision) else { throw DeviceError.failure("Invalid adapter lens settings.") }
        b.replaceSubrange(0..<8, with: Array("EA9LENS1".utf8))
        number(1, at: 8, count: 2); number(256, at: 10, count: 2)
        number(UInt32(focalMM10), at: 12, count: 2); number(UInt32(maximumAV), at: 14, count: 2)
        number(UInt32(reportedAV), at: 16, count: 2); number(234, at: 18, count: 2)
        number(revision, at: 20, count: 4)
        try string(id, at: 24, capacity: 80); try string(name, at: 104, capacity: 64)
        number(profileCRC(Data(b.prefix(252))), at: 252, count: 4)
        return Data(b)
    }
    static func decode(_ data: Data) throws -> Self {
        let b = Data(data)
        guard b.count == 256, b.prefix(8) == Data("EA9LENS1".utf8),
              u16(b, 8) == 1, u16(b, 10) == 256, u16(b, 18) == 234,
              profileCRC(Data(b.prefix(252))) == little32(b, 252), b[168..<252].allSatisfy({ $0 == 0 }) else {
            throw DeviceError.failure("Invalid lens profile signature, format or checksum.")
        }
        func string(_ offset: Int, _ capacity: Int) throws -> String {
            let bytes = b[offset..<(offset+capacity)]
            guard let zero = bytes.firstIndex(of: 0), bytes[zero...].allSatisfy({ $0 == 0 }),
                  let text = String(data: b[offset..<zero], encoding: .ascii) else { throw DeviceError.failure("Invalid profile string.") }
            return text
        }
        let value = Self(id: try string(24,80), name: try string(104,64), focalMM10: u16(b,12),
                         maximumAV: u16(b,14), reportedAV: u16(b,16), revision: little32(b,20))
        guard try value.encoded() == b else { throw DeviceError.failure("Noncanonical profile.") }
        return value
    }
    fileprivate init(id: String, name: String, focalMM10: UInt16, maximumAV: UInt16, reportedAV: UInt16, revision: UInt32) {
        self.id = id; self.name = name; self.focalMM10 = focalMM10; self.maximumAV = maximumAV
        self.reportedAV = reportedAV; self.revision = revision
    }
}

func u16(_ b: Data, _ offset: Int) -> UInt16 { UInt16(b[offset]) | UInt16(b[offset+1]) << 8 }
func profileCRC(_ b: Data) -> UInt32 {
    var crc: UInt32 = 0xffffffff
    for byte in b {
        crc ^= UInt32(byte)
        for _ in 0..<8 { crc = (crc >> 1) ^ ((crc & 1) == 1 ? 0xedb88320 : 0) }
    }
    return crc ^ 0xffffffff
}

/// Pinned application plans only; no arbitrary firmware file input.
struct ApplicationImage: Sendable {
    static let base = 0x5000
    let data: Data
    let version: [UInt8]
    let setting: AdapterLensSetting?
    var metadataOverride: Data? = nil
    static func cameraDialAperture() throws -> Self { try builtIn(.cameraDialAperture) }
    static func wideCameraAperture() throws -> Self { try builtIn(.wideCameraAperture) }
    static func upstreamStockSpeed() throws -> Self { try builtIn(.upstreamStockSpeed) }
    private static func builtIn(_ variant: FirmwareVariant) throws -> Self {
        Self(data: try template(variant), version: variant.version, setting: fixedUpstreamSetting(variant))
    }
    static func template(_ variant: FirmwareVariant = .cameraDialAperture) throws -> Data {
        guard let url = Bundle.module.url(forResource: variant.resource, withExtension: "bin") else {
            throw DeviceError.failure("The bundled firmware image is missing.")
        }
        let image = try Data(contentsOf: url)
        guard image.count == variant.applicationBytes, digest(image) == variant.sha256 else { throw DeviceError.failure("Firmware image checksum failed.") }
        let sp = little32(image,0), reset = little32(image,4)
        guard (0x20000000...0x20004000).contains(sp), sp % 8 == 0, reset & 1 == 1,
              reset & ~1 >= UInt32(base), reset & ~1 < UInt32(variant.profileAddress) else { throw DeviceError.failure("Invalid application vectors.") }
        return image
    }
    static func personalized(_ profile: LensProfile, variant: FirmwareVariant = .cameraDialAperture) throws -> Self {
        if variant == .lensProfiles {
            let setting = try AdapterLensSetting(profile: profile)
            return Self(data: try LensProfileImage.image(for: setting), version: variant.version, setting: setting)
        }
        let fixed = fixedUpstreamSetting(variant), selected = try AdapterLensSetting(profile: profile)
        guard selected == fixed else {
            throw DeviceError.failure("This release is compiled for \(fixed.name). Library edits stay on this Mac; changing firmware lens metadata requires another build.")
        }
        return try builtIn(variant)
    }
    static func requirePreservedFirmware(_ variant: FirmwareVariant, in backup: VerifiedBackup) throws {
        guard backup.result.manifest.reportedFirmwareVersion == variant.versionString,
              try installedVariant(backup.flash) == variant else {
            throw DeviceError.failure("The installed application differs from the expected pinned image. No update was started.")
        }
    }
    static func requireCameraDialApertureSource(_ backup: VerifiedBackup) throws {
        if backup.result.manifest.reportedFirmwareVersion == "1.8.0" {
            _ = try stockRestoration(backup)
        } else if ["4.6.0", "4.7.0"].contains(backup.result.manifest.reportedFirmwareVersion) {
            try requirePreservedFirmware(backup.result.manifest.reportedFirmwareVersion == "4.7.0" ? .lensProfiles : .wideCameraAperture, in: backup)
        } else {
            try requirePreservedFirmware(.upstreamStockSpeed, in: backup)
        }
    }
    static func requireWideCameraApertureSource(_ backup: VerifiedBackup) throws {
        try requirePreservedFirmware(backup.result.manifest.reportedFirmwareVersion == "4.7.0" ? .lensProfiles : .cameraDialAperture, in: backup)
    }
    static func requireLensProfileSource(_ backup: VerifiedBackup) throws {
        if backup.result.manifest.reportedFirmwareVersion == "1.8.0" { _ = try stockRestoration(backup); return }
        guard let variant = try installedVariant(backup.flash) else {
            throw DeviceError.failure("Read a supported, unmodified application before switching lens profiles.")
        }
        try requirePreservedFirmware(variant, in: backup)
    }
    static func requireUpstreamStockSpeedSource(_ backup: VerifiedBackup) throws {
        if backup.result.manifest.reportedFirmwareVersion == "1.8.0" {
            _ = try stockRestoration(backup)
        } else if backup.result.manifest.reportedFirmwareVersion == "4.5.0" {
            try requirePreservedFirmware(.cameraDialAperture, in: backup)
        } else if backup.result.manifest.reportedFirmwareVersion == "4.7.0" {
            try requirePreservedFirmware(.lensProfiles, in: backup)
        } else {
            try requirePreservedFirmware(.wideCameraAperture, in: backup)
        }
    }
    static func stockRestoration(_ backup: VerifiedBackup) throws -> Self {
        guard backup.result.manifest.reportedFirmwareVersion == "1.8.0",
              digest(Data(backup.flash[0x5000..<(0x5000+20172)])) == "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564" else {
            throw DeviceError.failure("Recovery needs this adapter’s verified original stock 1.8.0 backup.")
        }
        return Self(data: Data(backup.flash[0x5000..<0x20000]), version: [1,8,0], setting: nil,
                    metadataOverride: Data(backup.flash[0x4000..<0x403a]))
    }
    static func installedVariant(_ flash: Data) throws -> FirmwareVariant? {
        guard flash.count == 0x20000 else { throw DeviceError.failure("Invalid full-flash read.") }
        guard let variant = FirmwareVariant.from(version: Array(flash[0x4000..<0x4003])) else { return nil }
        if variant == .lensProfiles {
            return (try? LensProfileImage.setting(in: Data(flash[base..<variant.applicationEnd]))) != nil ? variant : nil
        }
        return flash[base..<variant.applicationEnd] == (try template(variant)) ? variant : nil
    }
    fileprivate static func fixedUpstreamSetting(_ variant: FirmwareVariant) -> AdapterLensSetting {
        if variant == .upstreamStockSpeed {
            return AdapterLensSetting(id: "upstream-november-50-f1-8", name: "Upstream 50mm f/1.8",
                                      focalMM10: 500, maximumAV: 4544, reportedAV: 4544, revision: 1)
        }
        // Lens specification and boot report; selectable camera range is separate.
        return AdapterLensSetting(id: "zeiss-jena-biotar-55-f2", name: "Zeiss Jena Biotar 58mm f/2",
                                  focalMM10: 580, maximumAV: 4608, reportedAV: 4608, revision: 1)
    }
    static func setting(in image: Data, variant: FirmwareVariant) throws -> AdapterLensSetting? {
        if variant == .lensProfiles { return try LensProfileImage.setting(in: image) }
        guard image == (try template(variant)) else { throw DeviceError.failure("Unrecognized application bytes.") }
        return fixedUpstreamSetting(variant)
    }
    static func installedSetting(_ flash: Data) throws -> AdapterLensSetting? {
        guard let variant = try installedVariant(flash) else { return nil }
        if variant == .lensProfiles { return try LensProfileImage.setting(in: Data(flash[base..<variant.applicationEnd])) }
        return fixedUpstreamSetting(variant)
    }
}
