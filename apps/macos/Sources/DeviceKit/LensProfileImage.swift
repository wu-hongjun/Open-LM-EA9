import Foundation

/// Personalization of the pinned 4.7 template, never an arbitrary image patcher.
enum LensProfileImage {
    static let sha256 = "5b5267d8a25e0fbad0de2f5072455dc838bf217e9cbcb602c8985c2d24537344"
    static let focalOffset = 15786
    static let startupOffset = 15784
    static let nameOffset = 19115
    static let recordOffset = 20224

    static func image(for setting: AdapterLensSetting) throws -> Data {
        let record = try setting.encoded()
        guard (4224...6400).contains(setting.reportedAV) else {
            throw DeviceError.failure("The startup aperture must be within the Sony dial range f/1.2–f/22.")
        }
        var data = try ApplicationImage.template(.lensProfiles)
        func word(_ value: UInt16, at offset: Int) {
            data[offset] = UInt8(truncatingIfNeeded: value)
            data[offset+1] = UInt8(value >> 8)
        }
        word(setting.focalMM10, at: focalOffset)
        word(setting.reportedAV, at: startupOffset)
        let name = Array(setting.name.utf8)
        data.replaceSubrange(nameOffset..<(nameOffset+64), with: name + [UInt8](repeating: 0, count: 64-name.count))
        data.replaceSubrange(recordOffset..<(recordOffset+256), with: record)
        return data
    }

    static func setting(in image: Data) throws -> AdapterLensSetting {
        guard image.count == 20480 else { throw DeviceError.failure("Invalid profile firmware size.") }
        let setting = try AdapterLensSetting.decode(Data(image[recordOffset..<(recordOffset+256)]))
        // Rebuilding the entire image binds all three live fields to the record and
        // rejects any other code, data, padding or record modification.
        guard image == (try self.image(for: setting)) else {
            throw DeviceError.failure("Lens firmware differs from the pinned template or its saved profile.")
        }
        return setting
    }
}
