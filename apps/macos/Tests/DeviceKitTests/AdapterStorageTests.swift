import Foundation
import Testing
@testable import DeviceKit

@Test func appRenamePreservesExistingStorageAndSharedUSBLock() {
    let legacy = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("org.openlmea9.prototype", isDirectory: true)
    #expect(AdapterStorage.defaultDirectory == legacy)
    #expect(USBConnectionSafety.canonicalDirectory == legacy)
}
