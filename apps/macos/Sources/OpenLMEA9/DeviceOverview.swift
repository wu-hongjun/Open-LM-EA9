import SwiftUI
import AppKit
import LensCore
import DeviceKit

struct DeviceView: View {
    @ObservedObject var model: AppModel
    private var connected: Bool { model.devices.count == 1 && !model.discoveryError }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(alignment: .bottom) {
                    VStack(alignment: .leading, spacing: 8) {
                        Eyebrow("Your adapter")
                        Text("Vintage glass. A simple connection.").font(.system(size: 28, weight: .medium, design: .serif))
                    }
                    Spacer()
                    Button { Task { await model.refreshDevices() } } label: { Image(systemName: "arrow.clockwise").padding(8) }
                        .buttonStyle(.plain).foregroundStyle(Palette.muted).disabled(model.busy)
                        .help("Refresh USB connection").accessibilityLabel("Refresh Connection")
                }
                HStack(spacing: 28) {
                    ProductPhoto(id: "lm-ea9", height: 145).frame(width: 250).padding(14)
                    VStack(alignment: .leading, spacing: 9) {
                        StatusPill(text: model.connectionLabel, connected: connected)
                        Text("TECHART").font(.system(size: 11, weight: .semibold)).tracking(2).foregroundStyle(Palette.muted)
                        Text("LM-EA9").font(.system(size: 32, weight: .medium, design: .rounded))
                        Text("Leica M → Sony E").font(.system(size: 14)).foregroundStyle(Palette.muted)
                        if model.reconnectRequired || model.discoveryError {
                            Text(model.reconnectRequired ? "Reconnect the USB cap before another read." : model.deviceMessage)
                                .font(.caption).foregroundStyle(.orange)
                        } else if !connected {
                            Text("Connect the USB cap. This view updates automatically.").font(.caption).foregroundStyle(Palette.muted)
                        }
                    }.padding(.vertical, 18).frame(maxWidth: .infinity, alignment: .leading)
                    VStack(alignment: .leading, spacing: 8) {
                        Eyebrow("Firmware")
                        Text(model.currentFirmwareObservation?.version ?? "Not read")
                            .font(.system(size: 25, weight: .medium, design: .rounded))
                        if let read = model.currentFirmwareObservation {
                            Text("Last read \(read.readAt.formatted(date: .abbreviated, time: .shortened))")
                                .font(.system(size: 10)).foregroundStyle(Palette.muted)
                        }
                        Button("Read version…") { model.showDeviceTools = true }.font(.system(size: 11)).padding(.top, 4)
                    }.frame(width: 190, alignment: .leading).padding(.trailing, 24)
                }.modifier(Surface())
                lensInformation
                HStack(spacing: 10) {
                    Image(systemName: "lock.shield").font(.system(size: 12))
                    Text("Choose a lens, apply it, then reconnect to verify the adapter.")
                        .font(.system(size: 11))
                    Spacer()
                    Button("USB tools…") { model.showDeviceTools = true }.font(.system(size: 11))
                }.foregroundStyle(Palette.muted)
            }.padding(24).frame(maxWidth: 1060).frame(maxWidth: .infinity)
        }
    }
    private var lensInformation: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Eyebrow("Lens on adapter")
                Spacer()
                if model.waitingForVerification {
                    StatusPill(text: "Verification needed")
                } else if let applied = model.currentAppliedLens {
                    Text("Verified \(applied.verifiedAt.formatted(date: .abbreviated, time: .shortened))")
                        .font(.system(size: 11)).foregroundStyle(Palette.muted)
                }
            }
            HStack(spacing: 28) {
                ProductPhoto(id: model.currentAppliedLens?.setting.id ?? model.preparedLens?.id ?? "contax-zeiss-50-f1-4", height: 100)
                    .frame(width: 170)
                VStack(alignment: .leading, spacing: 8) {
                    if let applied = model.currentAppliedLens {
                        Text(applied.setting.name).font(.system(size: 23, weight: .medium, design: .serif)).lineLimit(2)
                        Text("\(applied.setting.focalLengthMM.formatted()) mm · reported f/\(applied.setting.apertureLabel)")
                            .font(.system(size: 13)).foregroundStyle(Palette.muted)
                        StatusPill(text: "On adapter · USB verified", connected: true)
                    } else {
                        Text(model.waitingForVerification ? "Finish your lens change" : connected ? "Lens settings not read" : "Ready for your next lens")
                            .font(.system(size: 23, weight: .medium, design: .serif))
                        Text(model.waitingForVerification ? "Reconnect the USB cap, then verify the uploaded settings." : connected ? "Read the adapter’s settings in USB tools, or choose a profile below." : "Connect your adapter to see its saved lens information.")
                            .font(.system(size: 13)).foregroundStyle(Palette.muted)
                    }
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            Divider()
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    Text("Switch lens profile").font(.headline)
                    Spacer()
                    Button("Edit library…") { model.requestTab(.lensLibrary) }.buttonStyle(.plain).foregroundStyle(Palette.accent)
                }
                HStack(spacing: 18) {
                    Picker("Lens profile", selection: Binding(get: { model.preparedLensID }, set: { model.chooseDeviceLens($0) })) {
                        Text("Choose a lens…").tag(String?.none)
                        ForEach(model.library.profiles) { profile in
                            Text(profile.displayName).tag(Optional(profile.id))
                        }
                    }
                    .pickerStyle(.menu).labelsHidden().controlSize(.large)
                    .accessibilityLabel("Lens Profile")
                    .disabled(model.busy || model.isDirty || model.loadError != nil || model.waitingForVerification)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    if model.waitingForVerification {
                        Button("Verify lens", action: model.verifyLensUpdate).buttonStyle(PrimaryButtonStyle()).disabled(!model.canVerifyUpdate)
                    } else if model.stockUploadQualified {
                        Button(model.preparedMatchesApplied ? "Up to date" : "Apply profile", action: model.applyLens)
                            .buttonStyle(PrimaryButtonStyle()).disabled(!model.canApplyLens)
                    } else {
                        Button("Set up adapter", action: model.prepareAdapter).buttonStyle(PrimaryButtonStyle())
                            .disabled(!model.canReadDevice || model.updateStateError != nil || model.waitingForVerification)
                    }
                }
                if let profile = model.preparedLens {
                    Text(profile.focalSummary + (model.preparedMatchesApplied ? " · Matches adapter settings" : " · Ready to apply"))
                        .font(.callout).foregroundStyle(Palette.muted)
                }
                if let issue = model.preparedLensIssue, let profile = model.preparedLens {
                    HStack {
                        Text(issue).font(.caption).foregroundStyle(.orange)
                        Spacer()
                        Button("Edit lens…") { model.editLens(profile) }.disabled(model.busy)
                    }
                }
                if let error = model.updateStateError {
                    Text(error).font(.caption).foregroundStyle(.orange)
                }
                if model.waitingForVerification {
                    Text(model.reconnectRequired || model.pendingUpdate?.device.id == model.devices.first?.id ?
                         "Unplug and reconnect the USB cap. The app will detect the new connection automatically." :
                         "New connection detected. Confirm the updater is closed below, then verify your lens.")
                        .font(.callout).foregroundStyle(Palette.muted)
                } else if !connected {
                    Text("You can choose a profile now and apply it when the adapter is connected.")
                        .font(.caption).foregroundStyle(Palette.muted)
                } else if !model.idleAcknowledged && !model.reconnectRequired {
                    Text("Confirm the USB connection below before applying a different profile.")
                        .font(.caption).foregroundStyle(Palette.muted)
                }
                if connected && !model.busy && !model.reconnectRequired {
                    Toggle("Updater closed · USB cap reconnected", isOn: $model.idleAcknowledged).font(.caption)
                }
            }
            if model.busy, let progress = model.progress {
                Text(progress.phase).font(.callout)
                ProgressView(value: progress.fraction)
            }
            Text("Choose a profile, apply it, then reconnect to verify. Aperture settings are reported metadata; the adapter cannot read a passive lens’s rings.")
                .font(.caption).foregroundStyle(Palette.muted)
        }.padding(22).modifier(Surface())
    }

}

