import Foundation

/// Stable storage identity, independent of the app's display name or package.
/// Keeping this path also preserves the shared USB lock across old/new clients.
public enum AdapterStorage {
    public static let directoryName = "org.openlmea9.prototype"
    public static var defaultDirectory: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent(directoryName, isDirectory: true)
    }
}
