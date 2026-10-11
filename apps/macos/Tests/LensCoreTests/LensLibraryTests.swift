import Foundation
import Testing
@testable import LensCore

private func temporaryStore() throws -> LibraryStore {
    let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ea9-library-tests-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
    return LibraryStore(directory: directory)
}

@Test func requestedInventoryKeepsUnknownsAndDesignations() throws {
    let library = try LensLibrary.seeds()
    #expect(library.profiles.count == 8)
    #expect(library.profiles.map(\.minimumFocalLengthMM) == [28, 35, 50, 85, 100, 135, 28, 58])
    #expect(library.profiles.allSatisfy { $0.currentAperture == nil && $0.savedAt == nil })
    let zoom = library.profiles[6]
    #expect(zoom.maximumFocalLengthMM == 70 && zoom.activeFocalLengthMM == nil)
    #expect(zoom.displayName.contains("user-supplied"))
    #expect(library.profiles[7].displayName.contains("58mm"))
    #expect(try LensLibrary.decode(library.encoded()) == library)
}

@Test func metadataValidationRejectsImpossibleValues() throws {
    var profile = try LensLibrary.seeds().profiles[0]
    profile.maximumAperture = .nan
    #expect(throws: LibraryError.self) { try profile.validate() }
    profile.maximumAperture = 2
    profile.currentAperture = 1.4
    #expect(throws: LibraryError.self) { try profile.validate() }
    profile.currentAperture = 8
    try profile.validate()
    profile.maximumFocalLengthMM = 29
    #expect(throws: LibraryError.self) { try profile.validate() }
    var zoom = try LensLibrary.seeds().profiles[6]
    zoom.activeFocalLengthMM = 71
    #expect(throws: LibraryError.self) { try zoom.validate() }
    zoom.activeFocalLengthMM = 50
    try zoom.validate()
    zoom.minimumFocalLengthMM = 100
    #expect(throws: LibraryError.self) { try zoom.validate() }
}

@Test func unsupportedSchemaDuplicatesAndOversizedFilesFail() throws {
    var library = try LensLibrary.seeds()
    library.profiles[1].id = library.profiles[0].id
    #expect(throws: LibraryError.self) { try library.validate() }
    library = try LensLibrary.seeds()
    var object = try #require(JSONSerialization.jsonObject(with: library.encoded()) as? [String: Any])
    object["schemaVersion"] = 2
    #expect(throws: LibraryError.self) { try LensLibrary.decode(JSONSerialization.data(withJSONObject: object)) }
    object["schemaVersion"] = 1
    object["opticalCalibration"] = ["unrecognized": true]
    #expect(throws: LibraryError.self) { try LensLibrary.decode(JSONSerialization.data(withJSONObject: object)) }
    #expect(throws: LibraryError.self) { try LensLibrary.decode(Data(repeating: 32, count: 1_048_577)) }
}

@Test func savingAndImportingPreserveRevisionAndOriginalData() throws {
    let store = try temporaryStore()
    defer { try? FileManager.default.removeItem(at: store.directory) }
    var library = try store.loadOrSeed()
    library.profiles[0].displayName = "Distagon 28 · personal profile"
    library.profiles[0].currentAperture = 5.6
    library.profiles[0].revision = 2
    library.profiles[0].savedAt = Date(timeIntervalSince1970: 1_700_000_000)
    try store.save(library)
    #expect(try store.loadOrSeed() == library)
    let prior = try Data(contentsOf: store.fileURL)
    let invalid = store.directory.appendingPathComponent("invalid.json")
    try Data("{\"schemaVersion\":99}".utf8).write(to: invalid)
    #expect(throws: (any Error).self) { try store.importLibrary(from: invalid) }
    #expect(try Data(contentsOf: store.fileURL) == prior)
    let valid = store.directory.appendingPathComponent("import.json")
    try store.export(try LensLibrary.seeds(), to: valid)
    let imported = try store.importLibrary(from: valid)
    #expect(imported.profiles[0].revision == 1)
    let backups = try FileManager.default.contentsOfDirectory(at: store.directory, includingPropertiesForKeys: nil)
        .filter { $0.lastPathComponent.hasPrefix("profiles-before-import-") }
    #expect(backups.count == 1)
    #expect(try Data(contentsOf: backups[0]) == prior)
}

@Test func corruptLibraryIsNeverReseededOverTheOriginal() throws {
    let store = try temporaryStore()
    defer { try? FileManager.default.removeItem(at: store.directory) }
    let original = Data("unreadable original library".utf8)
    try original.write(to: store.fileURL)
    #expect(throws: (any Error).self) { try store.loadOrSeed() }
    #expect(try Data(contentsOf: store.fileURL) == original)
}
