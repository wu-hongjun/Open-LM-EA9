import Foundation

/// The bench image owns only two code segments and two initially erased trace slots.
struct MotionDiagnostic {
    static let version: [UInt8] = [4,8,1]
    static let traceRange = 0x14000..<0x16000
    static let applicationRange = 0x5000..<0x12000
    let application: Data
    let extensionCode: Data

    init() throws {
        func resource(_ name: String, size: Int, pin: String) throws -> Data {
            guard let url = Bundle.module.url(forResource: "ea9-motion481-" + name, withExtension: "bin") else {
                throw DeviceError.failure("The pinned motion diagnostic package is missing.")
            }
            let data = try Data(contentsOf: url)
            guard data.count == size, digest(data) == pin else {
                throw DeviceError.failure("Motion diagnostic package pin failed.")
            }
            return data
        }
        application = try resource("application", size: 0x5000,
            pin: "3ed4b7c56581dcfb472a9f1639616188fd19e7deed7d21be6f910c3308b87809")
        extensionCode = try resource("extension", size: 0x2000,
            pin: "fe8b7d2db469947d83bdbb672f849b3f33da984ccd63bd6128657dd3870c475a")
    }

    func inspect(flash: Data) throws -> ProfileBankState {
        let bank = try ProfileBank()
        guard flash.count == 0x20000, flash[0x4000..<0x4003] == Data(Self.version),
              flash[0x5000..<0xa000] == application, flash[0x10000..<0x12000] == extensionCode,
              flash[0x12000..<0x13000] == bank.bytes else {
            throw DeviceError.failure("Installed 4.8.1 code or bank does not match the pinned diagnostic.")
        }
        return try bank.inspectSettings(flash: flash)
    }
}
