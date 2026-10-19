import Foundation
import LensCore

public enum FirmwareVariant: String, CaseIterable, Sendable {
    case metadataOnly, autofocusExperimental, autofocusReconciled, autofocusHardened, autofocusFactoryBaseline, autofocusFactoryRefined, autofocusAuditedAperture, autofocusPolished, autofocusObservedMotion, autofocusServicedCamera, autofocusArbitratedCamera, autofocusUpstreamBaseline, autofocusStartupDiagnostic, autofocusUpstreamHardened, autofocusBoundedUpstream, autofocusAbsoluteUpstream, autofocusStartupHandoff, autofocusTargetedTrace, autofocusReadiness
    var version: [UInt8] {
        switch self { case .metadataOnly: [2,0,0]; case .autofocusExperimental: [2,1,0]; case .autofocusReconciled: [2,2,0]; case .autofocusHardened: [2,3,0]; case .autofocusFactoryBaseline: [2,4,0]; case .autofocusFactoryRefined: [2,5,0]; case .autofocusAuditedAperture: [2,6,0]; case .autofocusPolished: [2,7,0]; case .autofocusObservedMotion: [2,8,0]; case .autofocusServicedCamera: [2,9,0]; case .autofocusArbitratedCamera: [3,0,0]; case .autofocusUpstreamBaseline: [3,1,0]; case .autofocusStartupDiagnostic: [3,2,0]; case .autofocusUpstreamHardened: [3,3,0]; case .autofocusBoundedUpstream: [3,4,0]; case .autofocusAbsoluteUpstream: [3,5,0]; case .autofocusStartupHandoff: [3,6,0]; case .autofocusTargetedTrace: [3,7,0]; case .autofocusReadiness: [3,8,0] }
    }
    public var versionString: String { version.map(String.init).joined(separator: ".") }
    var resource: String {
        switch self { case .metadataOnly: "ea9-profile-template"; case .autofocusExperimental: "ea9-af-template"; case .autofocusReconciled: "ea9-af-reconciled-template"; case .autofocusHardened: "ea9-af-hardened-template"; case .autofocusFactoryBaseline: "ea9-af-factory-template"; case .autofocusFactoryRefined: "ea9-af-refined-template"; case .autofocusAuditedAperture: "ea9-af-audited-template"; case .autofocusPolished: "ea9-af-polished-template"; case .autofocusObservedMotion: "ea9-af-observed-template"; case .autofocusServicedCamera: "ea9-af-serviced-template"; case .autofocusArbitratedCamera: "ea9-af-arbitrated-template"; case .autofocusUpstreamBaseline: "ea9-af-upstream-baseline"; case .autofocusStartupDiagnostic: "ea9-af-startup-diagnostic"; case .autofocusUpstreamHardened: "ea9-af-upstream-hardened"; case .autofocusBoundedUpstream: "ea9-af-bounded-upstream"; case .autofocusAbsoluteUpstream: "ea9-af-absolute-upstream"; case .autofocusStartupHandoff: "ea9-af-handoff-upstream"; case .autofocusTargetedTrace: "ea9-af-targeted-trace"; case .autofocusReadiness: "ea9-af-readiness-upstream" }
    }
    var sha256: String {
        switch self { case .metadataOnly: TrustedTemplate.sha256; case .autofocusExperimental: TrustedAFTemplate.sha256; case .autofocusReconciled: TrustedReconciledAFTemplate.sha256; case .autofocusHardened: TrustedHardenedAFTemplate.sha256; case .autofocusFactoryBaseline: TrustedFactoryAFTemplate.sha256; case .autofocusFactoryRefined: TrustedRefinedAFTemplate.sha256; case .autofocusAuditedAperture: TrustedAuditedAFTemplate.sha256; case .autofocusPolished: TrustedPolishedAFTemplate.sha256; case .autofocusObservedMotion: TrustedObservedAFTemplate.sha256; case .autofocusServicedCamera: TrustedServicedAFTemplate.sha256; case .autofocusArbitratedCamera: TrustedArbitratedAFTemplate.sha256; case .autofocusUpstreamBaseline: TrustedUpstreamBaseline.sha256; case .autofocusStartupDiagnostic: TrustedStartupAFTemplate.sha256; case .autofocusUpstreamHardened: TrustedUpstreamHardened.sha256; case .autofocusBoundedUpstream: TrustedBoundedUpstream.sha256; case .autofocusAbsoluteUpstream: TrustedAbsoluteUpstream.sha256; case .autofocusStartupHandoff: TrustedHandoffUpstream.sha256; case .autofocusTargetedTrace: TrustedTargetedTrace.sha256; case .autofocusReadiness: TrustedReadinessUpstream.sha256 }
    }
    public var enablesAutofocus: Bool { self != .metadataOnly }
    // 2.2 and later stop before the retained factory prefix/copy. Legacy pins retain their layout.
    public var supportsLensProfileChanges: Bool { ![.autofocusUpstreamBaseline, .autofocusStartupDiagnostic, .autofocusUpstreamHardened, .autofocusBoundedUpstream, .autofocusAbsoluteUpstream, .autofocusStartupHandoff, .autofocusTargetedTrace, .autofocusReadiness].contains(self) }
    var profileAddress: Int { [.autofocusReconciled, .autofocusHardened, .autofocusFactoryBaseline, .autofocusFactoryRefined, .autofocusAuditedAperture, .autofocusPolished, .autofocusObservedMotion, .autofocusServicedCamera, .autofocusArbitratedCamera].contains(self) ? 0x9f00 : 0xa000 }
    var profileOffset: Int { profileAddress - ApplicationImage.base }
    var applicationBytes: Int { profileOffset + (supportsLensProfileChanges ? 256 : 0) }
    var applicationEnd: Int { profileAddress + (supportsLensProfileChanges ? 256 : 0) }
    static func from(version: [UInt8]) -> Self? { allCases.first { $0.version == version } }
}

