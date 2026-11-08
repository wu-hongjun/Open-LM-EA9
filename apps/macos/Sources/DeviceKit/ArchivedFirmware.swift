import Foundation

/// Read/verification compatibility for archived journals; no retired images are bundled.
enum ArchivedFirmware {
    struct Entry { let codeBytes: Int; let imageBytes: Int; let codeSHA: String; let profiled: Bool; let probe: Bool; let november: Bool }
    static let entries: [String: Entry] = [
        "2.0.0": Entry(codeBytes: 20480, imageBytes: 20736, codeSHA: "bf949a3c34f5b1a9261fcd9487e8b4b0185f7772595f74059d8397233f54d965", profiled: true, probe: false, november: false),
        "2.1.0": Entry(codeBytes: 20480, imageBytes: 20736, codeSHA: "30493051dcf99f92b8e114bd61c8d368ff967a86133adddc3f64b9fa73772efe", profiled: true, probe: false, november: false),
        "2.2.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "e012162c32c442ce9e739f042a8739a5c69628a0fa7f62b195cffb483ade3c9e", profiled: true, probe: false, november: false),
        "2.3.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "e64c5d741b252030f01c0ef6aface4804c9dafbf2dd4024a9a655fde8b483b5c", profiled: true, probe: false, november: false),
        "2.4.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "d17d4aa91b00f6f0743ab5acb3a7a32cf3ad258f138c16af521ad6d352e3147e", profiled: true, probe: false, november: false),
        "2.5.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "e086925dd6984608dbe17359989e62e2f492d8c6c1be80c684eead65fb9a6c3f", profiled: true, probe: false, november: false),
        "2.6.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "e7d578b1cc649975fcebedcf2002f6307c6a9fd9c13fdab1e3d66347b126b219", profiled: true, probe: false, november: false),
        "2.7.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "e28fe8ec3d74a3e3c0e1617cbbc00e47ab26364783dd5e89daebe5dfb0dfc906", profiled: true, probe: false, november: false),
        "2.8.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "8f90e316c1563d3640e423250297de71a07254ca791ffb3781f8757fcffa9db3", profiled: true, probe: false, november: false),
        "2.9.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "aec4af25e9de1adf45339311b119f770427e88cc130a38fff99ae682d668dfac", profiled: true, probe: false, november: false),
        "3.0.0": Entry(codeBytes: 20224, imageBytes: 20480, codeSHA: "396e9daf48fe6427dc0c8dc67ec6f2e409fb33ffdd85884fece5f4af95d21c9a", profiled: true, probe: false, november: false),
        "3.1.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "528225e6f6472da0d92479da2b3e475a32f82735347231b6dc7c3d0dc7e8b39f", profiled: false, probe: false, november: false),
        "3.2.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df", profiled: false, probe: false, november: false),
        "3.3.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "adc4b5de9a717b1a573425006ef565962bf5c56ab2233a4eca9192feb7ad11cd", profiled: false, probe: false, november: false),
        "3.4.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9", profiled: false, probe: false, november: false),
        "3.5.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632", profiled: false, probe: false, november: false),
        "3.6.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f", profiled: false, probe: false, november: false),
        "3.7.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5", profiled: false, probe: false, november: false),
        "3.8.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9", profiled: false, probe: false, november: false),
        "3.9.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44", profiled: false, probe: false, november: false),
        "4.0.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae", profiled: false, probe: false, november: false),
        "4.1.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641", profiled: false, probe: false, november: false),
        "4.2.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "2a11822d47672355455dc4415db95f1487527e4f9865270ea368f24fc0ceaa7b", profiled: false, probe: false, november: true),
        "4.3.0": Entry(codeBytes: 20480, imageBytes: 20480, codeSHA: "58e5eb9578732e6fa8113a28f8b1732a6edc30706333871bbc207ae66e20abac", profiled: false, probe: true, november: false),
    ]
    static func validate(_ record: PendingUpdate) throws {
        let version = record.version.map(String.init).joined(separator: ".")
        guard let entry = entries[version], record.image.count == entry.imageBytes,
              digest(Data(record.image.prefix(entry.codeBytes))) == entry.codeSHA else {
            throw DeviceError.failure("Archived update image does not match its original pin. Files were preserved.")
        }
        if entry.profiled {
            guard try AdapterLensSetting.decode(Data(record.image.suffix(256))) == record.setting else {
                throw DeviceError.failure("Archived lens settings do not match their saved profile.")
            }
        } else if entry.probe {
            guard record.setting == nil else { throw DeviceError.failure("Archived startup probe has no lens setting.") }
        } else {
            let av: UInt16 = entry.november ? 4544 : 4352
            guard let setting = record.setting, setting.focalMM10 == 500,
                  setting.maximumAV == av, setting.reportedAV == av, setting.revision == 1,
                  setting.id == (entry.november ? "upstream-november-50-f1-8" : "contax-zeiss-50-f1-4"),
                  setting.name == (entry.november ? "Upstream 50mm f/1.8" : "Contax Zeiss 50mm f/1.4") else {
                throw DeviceError.failure("Archived compiled lens setting is inconsistent.")
            }
        }
    }
}

func recognizedFirmwareVersion(_ version: String) -> Bool {
    version == "1.8.0" || version == ProfileBank.version || FirmwareVariant.allCases.contains { $0.versionString == version } || ArchivedFirmware.entries[version] != nil
}
