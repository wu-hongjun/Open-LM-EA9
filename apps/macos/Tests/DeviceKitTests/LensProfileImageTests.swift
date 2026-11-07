import Foundation
import Testing
import LensCore
@testable import DeviceKit

@Test func eachLibraryLensProducesCanonicalProfileFirmware() throws {
    let template = try ApplicationImage.template(.lensProfiles)
    #expect(digest(template) == LensProfileImage.sha256)
    #expect(template.suffix(256).allSatisfy { $0 == 0xff })
    #expect(throws: DeviceError.self) { try LensProfileImage.setting(in: template) }
    for var profile in try LensLibrary.seeds().profiles {
        if profile.kind == .zoom { profile.activeFocalLengthMM = 50 }
        let setting = try AdapterLensSetting(profile: profile)
        let image = try ApplicationImage.personalized(profile, variant: .lensProfiles)
        #expect(image.version == [4,7,0] && image.data.count == 20480)
        #expect(try ApplicationImage.setting(in: image.data, variant: .lensProfiles) == setting)
        #expect(u16(image.data, LensProfileImage.focalOffset) == setting.focalMM10)
        #expect(u16(image.data, LensProfileImage.startupOffset) == setting.reportedAV)
        #expect(image.data[LensProfileImage.nameOffset..<(LensProfileImage.nameOffset+setting.name.utf8.count)] == Data(setting.name.utf8))
        #expect(try FirmwareImageBuilder.prepare(profile: profile) == image.data)
        let allowed = Set([LensProfileImage.focalOffset, LensProfileImage.focalOffset+1,
                           LensProfileImage.startupOffset, LensProfileImage.startupOffset+1] +
                          Array(LensProfileImage.nameOffset..<(LensProfileImage.nameOffset+64)) +
                          Array(LensProfileImage.recordOffset..<20480))
        #expect(zip(template, image.data).enumerated().allSatisfy { index, pair in pair.0 == pair.1 || allowed.contains(index) })
    }
}

@Test func profileFirmwareRejectsCodePaddingAndLiveFieldRecordDisagreement() throws {
    let profile = try #require(LensLibrary.seeds().profiles.first { $0.id == "contax-zeiss-35-f1-4" })
    let image = try FirmwareImageBuilder.prepare(profile: profile)
    for offset in [64, LensProfileImage.focalOffset, LensProfileImage.startupOffset,
                   LensProfileImage.nameOffset, 0x4ee0, LensProfileImage.recordOffset+12, 20479] {
        var damaged = image; damaged[offset] ^= 1
        #expect(throws: DeviceError.self) { try LensProfileImage.setting(in: damaged) }
    }
    var other = profile; other.minimumFocalLengthMM = 85; other.maximumFocalLengthMM = 85
    let otherSetting = try AdapterLensSetting(profile: other)
    var staleFields = image
    staleFields.replaceSubrange(LensProfileImage.recordOffset..<20480, with: try otherSetting.encoded())
    #expect(throws: DeviceError.self) { try LensProfileImage.setting(in: staleFields) }
}

@Test func profileStartupRequiresDialRangeAndSelectedZoom() throws {
    let seeds = try LensLibrary.seeds()
    let zoom = try #require(seeds.profiles.first { $0.kind == .zoom })
    #expect(throws: DeviceError.self) { try FirmwareImageBuilder.prepare(profile: zoom) }
    var profile = seeds.profiles[0]; profile.currentAperture = 32
    #expect(throws: DeviceError.self) { try FirmwareImageBuilder.prepare(profile: profile) }
}

@Test func mismatchedSavedProfileCannotMasqueradeAsVerifiedAdapterData() throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let seeds = try LensLibrary.seeds()
    let first = try ApplicationImage.personalized(seeds.profiles[0], variant: .lensProfiles)
    let other = try AdapterLensSetting(profile: seeds.profiles[1])
    let device = DeviceIdentity(id: 1, product: "LM-EA9", manufacturer: "TECHART", serial: "CACHE-TEST", location: 0, qualifiedDescriptor: true)
    let store = UpdateStore(directory: folder)
    try store.saveApplied(AppliedLens(device: device, setting: other, firmwareVersion: "4.7.0",
        imageSHA256: digest(first.data), verifiedAt: Date()))
    #expect(throws: DeviceError.self) { try store.loadApplied() }
    #expect(FileManager.default.fileExists(atPath: store.appliedFile.path))
}
