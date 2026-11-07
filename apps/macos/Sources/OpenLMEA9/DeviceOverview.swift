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
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("Adapter").font(.headline)
                Spacer()
                StatusPill(text: model.connectionLabel, connected: model.adapterConnected)
            }.frame(height: 32)
            ProductPhoto(id: "lm-ea9", height: 190).padding(.vertical, 6)
            Text("Techart LM-EA9").font(.system(size: 23, weight: .medium))
            Divider()
            infoRow("Firmware", model.currentAppliedLens?.firmwareVersion ?? model.currentFirmwareObservation?.version ?? "Not read")
            if let caption = model.firmwareHistoryCaption {
                Text(caption).font(.caption).foregroundStyle(Palette.muted)
            }
            Spacer(minLength: 4)
            if !model.needsWorkflowBanner || model.busy {
                Button("USB tools") { model.showDeviceTools = true }.buttonStyle(.bordered).controlSize(.large)
            }
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading).frame(minHeight: 460).modifier(Surface())
    }
    private var lensCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack { Text("Lens").font(.headline); Spacer() }.frame(height: 32)
            if let applied = model.currentAppliedLens {
                ProductPhoto(id: applied.setting.id, height: 190).padding(.vertical, 6)
                Text(applied.setting.name).font(.system(size: 23, weight: .medium)).lineLimit(2)
                Divider()
                infoRow("Sony aperture dial", model.currentFirmwareVariant?.apertureRangeLabel ?? "Unknown")
                infoRow("Physical aperture", "Unknown")
                Text("Set the iris with the lens ring.").font(.caption).foregroundStyle(Palette.muted)
            } else {
                Text("Lens information not read").font(.system(size: 20, weight: .medium)).padding(.top, 24)
                Text(model.emptyLensMessage).font(.callout).foregroundStyle(Palette.muted)
            }
            Spacer(minLength: 4)
        }.padding(24).frame(maxWidth: .infinity, alignment: .leading).frame(minHeight: 460).modifier(Surface())
    }
    private func infoRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label).foregroundStyle(Palette.muted)
            Spacer()
            Text(value).fontWeight(.medium).monospacedDigit()
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
            if !model.busy { Button("USB tools") { model.showDeviceTools = true }.buttonStyle(.bordered) }
        }.padding(15).background(Palette.softAccent, in: RoundedRectangle(cornerRadius: 12))
    }
}
