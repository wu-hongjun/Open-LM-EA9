import Foundation
import AppKit
import CryptoKit
import LensCore
import DeviceKit

/// Isolated visual fixtures. No preview action can open USB.
@MainActor enum AppPreview {
    static func make(_ mode: String, directory: URL) -> AppModel {
        do {
            if mode == "dark" { NSApp.appearance = NSAppearance(named: .darkAqua) }
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let identity: [String: Any] = ["id": mode == "verify" ? 72 : 71, "product": "LM-EA9",
                "manufacturer": "TECHART", "serial": "PREVIEW-ONLY", "location": 0, "qualifiedDescriptor": true]
            let device = try JSONDecoder().decode(DeviceIdentity.self, from: JSONSerialization.data(withJSONObject: identity))
            let seeds = try LensLibrary.seeds()
            let biotar = seeds.profiles.first { $0.id == "zeiss-jena-biotar-55-f2" }!
            let distagon = seeds.profiles.first { $0.id == "contax-zeiss-35-f1-4" }!
            let selected = mode == "profile" ? distagon : biotar
            let setting = try AdapterLensSetting(profile: selected)
            let variant: FirmwareVariant = mode == "profile" ? .lensProfiles : .wideCameraAperture
            let data = try FirmwareImageBuilder.prepare(profile: selected, variant: variant)
            let hash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
            let settingJSON = try JSONSerialization.jsonObject(with: JSONEncoder().encode(setting))
            let now = Date().timeIntervalSinceReferenceDate
            if mode != "disconnected" {
                let record: [String: Any] = ["device": identity, "setting": settingJSON,
                    "firmwareVersion": variant.versionString, "imageSHA256": hash, "verifiedAt": now]
                try JSONSerialization.data(withJSONObject: record).write(to: directory.appendingPathComponent("applied-lens.json"))
                try FirmwareObservationStore(directory: directory).save(FirmwareObservation(device: device, version: variant.versionString))
                let qualification: [String: Any] = ["serial": "PREVIEW-ONLY",
                    "bootCodeSHA256": "8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895",
                    "transactionID": UUID().uuidString, "verifiedAt": now]
                try JSONSerialization.data(withJSONObject: qualification).write(to: directory.appendingPathComponent("stock-upload-qualification.json"))
            }
            if mode == "verify" {
                var old = identity; old["id"] = 71
                let image = try FirmwareImageBuilder.prepare(profile: distagon)
                let chosen = try JSONSerialization.jsonObject(with: JSONEncoder().encode(AdapterLensSetting(profile: distagon)))
                let record: [String: Any] = ["transactionID": UUID().uuidString, "device": old,
                    "backupURL": "file:///PREVIEW-ONLY.ea9backup", "image": image.base64EncodedString(),
                    "version": [4,7,0], "setting": chosen, "createdAt": now, "uploadedAt": now,
                    "imageSHA256": SHA256.hash(data: image).map { String(format: "%02x", $0) }.joined(),
                    "expectedMetadata": Data([4,7,0] + [UInt8](repeating: 0, count: 55)).base64EncodedString()]
                try JSONSerialization.data(withJSONObject: record).write(to: directory.appendingPathComponent("pending-update.json"))
            }
            let model = AppModel(directory: directory, preview: true,
                inventory: { mode == "disconnected" ? [] : [device] }, reconnect: { _ in mode == "reconnect" })
            if ["selected","verify","profile","disconnected"].contains(mode) { model.chooseDeviceLens(distagon.id) }
            return model
        } catch { fatalError("Cannot create offline preview fixture: \(error)") }
    }
}
