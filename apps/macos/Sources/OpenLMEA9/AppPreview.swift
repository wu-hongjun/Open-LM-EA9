import Foundation
import AppKit
import DeviceKit

/// Offline visual fixtures. Every USB action is disabled in preview mode.
@MainActor enum AppPreview {
    static func make(_ mode: String, directory: URL) -> AppModel {
        do {
            if mode == "dark" { NSApp.appearance = NSAppearance(named: .darkAqua) }
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let identity: [String: Any] = ["id": 71, "product": "LM-EA9", "manufacturer": "TECHART", "serial": "PREVIEW-ONLY", "location": 0, "qualifiedDescriptor": true]
            let device = try JSONDecoder().decode(DeviceIdentity.self, from: JSONSerialization.data(withJSONObject: identity))
            let variant: FirmwareVariant = mode == "wide" ? .wideCameraAperture : .cameraDialAperture
            if mode != "disconnected" {
                let record: [String: Any] = ["device": identity,
                    "setting": ["id": "zeiss-jena-biotar-55-f2", "name": "Zeiss Jena Biotar 58mm f/2", "focalMM10": 580, "maximumAV": 4608, "reportedAV": 4608, "revision": 1],
                    "firmwareVersion": variant.versionString, "imageSHA256": variant.imageSHA256,
                    "verifiedAt": Date().timeIntervalSinceReferenceDate]
                try JSONSerialization.data(withJSONObject: record).write(to: directory.appendingPathComponent("applied-lens.json"))
                try FirmwareObservationStore(directory: directory).save(FirmwareObservation(device: device, version: variant.versionString))
            }
            return AppModel(directory: directory, preview: true,
                inventory: { mode == "disconnected" ? [] : [device] }, reconnect: { _ in mode == "reconnect" })
        } catch { fatalError("Cannot create offline preview fixture: \(error)") }
    }
}
