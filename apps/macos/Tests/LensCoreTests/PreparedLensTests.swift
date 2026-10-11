import Foundation
import Testing
@testable import LensCore

@Test func preparedLensIsLocalAndResolvesOnlyWithinCurrentLibrary() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-prepared-lens-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    let store = PreparedLensStore(directory: directory)
    let library = try LensLibrary.seeds()
    let original = try library.encoded()
    #expect(try store.load(in: library) == nil)
    try store.save(library.profiles[0].id, in: library)
    #expect(try store.load(in: library) == library.profiles[0].id)
    #expect(try library.encoded() == original)
    #expect(try store.load(in: LensLibrary(profiles: Array(library.profiles.dropFirst()))) == nil)
    #expect(throws: LibraryError.self) { try store.save("unknown-lens", in: library) }
    #expect(try store.load(in: library) == library.profiles[0].id)
}

@Test func preparedLensRejectsUnsupportedAndOversizedHistory() throws {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-prepared-invalid-\(UUID().uuidString)")
    defer { try? FileManager.default.removeItem(at: directory) }
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let store = PreparedLensStore(directory: directory), library = try LensLibrary.seeds()
    try Data("{\"schemaVersion\":2,\"profileID\":\"contax-zeiss-28-f2\"}".utf8).write(to: store.fileURL)
    #expect(throws: LibraryError.self) { try store.load(in: library) }
    try Data(repeating: 0, count: 4_097).write(to: store.fileURL)
    #expect(throws: LibraryError.self) { try store.load(in: library) }
}
