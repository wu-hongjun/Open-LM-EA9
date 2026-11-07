import SwiftUI
import AppKit
import LensCore

enum Palette {
    static let canvas = Color(nsColor: .windowBackgroundColor)
    static let ink = Color.primary
    static let muted = Color.secondary
    static let line = Color(nsColor: .separatorColor)
    static let accent = Color(nsColor: .controlAccentColor)
    static let softAccent = accent.opacity(0.08)
}

struct Surface: ViewModifier {
    func body(content: Content) -> some View {
        content.background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(Palette.line, lineWidth: 0.5))
    }
}
struct StatusPill: View {
    let text: String
    var connected = false
    var body: some View {
        HStack(spacing: 7) {
            Circle().fill(connected ? Palette.accent : Palette.muted).frame(width: 6, height: 6)
            Text(text).font(.system(size: 12, weight: .medium))
        }.padding(.horizontal, 12).padding(.vertical, 8)
            .foregroundStyle(connected ? Palette.accent : Palette.muted)
            .background(connected ? Palette.softAccent : Palette.canvas, in: Capsule())
            .accessibilityElement(children: .combine)
    }
}

struct PhotoCredit: Decodable, Identifiable {
    let id: String
    let credit: String
    let depictedModel: String
    let sourcePage: String
    let rights: String
    let licenseURL: String?
    let modelNote: String?
}
@MainActor enum PhotoCatalog {
    static let credits: [PhotoCredit] = {
        struct Document: Decodable { let assets: [PhotoCredit] }
        guard let url = Bundle.module.url(forResource: "photo-credits", withExtension: "json"),
              let data = try? Data(contentsOf: url), let record = try? JSONDecoder().decode(Document.self, from: data) else { return [] }
        return record.assets
    }()
    private static var images: [String: NSImage] = [:]
    static func image(_ id: String) -> NSImage? {
        if let image = images[id] { return image }
        guard let url = Bundle.module.url(forResource: id, withExtension: "jpg"), let image = NSImage(contentsOf: url) else { return nil }
        images[id] = image
        return image
    }
    static func note(_ id: String) -> String? { credits.first { $0.id == id }?.modelNote }
    static func family(_ profile: LensProfile) -> String {
        switch profile.id {
        case "contax-zeiss-28-f2", "contax-zeiss-35-f1-4": "Distagon"
        case "contax-zeiss-50-f1-4", "contax-zeiss-85-f1-4": "Planar"
        case "contax-zeiss-100-f2-8-macro": "Makro-Planar"
        case "contax-zeiss-135-f2-8": "Sonnar"
        case "contax-zeiss-28-70-f3-5": "Vario-Sonnar"
        case "zeiss-jena-biotar-55-f2": "Biotar"
        default: profile.kind.label
        }
    }
}
struct ProductPhoto: View {
    let id: String
    let height: CGFloat
    var body: some View {
        Group {
            if let photo = PhotoCatalog.image(id) {
                Image(nsImage: photo).resizable().scaledToFit()
            } else {
                Image(systemName: "camera.aperture").resizable().scaledToFit().padding(40).foregroundStyle(Palette.muted)
            }
        }.frame(maxWidth: .infinity).frame(height: height).background(.white).clipShape(RoundedRectangle(cornerRadius: 8)).accessibilityHidden(true)
    }
}
struct LensNumbers: View {
    let profile: LensProfile
    var large = false
    private var focal: String {
        profile.kind == .zoom ? "\(profile.minimumFocalLengthMM.formatted())–\(profile.maximumFocalLengthMM.formatted())" : profile.minimumFocalLengthMM.formatted()
    }
    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 5) {
            Text(focal).font(.system(size: large ? 38 : 25, weight: .medium, design: .rounded))
            Text("mm").font(.system(size: 12)).foregroundStyle(Palette.muted)
            Spacer()
            Text("f/\(profile.maximumAperture.formatted())").font(.system(size: large ? 23 : 18, weight: .medium, design: .rounded))
        }.monospacedDigit().accessibilityElement(children: .ignore).accessibilityLabel(profile.focalSummary)
    }
}

struct AppHeader: View {
    @ObservedObject var model: AppModel
    var body: some View {
        Picker("Section", selection: Binding(get: { model.selectedTab }, set: { model.requestTab($0) })) {
            Text("Device").tag(AppTab.device)
            Text("Lens Library").tag(AppTab.lensLibrary)
        }.pickerStyle(.segmented).labelsHidden().frame(width: 260).padding(16)
            .frame(maxWidth: .infinity)
    }
}

struct PhotoCreditsView: View {
    @ObservedObject var model: AppModel
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text("Photo credits").font(.title2.weight(.semibold)); Spacer()
                Button("Done") { model.showPhotoCredits = false }
            }
            Text("Reference photographs show example lenses, not your individual equipment.").foregroundStyle(Palette.muted)
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    ForEach(PhotoCatalog.credits) { credit in
                        HStack(alignment: .top, spacing: 18) {
                            ProductPhoto(id: credit.id, height: 80).frame(width: 105)
                            VStack(alignment: .leading, spacing: 6) {
                                Text(credit.depictedModel).font(.headline)
                                Text(credit.credit).font(.callout)
                                if let url = URL(string: credit.sourcePage) { Link("Original photo source", destination: url) }
                                if let url = credit.licenseURL.flatMap(URL.init(string:)) { Link(credit.rights, destination: url) }
                                else { Text("Reference use in this local prototype; redistribution permission not established.").font(.caption).foregroundStyle(Palette.muted) }
                                if let note = credit.modelNote { Text(note).font(.caption).foregroundStyle(Palette.muted) }
                            }
                        }
                    }
                }
            }
        }.padding(28).frame(width: 690, height: 610).background(Palette.canvas)
    }
}
