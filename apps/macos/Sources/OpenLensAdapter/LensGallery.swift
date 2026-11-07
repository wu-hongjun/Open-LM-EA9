import SwiftUI
import LensCore

struct LensLibraryView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 26) {
                HStack(alignment: .bottom) {
                    Text("Lens Library").font(.system(size: 24, weight: .semibold))
                    Spacer()
                    Menu {
                        Button("Import Library…", action: model.importLibrary).disabled(model.isDirty || model.busy)
                        Button("Export Saved Library…", action: model.exportLibrary)
                        Button("Photo Credits…") { model.showPhotoCredits = true }
                    } label: { Image(systemName: "ellipsis").frame(width: 28, height: 22) }
                        .menuStyle(.borderlessButton).fixedSize().accessibilityLabel("Library options")
                }
                if let error = model.loadError { Text(error).foregroundStyle(.red).font(.callout) }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 260, maximum: 380), spacing: 18)], spacing: 18) {
                    ForEach(model.library.profiles) { profile in LensCard(model: model, profile: profile) }
                }
            }.padding(32).frame(maxWidth: 1130).frame(maxWidth: .infinity)
        }
    }
}

private struct LensCard: View {
    @ObservedObject var model: AppModel
    let profile: LensProfile
    var body: some View {
        Button { model.editLens(profile) } label: {
            VStack(alignment: .leading, spacing: 0) {
                ProductPhoto(id: profile.id, height: 176).padding(.horizontal, 16).padding(.top, 14)
                VStack(alignment: .leading, spacing: 10) {
                    LensNumbers(profile: profile)
                    Text(profile.displayName).font(.caption).foregroundStyle(Palette.muted)
                        .lineLimit(2).frame(height: 30, alignment: .top)
                }.padding(20)
            }.modifier(Surface())
        }.buttonStyle(.plain).accessibilityLabel("Edit \(profile.displayName)")
    }
}

struct LensEditor: View {
    @ObservedObject var model: AppModel
    let profile: LensProfile
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("Lens details").font(.system(size: 18, weight: .semibold))
                Spacer()
                Button("Close", action: model.closeLensEditor)
            }.padding(24)
            Divider()
            HStack(alignment: .top, spacing: 0) {
                VStack(alignment: .leading, spacing: 18) {
                    ProductPhoto(id: profile.id, height: 210).clipShape(RoundedRectangle(cornerRadius: 14))
                    LensNumbers(profile: profile, large: true)
                    if let note = PhotoCatalog.note(profile.id) { Text(note).font(.caption).foregroundStyle(Palette.muted) }
                    Spacer()
                }.padding(24).frame(width: 300)
                Form {
                    Section("Lens metadata") {
                        TextField("Display name", text: model.binding(\.name))
                        TextField(profile.kind == .zoom ? "Minimum focal length (mm)" : "Focal length (mm)", text: model.binding(\.minimum))
                        if profile.kind == .zoom { TextField("Maximum focal length (mm)", text: model.binding(\.maximum)) }
                        TextField("Maximum aperture (f-number)", text: model.binding(\.aperture))
                    }
                    if profile.kind == .zoom {
                        Section("Zoom setting") {
                            TextField("Current focal length (mm)", text: model.binding(\.active), prompt: Text("Unknown"))
                        }
                    }
                    Section("Notes") {
                        TextEditor(text: model.binding(\.notes)).frame(minHeight: 80).accessibilityLabel("Lens notes")
                    }
                    if let validation = model.validationMessage { Section { Text(validation).foregroundStyle(.red) } }
                    if let error = model.loadError { Section { Text(error).foregroundStyle(.red) } }
                }.formStyle(.grouped)
            }
            Divider()
            HStack {
                Label(model.isDirty ? "Unsaved changes" : "Saved on this Mac", systemImage: model.isDirty ? "pencil.circle" : "checkmark.circle")
                    .font(.system(size: 12)).foregroundStyle(model.isDirty ? Color.orange : Palette.accent)
                Spacer()
                Button("Revert", action: model.revert).disabled(!model.isDirty)
                Button("Save Lens", action: { model.save() }).buttonStyle(.borderedProminent).keyboardShortcut("s").disabled(!model.canSave)
            }.padding(24)
        }.frame(width: 810, height: 640).background(Palette.canvas).foregroundStyle(Palette.ink)
    }
}
