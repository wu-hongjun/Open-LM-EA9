import Foundation

/// Publishes a complete, verified read-back rather than retaining a stale profile.
/// The input is already a two-pass, unit-bound backup; this layer has no USB access.
enum LensInspection {
    static func publish(_ backup: VerifiedBackup, to store: UpdateStore) throws -> AppliedLens? {
        let result = backup.result, version = result.manifest.reportedFirmwareVersion
        try store.archiveAppliedBeforeInspection()
        try FirmwareObservationStore(directory: store.directory).save(FirmwareObservation(
            device: result.manifest.device, version: version, readAt: result.manifest.createdAt))
        if version == "1.8.0" {
            guard digest(Data(backup.flash[ApplicationImage.base..<(ApplicationImage.base + 20172)]))
                    == "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564" else {
                throw DeviceError.failure("The reported stock version does not match the supported stock application. The backup was preserved; no lens setting was verified.")
            }
            return nil
        }
        guard let variant = try ApplicationImage.installedVariant(backup.flash),
              let setting = try ApplicationImage.installedSetting(backup.flash),
              version == variant.versionString else {
            throw DeviceError.failure("The application does not match a supported lens firmware image. The backup was preserved; no lens setting was verified.")
        }
        let applied = AppliedLens(device: result.manifest.device, setting: setting, firmwareVersion: version,
                                  imageSHA256: digest(Data(backup.flash[ApplicationImage.base..<variant.applicationEnd])),
                                  verifiedAt: result.manifest.createdAt)
        try store.saveApplied(applied)
        return applied
    }
}
