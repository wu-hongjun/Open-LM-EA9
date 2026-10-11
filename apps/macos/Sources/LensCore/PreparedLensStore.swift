import Foundation

/// A local choice, deliberately independent of any adapter-reported or applied profile.
public struct PreparedLensStore: Sendable {
    public let fileURL: URL
    private struct Document: Codable { let schemaVersion: Int; let profileID: String }
    public init(directory: URL) { fileURL = directory.appendingPathComponent("prepared-lens.json") }
    public func load(in library: LensLibrary) throws -> String? {
        guard FileManager.default.fileExists(atPath: fileURL.path) else { return nil }
        let handle = try FileHandle(forReadingFrom: fileURL); defer { try? handle.close() }
        let data = try handle.read(upToCount: 4_097) ?? Data()
        guard data.count <= 4_096 else { throw LibraryError.invalid("Local lens choice is too large.") }
        let document = try JSONDecoder().decode(Document.self, from: data)
        guard document.schemaVersion == 1 else { throw LibraryError.invalid("Unsupported local lens choice.") }
        return library.profiles.contains { $0.id == document.profileID } ? document.profileID : nil
    }
    public func save(_ profileID: String, in library: LensLibrary) throws {
        try library.validate()
        guard library.profiles.contains(where: { $0.id == profileID }) else { throw LibraryError.invalid("Choose a lens from this library.") }
        let data = try JSONEncoder().encode(Document(schemaVersion: 1, profileID: profileID))
        try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        try data.write(to: fileURL, options: .atomic)
    }
}
