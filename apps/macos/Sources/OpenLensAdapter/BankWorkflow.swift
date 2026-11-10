import AppKit
import DeviceKit
import LensCore

/// Bank UI owns no transport. Dropdowns stay local until a concrete plan is reviewed.
@MainActor extension AppModel {
    var currentBankObservation: BankObservation? {
        if isPreview,let previewBankObservation { return previewBankObservation }
        guard updateStateError == nil,!waitingForVerification,!discoveryError,devices.count == 1,
              let device = devices.first,let bankObservation,bankObservation.belongs(to: device) else { return nil }
        if let observation = currentFirmwareObservation,observation.readAt >= bankObservation.readAt,
           observation.version != bankObservation.version { return nil }
        return bankObservation
    }
    var currentBankState: ProfileBankState? { currentBankObservation?.state }
    var motionDiagnosticInstalled: Bool { currentBankObservation?.version == ProfileBank.motionDiagnosticVersion }
    var activePendingDevice: DeviceIdentity? {
        if pendingUpdate?.needsVerification == true { return pendingUpdate?.device }
        return pendingBank?.needsVerification == true ? pendingBank?.device : nil
    }
    var bankSelectionMatches: Bool {
        guard let profile = preparedLens ?? deviceLensPreview,let state = currentBankState,
              let slot = try? ProfileBank().slot(for: profile) else { return false }
        return slot == state.request.slot
    }
    var canUseBankAction: Bool {
        guard canRequestDeviceRead,updateStateError == nil,loadError == nil,!waitingForVerification,!motionDiagnosticInstalled,
              stockUploadQualified,!isDirty,let profile = deviceLensPreview,
              (try? ProfileBank().slot(for: profile)) != nil,
              currentBankObservation?.device.id == devices.first?.id else { return false }
        return currentBankState == nil || !bankSelectionMatches
    }
    var bankActionLabel: String {
        if waitingForVerification { return "Reconnect and verify" }
        if motionDiagnosticInstalled { return "Motion diagnostic" }
        guard let state = currentBankState else { return "Install lens bank…" }
        if bankSelectionMatches { return state.pendingCameraBoot ? "Waiting for camera" : "Configured" }
        return bankTransportQualified ? "Switch profile…" : "Test profile switch…"
    }
    var bankActionHint: String {
        if busy || waitingForVerification || reconnectRequired { return workflowDetail }
        guard adapterConnected else { return "Connect the adapter through its USB cap." }
        if motionDiagnosticInstalled { return "Read the motion trace through the CLI after the camera test." }
        if let state = currentBankState {
            if let issue = preparedLensIssue { return issue }
            if currentBankObservation?.device.id != devices.first?.id { return "Read the adapter to refresh its stored selection." }
            if bankSelectionMatches {
                return state.pendingCameraBoot ? "Saved for next camera power-on. Read again after camera use to verify it was applied." : "This profile is already stored on the adapter."
            }
            return bankTransportQualified ? "Switching updates metadata only. Reconnect and verify afterward." :
                "The first metadata-only switch is an experimental test. Reconnect verification checks all firmware and protected data."
        }
        if currentBankObservation?.device.id != devices.first?.id { return "Read the adapter before reviewing the one-time bank installation." }
        if !stockUploadQualified { return "Open USB tools to verify this adapter’s upload path first." }
        if let profile = deviceLensPreview,let bank = try? ProfileBank(),(try? bank.slot(for: profile)) == nil {
            return "This profile is not in the bank. Edited metadata and zoom settings need a separate bank update."
        }
        return "Install 4.8 once; later profile switches update metadata. This candidate still needs hardware testing."
    }
    func performPreparedBankAction() {
        guard canUseBankAction,let profile = deviceLensPreview else { return }
        performBankChange(currentBankState == nil ? .install : .select,profile: profile)
    }
    var canRollbackBank: Bool { canRequestDeviceRead && currentBankState != nil && !motionDiagnosticInstalled && !waitingForVerification && updateStateError == nil }
    func rollbackBank() { guard canRollbackBank else { return }; performBankChange(.rollback,profile: nil) }
    private func performBankChange(_ operation: BankOperation,profile: LensCore.LensProfile?) {
        guard canRequestDeviceRead,updateStateError == nil,!waitingForVerification,let target = devices.first else { return }
        let preview: BankPreview
        do { preview = try deviceService.previewBank(operation: operation,profile: profile,device: target) }
        catch { errorMessage = error.localizedDescription; return }
        guard preview.requiresWrite else { return }
        let experimental = operation == .install || (operation == .select && !bankTransportQualified)
        let alert = NSAlert()
        switch operation {
        case .install:
            alert.messageText = "Install the 4.8 lens bank?"
            alert.informativeText = "\(preview.profile?.name ?? "Selected lens"). This writes \(preview.applicationBytes.formatted()) application bytes, initializes settings and transfers the mailbox to 4.8. Existing gap data and the original metadata are saved for rollback. This candidate has not been camera-tested."
        case .select:
            alert.messageText = "\(experimental ? "Test switching" : "Switch") to \(preview.profile?.name ?? "this profile")?"
            alert.informativeText = "One metadata report; no firmware pages. The new profile is applied at the next camera power-on.\(experimental ? " This first switch is a hardware qualification test." : "")"
        case .rollback:
            alert.messageText = "Restore the pre-bank firmware?"
            alert.informativeText = "Restore this adapter’s saved pre-bank application, upper-flash contents and original metadata. The rollback writes \(preview.applicationBytes.formatted()) application bytes."
        case .motionDiagnostic: return
        }
        alert.informativeText += "\n\nA fresh verified backup is checked against this plan before writing. Keep TECHART Update closed. Physically reconnect afterward, then verify before camera use."
        alert.addButton(withTitle: operation == .select ? (experimental ? "Run Test" : "Switch Profile") : operation == .install ? "Install Candidate" : "Restore")
        alert.addButton(withTitle: "Cancel")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        guard devices.first == target,canRequestDeviceRead,!waitingForVerification else { idleAcknowledged = false; return }
        idleAcknowledged = true
        runLensOperation(writing: true) { device,token in
            _ = try await self.deviceService.performBank(operation: operation,profile: profile,
                approvedDigest: preview.approvalDigest,experimentalAcknowledged: experimental,device: device,
                idleAcknowledged: self.idleAcknowledged,cancellation: token,
                progress: { value in Task { @MainActor in self.progress = value } })
            self.pendingBank = try self.deviceService.pendingBankTransaction()
            self.deviceMessage = "Unplug and reconnect the USB cap, then verify the complete transaction."
        }
    }
    func verifyBankChange() {
        guard canReadDevice,pendingBank?.needsVerification == true,activePendingDevice?.id != devices.first?.id,
              activePendingDevice?.serial == devices.first?.serial else { return }
        runLensOperation { device,token in
            self.bankObservation = try await self.deviceService.verifyBank(device: device,idleAcknowledged: self.idleAcknowledged,
                cancellation: token,progress: { value in Task { @MainActor in self.progress = value } })
            self.pendingBank = try self.deviceService.pendingBankTransaction()
            self.deviceMessage = self.bankObservation?.state?.pendingCameraBoot == true ?
                "Metadata verified. The selected profile will apply at next camera power-on." : "Bank transaction verified."
        }
    }
}
