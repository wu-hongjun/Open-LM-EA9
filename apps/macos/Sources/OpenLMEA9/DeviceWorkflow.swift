import Foundation
import DeviceKit

enum DeviceLensAction {
    case setup, read, apply, verify, upToDate, tools
    var title: String {
        switch self {
        case .setup: "Set up adapter"
        case .read: "Read lens settings"
        case .apply: "Apply profile"
        case .verify: "Verify lens"
        case .upToDate: "Up to date"
        case .tools: "Open USB tools"
        }
    }
}

/// Product guidance derived from the same guards used by explicit USB actions.
/// Evaluating this state never reads or writes the adapter.
@MainActor extension AppModel {
    static let cameraFailureHolds = [
        "3.0.0": "AF 3.0 failed capture and shutdown testing with a full-press freeze requiring battery removal.",
        "3.1.0": "Upstream 3.1 failed camera testing: aperture showed -- and the shutter would not release. Shutdown worked.",
        "3.6.0": "Upstream AF 3.6 failed capture and shutdown testing: shutter press froze the camera and it did not shut down."
    ]
    var installedCameraFailureHold: Bool {
        Self.cameraFailureHolds[currentAppliedLens?.firmwareVersion ?? ""] != nil
    }
    var upstreamBaselineCameraFailureHold: Bool {
        Self.cameraFailureHolds[FirmwareVariant.autofocusUpstreamBaseline.versionString] != nil
    }
    var pendingBelongsToConnectedAdapter: Bool {
        guard let pendingUpdate, let device = devices.first, devices.count == 1 else { return false }
        return !device.serial.isEmpty && pendingUpdate.device.serial == device.serial
    }
    var primaryLensAction: DeviceLensAction {
        if updateStateError != nil || (waitingForVerification && devices.count == 1 && !pendingBelongsToConnectedAdapter) { return .tools }
        if waitingForVerification { return .verify }
        if installedCameraFailureHold { return .tools }
        if ["3.2.0", "3.3.0", "3.4.0", "3.5.0", "3.6.0"].contains(currentAppliedLens?.firmwareVersion ?? "") { return .tools }
        if !stockUploadQualified { return .setup }
        if variantForLensChanges == nil { return .read }
        if variantForLensChanges?.supportsLensProfileChanges == false && !preparedMatchesApplied { return .tools }
        return preparedMatchesApplied ? .upToDate : .apply
    }
    var canPerformPrimaryLensAction: Bool {
        switch primaryLensAction {
        case .setup: canReadDevice && updateStateError == nil
        case .read: canReadDevice && updateStateError == nil && !waitingForVerification
        case .apply: canApplyLens
        case .verify: canVerifyUpdate
        case .upToDate: false
        case .tools: !busy
        }
    }
    func performPrimaryLensAction() {
        guard canPerformPrimaryLensAction else { return }
        switch primaryLensAction {
        case .setup: prepareAdapter()
        case .read: readAdapterLens()
        case .apply: applyLens()
        case .verify: verifyLensUpdate()
        case .upToDate: break
        case .tools: showDeviceTools = true
        }
    }
    var workflowTitle: String {
        if busy { return isUploadingFirmware ? "Updating your adapter" : "Reading your adapter" }
        if discoveryError { return "Check the USB connection" }
        if devices.isEmpty { return "Connect your adapter" }
        if devices.count != 1 { return "Connect one adapter" }
        if devices.first?.qualifiedDescriptor != true { return "Adapter not recognized" }
        if updateStateError != nil { return "Review recovery options" }
        if waitingForVerification && !pendingBelongsToConnectedAdapter { return "Another adapter has an unfinished update" }
        if reconnectRequired || (waitingForVerification && pendingUpdate?.device.id == devices.first?.id) { return "Reconnect the USB cap" }
        if waitingForVerification { return "Verify your lens change" }
        if let version = currentAppliedLens?.firmwareVersion, Self.cameraFailureHolds[version] != nil {
            return "AF \(version.split(separator: ".").prefix(2).joined(separator: ".")) camera testing held"
        }
        if ["3.5.0", "3.6.0"].contains(currentAppliedLens?.firmwareVersion ?? "") { return "Upstream AF candidate" }
        if currentAppliedLens?.firmwareVersion == "3.4.0" { return "Bounded upstream candidate" }
        if currentAppliedLens?.firmwareVersion == "3.3.0" { return "Upstream hardening candidate" }
        if currentAppliedLens?.firmwareVersion == "3.2.0" { return "Startup diagnostic candidate" }
        if isDirty { return "Save your lens edits" }
        if loadError != nil { return "Recover your lens library" }
        if preparedLensIssue != nil { return "Finish this lens profile" }
        if primaryLensAction == .read { return "Read the saved lens settings" }
        if !stockUploadQualified { return "Set up this adapter once" }
        if preparedLens == nil { return "Choose your lens" }
        if variantForLensChanges?.supportsLensProfileChanges == false { return "Fixed 50mm upstream baseline" }
        if preparedMatchesApplied { return "Your lens profile is up to date" }
        if !idleAcknowledged { return "Confirm the USB connection" }
        return "Ready to switch lenses"
    }
    var workflowDetail: String {
        if busy { return progress?.phase ?? "Keep the USB cap connected until this operation finishes." }
        if discoveryError { return deviceMessage }
        if devices.isEmpty { return "Connect the LM-EA9 through its USB cap. Connection status updates automatically." }
        if devices.count != 1 { return "Disconnect the extra adapters before reading or changing settings." }
        if devices.first?.qualifiedDescriptor != true { return "This connection does not match the supported LM-EA9. USB actions are unavailable." }
        if updateStateError != nil { return "Local update history needs attention. Open USB tools to review the error and restore from a verified backup." }
        if waitingForVerification && !pendingBelongsToConnectedAdapter { return "Connect the adapter used for that update, or review its saved backup in USB tools." }
        if reconnectRequired || (waitingForVerification && pendingUpdate?.device.id == devices.first?.id) { return "Physically unplug and reconnect the cap. The app will detect the new connection." }
        if waitingForVerification { return "Confirm the updater is closed, then verify the uploaded settings before using the camera." }
        if let reason = Self.cameraFailureHolds[currentAppliedLens?.firmwareVersion ?? ""] {
            return reason + " Keep the camera off; open USB tools to review the verified image and backup."
        }
        if ["3.5.0", "3.6.0"].contains(currentAppliedLens?.firmwareVersion ?? "") { return "Camera compatibility remains unqualified. Save a read-only backup after one coordinated cycle for log review. The compiled lens is the original 50mm f/1.4 profile; actual iris position is unknown." }
        if currentAppliedLens?.firmwareVersion == "3.4.0" { return "Camera compatibility remains unqualified. After one coordinated cycle, save a read-only backup for log review. This candidate is compiled for the original 50mm f/1.4 profile; actual iris position is unknown." }
        if currentAppliedLens?.firmwareVersion == "3.3.0" { return "Camera compatibility remains unqualified. After one coordinated camera cycle, save a read-only backup for log review before another trial. Lens library edits stay local in this fixed 50mm build." }
        if currentAppliedLens?.firmwareVersion == "3.2.0" { return "Camera compatibility is unqualified. After one coordinated camera cycle, use USB tools to save a read-only backup for diagnostic decoding." }
        if isDirty { return "Save or discard the changes in the lens editor before applying a profile." }
        if loadError != nil { return "The saved library was preserved. Import a valid library from Lens Library to recover it." }
        if let issue = preparedLensIssue { return issue }
        if primaryLensAction == .read { return "Read the adapter once to identify its installed firmware and lens setting. Profile changes will preserve that firmware." }
        if !stockUploadQualified { return "A verified backup and stock upload check prepare this adapter for profile changes." }
        if preparedLens == nil { return "Choose a profile from the dropdown. The saved adapter setting stays visible above." }
        if variantForLensChanges?.supportsLensProfileChanges == false { return "This baseline is compiled for Contax Zeiss 50mm f/1.4. Library edits stay local; changing the adapter setting requires another firmware build." }
        if preparedMatchesApplied { return "The selected profile matches the last USB-verified setting. You can disconnect and use it on your camera." }
        if !idleAcknowledged { return "Close TECHART Update, reconnect the cap, then confirm the checkbox below." }
        return "Apply the selected profile, then reconnect to verify. The installed firmware is preserved."
    }
    var workflowSymbol: String {
        if busy { return "arrow.triangle.2.circlepath" }
        if installedCameraFailureHold { return "exclamationmark.triangle.fill" }
        if ["3.2.0", "3.3.0", "3.4.0", "3.5.0", "3.6.0"].contains(currentAppliedLens?.firmwareVersion ?? "") { return "waveform.path.ecg" }
        if preparedMatchesApplied && !waitingForVerification && !reconnectRequired { return "checkmark.circle.fill" }
        return "cable.connector"
    }
}
