import Foundation

public enum LensKind: String, Codable, Sendable, CaseIterable {
    case prime, macro = "macro-prime", zoom
    public var label: String {
        switch self { case .prime: "Prime"; case .macro: "Macro prime"; case .zoom: "Zoom" }
    }
}

/// Metadata only. Neither physical settings nor optical calibration are discovered by USB.
public struct LensProfile: Codable, Equatable, Identifiable, Sendable {
    public var id: String
    public var displayName: String
    public var kind: LensKind
    public var minimumFocalLengthMM: Double
    public var maximumFocalLengthMM: Double
    public var activeFocalLengthMM: Double?
    public var maximumAperture: Double
    // Persisted key retained for existing libraries: an optional owner-declared
    // fixed camera f-number, never a measurement of the current iris position.
    public var currentAperture: Double?
    public var notes: String
    public var revision: Int
    public var savedAt: Date?

    public var focalSummary: String {
        let range = kind == .zoom ? "\(minimumFocalLengthMM.formatted())–\(maximumFocalLengthMM.formatted())" : minimumFocalLengthMM.formatted()
        return "\(range) mm · f/\(maximumAperture.formatted())"
    }

    public func validate() throws {
        guard !id.isEmpty, id.count <= 80, id.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-") }) else {
            throw LibraryError.invalid("Invalid profile identifier.")
        }
        guard !displayName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, displayName.count <= 120 else {
            throw LibraryError.invalid("Use a lens name between 1 and 120 characters.")
        }
        guard minimumFocalLengthMM.isFinite, maximumFocalLengthMM.isFinite,
              (1...1000).contains(minimumFocalLengthMM), (minimumFocalLengthMM...1000).contains(maximumFocalLengthMM) else {
            throw LibraryError.invalid("Focal lengths must be between 1 and 1,000 mm, with the range in increasing order.")
        }
        if kind != .zoom && (minimumFocalLengthMM != maximumFocalLengthMM || activeFocalLengthMM != nil) {
            throw LibraryError.invalid("A prime needs one focal length and no zoom setting.")
        }
        if let activeFocalLengthMM, !activeFocalLengthMM.isFinite || !(minimumFocalLengthMM...maximumFocalLengthMM).contains(activeFocalLengthMM) {
            throw LibraryError.invalid("Current zoom setting must lie inside the lens range.")
        }
        guard maximumAperture.isFinite, (0.5...64).contains(maximumAperture) else {
            throw LibraryError.invalid("Maximum aperture must be an f-number between 0.5 and 64.")
        }
        if let currentAperture, !currentAperture.isFinite || !(maximumAperture...128).contains(currentAperture) {
            throw LibraryError.invalid("The fixed camera aperture must be at least the maximum-aperture f-number and no greater than 128.")
        }
        guard notes.count <= 2000, (1...1_000_000).contains(revision) else {
            throw LibraryError.invalid("Notes are limited to 2,000 characters; profile revision is out of range.")
        }
    }
}

public enum LibraryError: LocalizedError {
    case invalid(String)
    public var errorDescription: String? { switch self { case .invalid(let message): message } }
}

public struct LensLibrary: Codable, Equatable, Sendable {
    public var schemaVersion = 1
    public var targetCamera = "Sony A7C II"
    public var profiles: [LensProfile]
    public init(profiles: [LensProfile]) { self.profiles = profiles }

    public func validate() throws {
        guard schemaVersion == 1 else { throw LibraryError.invalid("Unsupported library schema \(schemaVersion). The existing library was preserved.") }
        guard !targetCamera.isEmpty, targetCamera.count <= 120, (1...256).contains(profiles.count) else {
            throw LibraryError.invalid("A library needs a camera name and 1–256 profiles.")
        }
        guard Set(profiles.map(\.id)).count == profiles.count else { throw LibraryError.invalid("Profile identifiers must be unique.") }
        for profile in profiles { try profile.validate() }
    }

    public func encoded() throws -> Data {
        try validate()
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        return try encoder.encode(self)
    }

