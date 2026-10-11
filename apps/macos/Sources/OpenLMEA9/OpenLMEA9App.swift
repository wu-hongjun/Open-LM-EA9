import SwiftUI
import AppKit
import LensCore
import DeviceKit

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    weak var model: AppModel?
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        model?.shouldTerminate() == false ? .terminateCancel : .terminateNow
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

@main struct OpenLMEA9App: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model: AppModel
    init() {
        let args = CommandLine.arguments
        let directory: URL
        if let index = args.firstIndex(of: "--library-directory"), index + 1 < args.count {
            directory = URL(fileURLWithPath: args[index + 1], isDirectory: true)
        } else {
            directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("org.openlmea9.prototype", isDirectory: true)
        }
        _model = StateObject(wrappedValue: AppModel(directory: directory))
    }
    var body: some Scene {
        Window("Open LM-EA9", id: "main") {
            ContentView(model: model)
                .frame(minWidth: 920, minHeight: 680)
                .onAppear { delegate.model = model }
                .task { await model.monitorDevices() }
                .onReceive(NotificationCenter.default.publisher(for: NSApplication.didBecomeActiveNotification)) { _ in
                    Task { await model.refreshDevices(silent: true) }
                }
        }
        .defaultSize(width: 1130, height: 780)
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Photo Credits…") { model.showPhotoCredits = true }
            }
            CommandGroup(replacing: .newItem) {
                Button("Import Lens Library…", action: model.importLibrary).disabled(model.isDirty || model.busy)
                Button("Export Saved Library…", action: model.exportLibrary).keyboardShortcut("e", modifiers: [.command, .shift])
            }
            CommandGroup(replacing: .saveItem) {
                Button("Save Lens", action: { model.save() }).keyboardShortcut("s").disabled(!model.canSave)
                Button("Revert Lens Changes", action: model.revert).disabled(!model.isDirty)
            }
        }
    }
}

struct ContentView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        VStack(spacing: 0) {
            AppHeader(model: model)
            Rectangle().fill(Palette.line).frame(height: 1)
            if model.selectedTab == .device { DeviceView(model: model) }
            else { LensLibraryView(model: model) }
        }
        .background(Palette.canvas).foregroundStyle(Palette.ink).tint(Palette.accent)
        .preferredColorScheme(.light)
        .toolbar(.hidden, for: .windowToolbar)
        .sheet(isPresented: Binding(get: { model.showLensEditor }, set: { if !$0 { model.closeLensEditor() } })) {
            if let profile = model.selectedProfile {
                LensEditor(model: model, profile: profile).interactiveDismissDisabled(model.isDirty)
            }
        }
        .sheet(isPresented: $model.showDeviceTools) {
            DeviceToolsView(model: model).interactiveDismissDisabled(model.busy)
        }
        .sheet(isPresented: $model.showPhotoCredits) { PhotoCreditsView(model: model) }
        .alert("Operation stopped", isPresented: Binding(get: { model.errorMessage != nil }, set: { if !$0 { model.errorMessage = nil } })) {
            Button("OK", role: .cancel) { model.errorMessage = nil }
        } message: { Text(model.errorMessage ?? "") }
        .confirmationDialog("Save changes before leaving this lens?", isPresented: $model.showSwitchConfirmation, titleVisibility: .visible) {
            Button("Save and Continue") { model.finishSwitch(saveFirst: true) }.disabled(!model.canSave)
            Button("Discard Changes", role: .destructive) { model.finishSwitch(saveFirst: false) }
            Button("Cancel", role: .cancel, action: model.cancelSwitch)
        }
        .alert("Replace the local lens library?", isPresented: $model.showImportConfirmation) {
            Button("Replace Library", role: .destructive, action: model.commitImport)
            Button("Cancel", role: .cancel) { model.pendingImport = nil }
        } message: {
            Text("Import \(model.pendingImport?.profiles.count ?? 0) profiles for \(model.pendingImport?.targetCamera ?? ""). A copy of the current library will be kept on this Mac.")
        }
    }
}
