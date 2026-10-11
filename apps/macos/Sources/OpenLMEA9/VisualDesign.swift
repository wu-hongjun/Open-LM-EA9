import SwiftUI
import AppKit
import LensCore

enum Palette {
    static let canvas = Color(red: 0.96, green: 0.95, blue: 0.93)
    static let ink = Color(red: 0.13, green: 0.15, blue: 0.16)
    static let muted = Color(red: 0.40, green: 0.43, blue: 0.43)
    static let line = Color(red: 0.87, green: 0.87, blue: 0.84)
    static let accent = Color(red: 0.17, green: 0.39, blue: 0.34)
    static let softAccent = Color(red: 0.91, green: 0.95, blue: 0.92)
}

struct Eyebrow: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View { Text(text.uppercased()).font(.system(size: 10, weight: .semibold)).tracking(1.5).foregroundStyle(Palette.muted) }
}
struct Surface: ViewModifier {
    func body(content: Content) -> some View {
        content.background(.white, in: RoundedRectangle(cornerRadius: 22))
            .overlay(RoundedRectangle(cornerRadius: 22).strokeBorder(Palette.line.opacity(0.7), lineWidth: 0.7))
    }
}
struct PrimaryButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.system(size: 13, weight: .semibold)).padding(.horizontal, 20).padding(.vertical, 11)
            .foregroundStyle(.white).background(Palette.ink.opacity(enabled ? (configuration.isPressed ? 0.8 : 1) : 0.35), in: RoundedRectangle(cornerRadius: 10))
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
        }.frame(maxWidth: .infinity).frame(height: height).background(.white).accessibilityHidden(true)
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
        HStack {
            HStack(spacing: 10) {
                Image(systemName: "camera.aperture").font(.system(size: 22, weight: .light))
                Text("Open LM-EA9").font(.system(size: 15, weight: .semibold))
            }.frame(maxWidth: .infinity, alignment: .leading)
            HStack(spacing: 4) {
                tab("Device", image: "cable.connector", value: .device)
                tab("Lens Library", image: "camera.aperture", value: .lensLibrary)
            }.padding(4).background(.white.opacity(0.7), in: RoundedRectangle(cornerRadius: 12))
            Label(model.library.targetCamera, systemImage: "camera")
                .font(.system(size: 12)).foregroundStyle(Palette.muted).frame(maxWidth: .infinity, alignment: .trailing)
        }.padding(.horizontal, 32).padding(.vertical, 16)
    }
    private func tab(_ title: String, image: String, value: AppTab) -> some View {
        Button { model.requestTab(value) } label: {
            Label(title, systemImage: image).font(.system(size: 12, weight: .medium))
                .padding(.horizontal, 15).padding(.vertical, 9)
                .background(model.selectedTab == value ? Palette.ink : .clear, in: RoundedRectangle(cornerRadius: 9))
                .foregroundStyle(model.selectedTab == value ? .white : Palette.muted)
        }.buttonStyle(.plain).accessibilityAddTraits(model.selectedTab == value ? .isSelected : [])
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