    public static func decode(_ data: Data) throws -> Self {
        guard data.count <= 1_048_576 else { throw LibraryError.invalid("Library files are limited to 1 MiB.") }
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let profiles = object["profiles"] as? [[String: Any]] else {
            throw LibraryError.invalid("Expected a versioned lens library with a profiles array.")
        }
        let libraryKeys: Set<String> = ["schemaVersion", "targetCamera", "profiles"]
        let profileKeys: Set<String> = ["id", "displayName", "kind", "minimumFocalLengthMM", "maximumFocalLengthMM",
            "activeFocalLengthMM", "maximumAperture", "currentAperture", "notes", "revision", "savedAt"]
        guard Set(object.keys).isSubset(of: libraryKeys), profiles.allSatisfy({ Set($0.keys).isSubset(of: profileKeys) }) else {
            throw LibraryError.invalid("Unknown library fields. Import stopped to preserve data this prototype cannot represent.")
        }
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let result = try decoder.decode(Self.self, from: data)
        try result.validate()
        return result
    }

    public static func seeds() throws -> Self {
        struct Inventory: Decodable { let lenses: [Seed] }
        struct Seed: Decodable {
            let id: String, display_name: String, kind: LensKind
            let focal_length_mm: Double?, focal_length_range_mm: [Double]?
            let nominal_maximum_aperture: Double?, reported_nominal_maximum_aperture: Double?
            let notes: String?
        }
        guard let url = Bundle.module.url(forResource: "requested-lenses", withExtension: "json") else {
            throw LibraryError.invalid("The bundled lens inventory is missing.")
        }
        let inventory = try JSONDecoder().decode(Inventory.self, from: Data(contentsOf: url))
        let profiles = try inventory.lenses.map { seed -> LensProfile in
            guard let minimum = seed.focal_length_mm ?? seed.focal_length_range_mm?.first,
                  let maximum = seed.focal_length_mm ?? seed.focal_length_range_mm?.last,
                  let aperture = seed.nominal_maximum_aperture ?? seed.reported_nominal_maximum_aperture else {
                throw LibraryError.invalid("Incomplete bundled lens inventory.")
            }
            return LensProfile(id: seed.id, displayName: seed.display_name, kind: seed.kind,
                               minimumFocalLengthMM: minimum, maximumFocalLengthMM: maximum,
                               activeFocalLengthMM: nil, maximumAperture: aperture, currentAperture: nil,
                               notes: seed.notes ?? "", revision: 1, savedAt: nil)
        }
        let library = Self(profiles: profiles)
        try library.validate()
        return library
    }
}

/// UI calls these small local-file operations synchronously; device I/O has a separate worker.
public struct LibraryStore: Sendable {
    public let directory: URL
    public var fileURL: URL { directory.appendingPathComponent("profiles.json") }
    public init(directory: URL) { self.directory = directory }

    public func loadOrSeed() throws -> LensLibrary {
        if FileManager.default.fileExists(atPath: fileURL.path) {
            return try LensLibrary.decode(readBounded(fileURL))
        }
        let seed = try LensLibrary.seeds()
        try save(seed)
        return seed
    }

    public func save(_ library: LensLibrary) throws {
        let data = try library.encoded()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try data.write(to: fileURL, options: .atomic)
    }

    /// Validate before touching the live file; retain a timestamped copy before replacement.
    public func importLibrary(from url: URL) throws -> LensLibrary {
        let replacement = try LensLibrary.decode(readBounded(url))
        if FileManager.default.fileExists(atPath: fileURL.path) {
            let prior = directory.appendingPathComponent("profiles-before-import-\(UUID().uuidString).json")
            try FileManager.default.copyItem(at: fileURL, to: prior)
        }
        try save(replacement)
        return replacement
    }

    public func export(_ library: LensLibrary, to url: URL) throws {
        try library.encoded().write(to: url, options: .atomic)
    }

    public func readBounded(_ url: URL) throws -> Data {
        let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
        guard size <= 1_048_576 else { throw LibraryError.invalid("Library files are limited to 1 MiB.") }
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let data = try handle.read(upToCount: 1_048_577) ?? Data()
        guard data.count <= 1_048_576 else { throw LibraryError.invalid("Library files are limited to 1 MiB.") }
        return data
    }
}
