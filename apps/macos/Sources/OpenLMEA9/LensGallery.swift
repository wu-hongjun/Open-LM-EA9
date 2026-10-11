import SwiftUI
import LensCore

struct LensLibraryView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 26) {
                HStack(alignment: .bottom) {
                    VStack(alignment: .leading, spacing: 9) {
                        Eyebrow("Your collection · \(model.library.profiles.count) lenses")
                        Text("Good glass. Ready to go.").font(.system(size: 32, weight: .medium, design: .serif))
                        Text("Choose a profile to prepare on this Mac. Edit the details only when you need to.")
                            .font(.system(size: 13)).foregroundStyle(Palette.muted)
                    }
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
                Text("Local choices are not applied to the adapter. Reference photos may show a different production variant.")
                    .font(.system(size: 11)).foregroundStyle(Palette.muted)
            }.padding(32).frame(maxWidth: 1130).frame(maxWidth: .infinity)
        }
    }
}

private struct LensCard: View {
    @ObservedObject var model: AppModel
    let profile: LensProfile
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button { model.editLens(profile) } label: {
                ProductPhoto(id: profile.id, height: 176).padding(.horizontal, 16).padding(.top, 14)
            }.buttonStyle(.plain).accessibilityLabel("View \(profile.displayName)")
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Eyebrow(PhotoCatalog.family(profile))
                    Spacer()
                    if model.preparedLensID == profile.id {
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(Palette.accent).accessibilityLabel("Prepared on this Mac")
                    }
                }
                LensNumbers(profile: profile)
                Text(profile.displayName).font(.system(size: 11)).foregroundStyle(Palette.muted).lineLimit(2).frame(height: 30, alignment: .top)
                HStack {
                    Button(model.preparedLensID == profile.id ? "Prepared locally" : "Prepare lens") { model.prepareLens(profile) }
                        .buttonStyle(PrimaryButtonStyle()).disabled(model.loadError != nil)
                        .accessibilityLabel("Prepare \(profile.displayName) on this Mac")
                    Spacer()
                    Button { model.editLens(profile) } label: { Image(systemName: "slider.horizontal.3").padding(8) }
                        .buttonStyle(.plain).foregroundStyle(Palette.muted).help("Edit lens details")
                        .accessibilityLabel("Edit metadata for \(profile.displayName)")
                }
            }.padding(20)
        }.modifier(Surface())
            .overlay(RoundedRectangle(cornerRadius: 22).strokeBorder(model.preparedLensID == profile.id ? Palette.accent : .clear, lineWidth: 1.5))
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
                    Eyebrow(PhotoCatalog.family(profile))
                    LensNumbers(profile: profile, large: true)
                    Text(profile.displayName).font(.system(size: 18, weight: .medium, design: .serif))
                    if let note = PhotoCatalog.note(profile.id) { Text(note).font(.caption).foregroundStyle(Palette.muted) }
                    Text("Your saved metadata stays on this Mac.").font(.callout).foregroundStyle(Palette.muted)
                    Spacer()
                }.padding(24).frame(width: 300)
                Form {
                    Section("Lens metadata") {
                        TextField("Display name", text: model.binding(\.name))
                        TextField(profile.kind == .zoom ? "Minimum focal length (mm)" : "Focal length (mm)", text: model.binding(\.minimum))
                        if profile.kind == .zoom { TextField("Maximum focal length (mm)", text: model.binding(\.maximum)) }
                        TextField("Maximum aperture (f-number)", text: model.binding(\.aperture))
                    }
                    Section {
                        if profile.kind == .zoom { TextField("Current zoom setting (mm)", text: model.binding(\.active), prompt: Text("Unknown")) }
                        TextField("Aperture-ring setting (f-number)", text: model.binding(\.currentAperture), prompt: Text("Unknown"))
                    } header: { Text("Manual settings") } footer: {
                        Text("Optional. These positions cannot be sensed through the passive mount.")
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
                Button("Save Lens", action: { model.save() }).buttonStyle(PrimaryButtonStyle()).keyboardShortcut("s").disabled(!model.canSave)
            }.padding(24)
        }.frame(width: 810, height: 640).background(Palette.canvas).foregroundStyle(Palette.ink)
    }
}