public enum FirmwareImageBuilder {
    public static func prepare(profile: LensProfile, variant: FirmwareVariant = .metadataOnly) throws -> Data { try ApplicationImage.personalized(profile, variant: variant).data }
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

/// Only a pinned built-in application or a verified unit backup can create a plan.
struct ApplicationImage: Sendable {
    static let base = 0x5000
    let data: Data
    let version: [UInt8]
    let setting: AdapterLensSetting?
    var metadataOverride: Data? = nil
    static func template(_ variant: FirmwareVariant = .metadataOnly) throws -> Data {
        guard let url = Bundle.module.url(forResource: variant.resource, withExtension: "bin") else {
            throw DeviceError.failure("The bundled firmware template is missing.")
        }
        let image = try Data(contentsOf: url)
        guard image.count == variant.applicationBytes, digest(image) == variant.sha256 else { throw DeviceError.failure("Firmware template checksum failed.") }
        let sp = little32(image,0), reset = little32(image,4)
        guard (0x20000000...0x20004000).contains(sp), sp % 8 == 0, reset & 1 == 1,
              reset & ~1 >= UInt32(base), reset & ~1 < UInt32(variant.profileAddress) else { throw DeviceError.failure("Invalid application vectors.") }
        return image
    }
    static func personalized(_ profile: LensProfile, variant: FirmwareVariant = .metadataOnly) throws -> Self {
        var data = try template(variant); let setting = try AdapterLensSetting(profile: profile)
        if !variant.supportsLensProfileChanges {
            let fixed = try upstreamBaselineSetting()
            guard setting == fixed else {
                throw DeviceError.failure("This upstream firmware is compiled for the original Contax Zeiss 50mm f/1.4 profile. Lens edits and other profiles require another firmware build; no USB update was started.")
            }
            return Self(data: data, version: variant.version, setting: fixed)
        }
        data.replaceSubrange(variant.profileOffset..<variant.applicationBytes, with: try setting.encoded())
        return Self(data: data, version: variant.version, setting: setting)
    }
    /// The main profile action preserves firmware based on its fresh backup,
    /// not just a cached version. Explicit install/restore actions choose a variant.
    static func requirePreservedFirmware(_ variant: FirmwareVariant, in backup: VerifiedBackup) throws {
        if variant == .metadataOnly && backup.result.manifest.reportedFirmwareVersion == "1.8.0",
           backup.flash[0x4000..<0x4003] == Data([1,8,0]),
           digest(Data(backup.flash[base..<(base + 20172)])) == "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564" {
            return // The reviewed initial stock-to-metadata setup.
        }
        guard backup.result.manifest.reportedFirmwareVersion == variant.versionString,
              try installedVariant(backup.flash) == variant,
              try installedSetting(backup.flash) != nil else {
            throw DeviceError.failure("Current firmware does not match your last verified setting. No update was started. Review the adapter’s settings and try again.")
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
        guard flash[base..<variant.profileAddress] == (try template(variant)).prefix(variant.profileOffset) else { return nil }
        return variant
    }
    private static func upstreamBaselineSetting() throws -> AdapterLensSetting {
        // Frozen with this image; future library-seed edits cannot reinterpret it.
        AdapterLensSetting(id: "contax-zeiss-50-f1-4", name: "Contax Zeiss 50mm f/1.4",
                           focalMM10: 500, maximumAV: 4352, reportedAV: 4352, revision: 1)
    }
    static func setting(in image: Data, variant: FirmwareVariant) throws -> AdapterLensSetting {
        guard image.count == variant.applicationBytes,
              image.prefix(variant.profileOffset) == (try template(variant)).prefix(variant.profileOffset) else {
            throw DeviceError.failure("Unrecognized application bytes.")
        }
        if !variant.supportsLensProfileChanges { return try upstreamBaselineSetting() }
        return try AdapterLensSetting.decode(Data(image.suffix(256)))
    }
    static func installedSetting(_ flash: Data) throws -> AdapterLensSetting? {
        guard flash.count == 0x20000 else { throw DeviceError.failure("Invalid full-flash read.") }
        guard let variant = try installedVariant(flash) else { return nil }
        return try setting(in: Data(flash[base..<variant.applicationEnd]), variant: variant)
    }
}
