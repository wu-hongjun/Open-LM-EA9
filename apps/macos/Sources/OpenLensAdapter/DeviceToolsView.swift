import SwiftUI
import AppKit
import DeviceKit

struct DeviceToolsView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("USB tools").font(.title2.weight(.semibold))
                Spacer()
                Button("Done") { model.showDeviceTools = false }.disabled(model.busy)
            }.padding(26)
            Divider()
            if model.busy, let p = model.progress {
                VStack(alignment: .leading, spacing: 10) {
                    Text(p.phase).font(.callout)
                    ProgressView(value: p.fraction)
                    if model.canCancelRead { Button("Cancel read", action: model.cancelBackup) }
                }.padding(26)
            }
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    StatusPill(text: model.connectionLabel, connected: model.adapterConnected)
                    if model.isPreview { Text("Preview mode · all USB actions disabled").font(.caption).foregroundStyle(Palette.muted) }
                    if model.needsWorkflowBanner { Text(model.workflowDetail).font(.callout).foregroundStyle(Palette.muted) }
                    if let error = model.updateStateError { Text(error).font(.caption).foregroundStyle(.orange) }
                    VStack(alignment: .leading, spacing: 12) {
                        Toggle("Updater closed · USB cap reconnected", isOn: $model.idleAcknowledged)
                            .disabled(model.busy || model.reconnectRequired || !model.adapterConnected || model.isPreview)
                        Text("A physical reconnect is required after every firmware upload, before any read-back.").font(.caption).foregroundStyle(Palette.muted)
                        HStack {
                            Button("Read adapter information", action: model.readAdapterLens).buttonStyle(.borderedProminent)
                                .disabled(!model.canReadDevice || model.updateStateError != nil || model.waitingForVerification)
                            Button("Read version", action: model.readFirmware).disabled(!model.canReadDevice)
                        }
                        if model.waitingForVerification {
                            Button("Verify changes", action: model.verifyLensUpdate).buttonStyle(.borderedProminent).disabled(!model.canRequestVerification)
                        }
                    }.padding(20).modifier(Surface())
                    DisclosureGroup("Firmware updates") { firmwareSection.padding(.top, 12) }.padding(20).modifier(Surface())
                    VStack(alignment: .leading, spacing: 12) {
                        Label("Keep a backup", systemImage: "externaldrive").font(.headline)
                        Text("Two full reads are compared before your private backup is saved.").font(.callout).foregroundStyle(Palette.muted)
                        Button("Create verified backup…", action: model.chooseBackup).disabled(!model.canReadDevice)
                        if let result = model.lastBackup {
                            Label("Backup verified", systemImage: "checkmark.seal.fill").foregroundStyle(Palette.accent)
                            Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([result.url]) }
                        }
                    }.padding(20).modifier(Surface())
                    DisclosureGroup("Recovery") {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Restoring stock 1.8.0 requires this adapter’s original verified backup.").font(.caption).foregroundStyle(Palette.muted)
                            Button("Restore original stock…", action: model.chooseStockRestore).disabled(!model.canReadDevice)
                            Button("Restore pre-bank firmware…", action: model.rollbackBank).disabled(!model.canRollbackBank)
                            if !model.stockUploadQualified {
                                Button("Verify stock upload path…", action: model.prepareAdapter).disabled(!model.canReadDevice || model.waitingForVerification || model.updateStateError != nil)
                            }
                        }.padding(.top, 12)
                    }.padding(20).modifier(Surface())
                }.padding(26)
            }
        }.frame(width: 640, height: 670).background(Palette.canvas)
    }
    private var firmwareSection: some View {
        VStack(alignment: .leading, spacing: 13) {
            Text("4.8.0 · Lens bank").font(.callout.weight(.medium))
            Text("One installation, then metadata-only profile switching. Hardware qualification is pending.").font(.caption).foregroundStyle(Palette.muted)
            Button(model.bankActionLabel,action: model.performPreparedBankAction).disabled(!model.canUseBankAction)
            Divider()
            Text("4.5.0 · Working baseline").font(.callout.weight(.medium))
            Text("\(FirmwareVariant.cameraDialAperture.compiledLens.name) · \(FirmwareVariant.cameraDialAperture.apertureRangeLabel)").font(.caption).foregroundStyle(Palette.muted)
            if model.currentFirmwareVariant == .cameraDialAperture {
                Text("Installed").font(.caption).foregroundStyle(Palette.muted)
            } else {
                Button(model.currentFirmwareVariant == .wideCameraAperture ? "Restore working 4.5.0" : "Install 4.5.0", action: model.installBaseline)
                    .disabled(!model.canInstallBaseline)
            }
            Divider()
            Text("4.6.0 · Wider aperture range").font(.callout.weight(.medium))
            Text("Biotar image · reported f/1.2–f/22, starting at f/2. Camera checks remain incomplete.")
                .font(.caption).foregroundStyle(Palette.muted)
            if model.currentFirmwareVariant == .wideCameraAperture {
                Text("Installed").font(.caption).foregroundStyle(Palette.muted)
            } else {
                Button("Install 4.6.0 candidate…", action: model.installWideAperture).disabled(!model.canInstallWideAperture)
            }
            Divider()
            Button("Legacy per-lens firmware update…",action: model.applyPreparedLens).disabled(!model.canApplyLens)
            Text("4.7 fallback rewrites the application per lens. It does not switch bank settings.").font(.caption).foregroundStyle(Palette.muted)
        }
    }
}
