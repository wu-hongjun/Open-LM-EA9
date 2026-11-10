import Foundation
import DeviceKit

/// Pure presentation state. Evaluating it never opens USB or issues a report.
@MainActor extension AppModel {
    var pendingBelongsToConnectedAdapter: Bool {
        guard let activePendingDevice, devices.count == 1, let device = devices.first else { return false }
        return !device.serial.isEmpty && activePendingDevice.serial == device.serial
    }
    var firmwareHistoryCaption: String? {
        if let observation = currentBankObservation { return "Read " + observation.readAt.formatted(date: .abbreviated,time: .shortened) }
        if let applied = currentAppliedLens { return "Verified " + applied.verifiedAt.formatted(date: .abbreviated, time: .shortened) }
        if let observation = currentFirmwareObservation { return "Read " + observation.readAt.formatted(date: .abbreviated, time: .shortened) }
        return nil
    }
    var emptyLensMessage: String {
        if waitingForVerification { return "Verify the uploaded firmware first." }
        return adapterConnected ? "Read the adapter in USB tools." : "Connect the adapter through its USB cap."
    }
    var canCancelRead: Bool { busy && !isUploadingFirmware }
    var adapterConnected: Bool { devices.count == 1 && devices.first?.qualifiedDescriptor == true && !discoveryError }
    var isArchivedFirmware: Bool {
        guard let version = currentFirmwareObservation?.version else { return false }
        return version != "1.8.0" && version != ProfileBank.version && version != ProfileBank.motionDiagnosticVersion &&
            !FirmwareVariant.allCases.contains { $0.versionString == version }
    }
    var workflowTitle: String {
        if busy { return isUploadingFirmware ? "Updating your adapter" : "Reading your adapter" }
        if discoveryError { return "Check the USB connection" }
        if devices.isEmpty { return "Connect your adapter" }
        if devices.count != 1 { return "Connect one adapter" }
        if devices.first?.qualifiedDescriptor != true { return "Adapter not recognized" }
        if updateStateError != nil { return "Review USB history" }
        if waitingForVerification && !pendingBelongsToConnectedAdapter { return "Another adapter has an unfinished update" }
        if reconnectRequired || (waitingForVerification && activePendingDevice?.id == devices.first?.id) { return "Reconnect the USB cap" }
        if waitingForVerification { return pendingUpdate?.needsVerification == true ? "Verify the uploaded firmware" : "Verify profile settings" }
        if motionDiagnosticInstalled { return "Motion diagnostic installed" }
        if let state = currentBankState { return state.pendingCameraBoot ? "Profile saved for next camera startup" : "Your lens bank is ready" }
        if isArchivedFirmware { return "Archived firmware detected" }
        if currentFirmwareVariant == .cameraDialAperture { return "Your adapter is ready" }
        if currentFirmwareVariant == .lensProfiles { return "Your lens profile is ready" }
        if currentFirmwareVariant == .wideCameraAperture { return "Wide aperture candidate installed" }
        if currentFirmwareVariant == .upstreamStockSpeed { return "Ready for the 4.5 baseline" }
        return "Read your adapter once"
    }
    var workflowDetail: String {
        if busy { return progress?.phase ?? "Keep the USB cap connected until this operation finishes." }
        if discoveryError { return deviceMessage }
        if devices.isEmpty { return "Connect the LM-EA9 through its USB update cap. Connection status refreshes automatically." }
        if devices.count != 1 { return "Disconnect the extra adapters before using USB tools." }
        if devices.first?.qualifiedDescriptor != true { return "This USB connection does not match the supported LM-EA9." }
        if updateStateError != nil { return "Saved history was preserved. Open USB tools to review it or restore a verified stock backup." }
        if waitingForVerification && !pendingBelongsToConnectedAdapter { return "Connect the adapter used for that upload." }
        if reconnectRequired || (waitingForVerification && activePendingDevice?.id == devices.first?.id) { return "Physically unplug and reconnect the cap before reading it again." }
        if waitingForVerification { return "Verify the complete image before moving the adapter to your camera." }
        if currentBankState != nil { return bankActionHint }
        if isArchivedFirmware { return "Earlier experiments are retired. Backup and stock recovery remain available; no retired image can be installed here." }
        if currentFirmwareVariant != nil { return firmwareBehaviorNote }
        return "Open USB tools to read firmware and lens information."
    }
    var workflowSymbol: String {
        if busy { return "arrow.triangle.2.circlepath" }
        if reconnectRequired || waitingForVerification { return "cable.connector" }
        if currentFirmwareVariant == .cameraDialAperture { return "checkmark.circle.fill" }
        return adapterConnected ? "info.circle" : "cable.connector"
    }
    var needsWorkflowBanner: Bool { busy || reconnectRequired || waitingForVerification || updateStateError != nil || discoveryError || isArchivedFirmware }
    func cameraMetadataSummary(_ setting: AdapterLensSetting) -> String {
        if let variant = currentFirmwareVariant, variant != .upstreamStockSpeed {
            return "\(setting.focalLengthMM.formatted()) mm · startup f/\(setting.apertureLabel) · Sony dial \(variant.apertureRangeLabel)"
        }
        return "\(setting.focalLengthMM.formatted()) mm · reported f/\(setting.apertureLabel)"
    }
}
