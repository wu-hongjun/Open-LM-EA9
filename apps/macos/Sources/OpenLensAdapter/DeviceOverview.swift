import SwiftUI
import LensCore
import DeviceKit

struct DeviceView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        ScrollView {
            VStack(spacing: 18) {
                if model.needsWorkflowBanner { statusBanner }
                HStack(alignment: .top, spacing: 20) {
                    adapterCard
                    lensCard
                }
            }.padding(28).frame(maxWidth: 1040).frame(maxWidth: .infinity)
        }
    }
    private var adapterCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Adapter").font(.headline)
                Spacer()
                StatusPill(text: model.connectionLabel, connected: model.adapterConnected)
            }.frame(height: 32)
            ProductPhoto(id: "lm-ea9", height: 132).padding(.vertical, 4)
            Text("Techart LM-EA9").font(.system(size: 23, weight: .medium))
            Divider()
            infoRow("Status", model.adapterStateText)
            infoRow("Firmware", model.adapterFirmwareText)
            VStack(alignment: .leading, spacing: 5) {
                Text("Profile on adapter").font(.caption).foregroundStyle(Palette.muted)
                Text(model.installedProfileText).font(.callout.weight(.medium)).fixedSize(horizontal: false, vertical: true)
            }
            if let caption = model.firmwareHistoryCaption {
                Text("Last " + caption.prefix(1).lowercased() + caption.dropFirst())
                    .font(.caption).foregroundStyle(Palette.muted)
            }
            Spacer(minLength: 0)
            HStack {
                if model.waitingForVerification {
                    Button("Verify profile", action: model.verifyFromCard)
                        .buttonStyle(.borderedProminent).disabled(!model.canRequestVerification)
                } else {
                    Button("Read adapter", action: model.readAdapterFromCard)
                        .buttonStyle(.borderedProminent)
                        .disabled(!model.canRequestDeviceRead || model.updateStateError != nil)
                }
                Spacer()
                Button { model.showDeviceTools = true } label: { Image(systemName: "ellipsis") }
                    .buttonStyle(.bordered).help("Backups, firmware and recovery").accessibilityLabel("USB tools")
            }.controlSize(.large)
            Text("Connection refreshes automatically. Read refreshes adapter information.")
                .font(.caption).foregroundStyle(Palette.muted)
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading).frame(minHeight: 540).modifier(Surface())
    }
    private var lensCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Lens").font(.headline)
                Spacer()
                Text(model.selectedLensState).font(.caption).foregroundStyle(Palette.muted)
            }.frame(height: 32)
            ProductPhoto(id: model.deviceLensPreview?.id ?? "", height: 132).padding(.vertical, 4)
            Picker("Lens profile", selection: Binding(
                get: { model.deviceLensSelectionID },
                set: { model.chooseDeviceLens($0) })) {
                Text("Choose a lens…").tag(String?.none)
                ForEach(model.library.profiles) { profile in
                    Text(profile.displayName).tag(Optional(profile.id))
                }
            }.pickerStyle(.menu).labelsHidden().controlSize(.large)
                .frame(maxWidth: .infinity).accessibilityLabel("Lens profile")
                .disabled(model.busy || model.isDirty || model.waitingForVerification)
            if let profile = model.deviceLensPreview {
                LensNumbers(profile: profile)
                if profile.kind == .zoom {
                    infoRow("Zoom setting", profile.activeFocalLengthMM.map { "\($0.formatted()) mm" } ?? "Choose in Edit")
                }
                Divider()
                infoRow("Sony aperture dial", model.preparedMatchesApplied || model.preparedLensID == nil
                    ? model.currentFirmwareVariant?.apertureRangeLabel ?? "f/1.2–f/22" : "f/1.2–f/22")
                infoRow("Physical aperture", "Unknown")
                Text("Use the lens ring to control the iris.").font(.caption).foregroundStyle(Palette.muted)
            } else {
                Text("Choose the lens you mounted.").font(.callout).foregroundStyle(Palette.muted)
                    .padding(.vertical, 20)
            }
            Spacer(minLength: 0)
            HStack {
                Button(model.bankActionLabel, action: model.performPreparedBankAction)
                    .buttonStyle(.borderedProminent).disabled(!model.canUseBankAction)
                if let profile = model.deviceLensPreview {
                    Button("Edit…") { model.editLens(profile) }.buttonStyle(.bordered).disabled(model.busy || model.isDirty)
                }
            }.controlSize(.large)
            Text(model.bankActionHint).font(.caption).foregroundStyle(Palette.muted)
                .fixedSize(horizontal: false, vertical: true)
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading).frame(minHeight: 540).modifier(Surface())
    }
    private func infoRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label).foregroundStyle(Palette.muted)
            Spacer(minLength: 16)
            Text(value).fontWeight(.medium).multilineTextAlignment(.trailing).monospacedDigit()
        }.font(.callout)
    }
    private var statusBanner: some View {
        HStack(spacing: 12) {
            if model.busy { ProgressView().controlSize(.small) }
            else { Image(systemName: model.workflowSymbol) }
            VStack(alignment: .leading, spacing: 4) {
                Text(model.workflowTitle).font(.callout.weight(.semibold))
                Text(model.workflowDetail).font(.caption).foregroundStyle(Palette.muted)
                if model.busy, let p = model.progress { ProgressView(value: p.fraction) }
            }
            Spacer()
            if model.canRequestVerification {
                Button("Verify profile", action: model.verifyFromCard).buttonStyle(.borderedProminent)
            } else if model.canCancelRead {
                Button("Cancel read", action: model.cancelBackup).buttonStyle(.bordered)
            }
        }.padding(15).background(Palette.softAccent, in: RoundedRectangle(cornerRadius: 12))
    }
}