struct DeviceToolsView: View {
    @ObservedObject var model: AppModel
    @State private var showBackup = false
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 5) {
                    Text("USB tools").font(.title2.weight(.semibold))
                    Text("Read adapter settings or keep a verified backup.").font(.callout).foregroundStyle(Palette.muted)
                }
                Spacer()
                Button("Done") { model.showDeviceTools = false }.disabled(model.busy)
            }.padding(26)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HStack {
                        StatusPill(text: model.connectionLabel, connected: model.devices.count == 1 && !model.discoveryError)
                        Spacer()
                        Button("Refresh Connection") { Task { await model.refreshDevices() } }.disabled(model.busy)
                    }
                    Text(model.deviceMessage).font(.callout).foregroundStyle(Palette.muted)
                    if let error = model.updateStateError {
                        Label(error, systemImage: "exclamationmark.circle").font(.callout).foregroundStyle(.orange)
                    }
                    if model.reconnectRequired {
                        Label("Unplug and reconnect the USB cap. Connection updates automatically.", systemImage: "exclamationmark.circle").foregroundStyle(.orange)
                    }
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Prepare the connection").font(.headline)
                        Toggle("I’ve closed the updater and reconnected the USB cap", isOn: $model.idleAcknowledged)
                            .disabled(model.busy || model.reconnectRequired || model.devices.count != 1 || model.discoveryError)
                        Text("Close TECHART Update and other USB tools, then unplug and reconnect the cap before the first read. An unfinished stock update can interpret even a version request as firmware data.")
                            .font(.caption).foregroundStyle(Palette.muted)
                    }.padding(20).modifier(Surface())
                    HStack {
                        VStack(alignment: .leading, spacing: 7) {
                            Eyebrow("Reported firmware")
                            Text(model.currentFirmwareObservation?.version ?? "Not read").font(.title2.weight(.medium))
                            if let observation = model.currentFirmwareObservation {
                                Text("Last read \(observation.readAt.formatted(date: .abbreviated, time: .standard))").font(.caption).foregroundStyle(Palette.muted)
                            }
                        }
                        Spacer()
                        if model.isReadingFirmware { ProgressView().controlSize(.small); Button("Cancel USB Read", action: model.cancelBackup) }
                        Button("Read Version", action: model.readFirmware).disabled(!model.canReadDevice)
                    }.padding(20).modifier(Surface())
                    Button("Read Adapter Lens", action: model.readAdapterLens).disabled(!model.canReadDevice || model.updateStateError != nil || model.waitingForVerification)
                    DisclosureGroup("Read-only USB backup", isExpanded: $showBackup) {
                        VStack(alignment: .leading, spacing: 15) {
                            Text("Two complete flash reads are compared before a backup is saved. The package includes unit data, a manifest and checksums.")
                            Text("Keep backups private. Stock application upload requires a reconnect and byte verification.").font(.callout).foregroundStyle(Palette.muted)
                            Button("Create Verified Backup…", action: model.chooseBackup).buttonStyle(PrimaryButtonStyle()).disabled(!model.canReadDevice)
                        }.padding(.top, 14)
                    }.padding(20).modifier(Surface())
                    if model.busy, let progress = model.progress {
                        VStack(alignment: .leading, spacing: 10) {
                            Text(progress.phase).font(.headline)
                            ProgressView(value: progress.fraction)
                            Button("Cancel USB Operation", action: model.cancelBackup)
                        }
                    }
                    if let result = model.lastBackup {
                        VStack(alignment: .leading, spacing: 12) {
                            Label("Backup verified", systemImage: "checkmark.seal.fill").foregroundStyle(Palette.accent)
                            Text("Two identical reads · \(result.manifest.flashBytes.formatted()) bytes").font(.callout)
                            Text(result.url.lastPathComponent).font(.caption).textSelection(.enabled)
                            Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([result.url]) }
                        }.padding(20).modifier(Surface())
                    }
                    Button("Restore Stock from Backup…", action: model.chooseStockRestore).disabled(!model.canReadDevice)
                    DisclosureGroup("Experimental autofocus") {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("The new AF 2.2.0 candidate reconciles reference, homing, timing and completion policy. It enables motor movement and still needs camera qualification. Choose a lens on Device, install, then reconnect to verify.").font(.callout)
                            Button("Install Experimental AF 2.2.0", action: model.installAutofocus).disabled(!model.canChangeFirmware)
                            Button("Install Metadata Only for Prepared Lens", action: model.installMetadataOnly).disabled(!model.canChangeFirmware)
                        }.padding(.top, 12)
                    }.padding(20).modifier(Surface())
                    Text(model.firmwareBehaviorNote + " Version reads do not verify application bytes. No automatic USB commands are sent.")
                        .font(.caption).foregroundStyle(Palette.muted)
                }.padding(26)
            }
        }.frame(width: 720, height: 650).background(Palette.canvas).foregroundStyle(Palette.ink)
    }
}
