import Foundation
import LensCore
import IOKit
import IOKit.hid

private let descriptor = Data([0x06,0xff,0xff,0x09,0x01,0xa1,0x01,0x09,0x02,0x09,0x03,0x15,0x00,0x26,0xff,0x00,0x75,0x08,0x95,0x40,0x81,0x02,0x09,0x04,0x09,0x05,0x15,0x00,0x26,0xff,0x00,0x75,0x08,0x95,0x40,0x91,0x02,0x09,0x06,0x09,0x07,0x15,0x00,0x26,0xff,0x00,0x75,0x08,0x95,0x04,0xb1,0x02,0xc0])

private func identify(_ device: IOHIDDevice) throws -> DeviceIdentity {
    func property(_ key: String) -> Any? { IOHIDDeviceGetProperty(device, key as CFString) }
    func integer(_ key: String) -> UInt32 { (property(key) as? NSNumber)?.uint32Value ?? 0 }
    func string(_ key: String) -> String { property(key) as? String ?? "" }
    var id: UInt64 = 0
    guard IORegistryEntryGetRegistryEntryID(IOHIDDeviceGetService(device), &id) == kIOReturnSuccess else {
        throw DeviceError.failure("Cannot obtain the USB connection identity.")
    }
    let qualified = integer(kIOHIDVendorIDKey) == 0x0483 && integer(kIOHIDProductIDKey) == 0x575A
        && string(kIOHIDProductKey) == "LM-EA9" && string(kIOHIDManufacturerKey) == "TECHART"
        && integer(kIOHIDPrimaryUsagePageKey) == 0xFFFF && integer(kIOHIDPrimaryUsageKey) == 1
        && integer(kIOHIDMaxInputReportSizeKey) == 64 && integer(kIOHIDMaxOutputReportSizeKey) == 64
        && integer(kIOHIDMaxFeatureReportSizeKey) == 4 && property(kIOHIDReportDescriptorKey) as? Data == descriptor
    return DeviceIdentity(id: id, product: string(kIOHIDProductKey), manufacturer: string(kIOHIDManufacturerKey),
                          serial: string(kIOHIDSerialNumberKey), location: integer(kIOHIDLocationIDKey), qualifiedDescriptor: qualified)
}

/// Constructed, used, and destroyed on one worker thread for the entire transaction.
private final class HIDCollection {
    let manager: IOHIDManager
    let options: IOOptionBits
    var devices: [IOHIDDevice] = []
    init(exclusive: Bool) throws {
        options = IOOptionBits(exclusive ? kIOHIDOptionsTypeSeizeDevice : kIOHIDOptionsTypeNone)
        manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(kIOHIDOptionsTypeNone))
        IOHIDManagerSetDeviceMatching(manager, [kIOHIDVendorIDKey: 0x0483, kIOHIDProductIDKey: 0x575A] as CFDictionary)
        let result = IOHIDManagerOpen(manager, options)
        guard result == kIOReturnSuccess else {
            IOHIDManagerClose(manager, options)
            throw DeviceError.failure("Cannot open the adapter\(exclusive ? " exclusively" : "") (IOKit \(String(format: "0x%08x", result))). Close other USB tools and reconnect the cap.")
        }
        if let set = IOHIDManagerCopyDevices(manager) { devices = (set as NSSet).allObjects.map { $0 as! IOHIDDevice } }
    }
    deinit { IOHIDManagerClose(manager, options) }
}

/// All fields and the C callback are confined to the scheduled worker's run loop.
private final class ReportInbox {
    let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 64)
    var reply: Data?
    var count = 0
    var invalid = false
    deinit { buffer.deallocate() }
    func reset() { reply = nil; count = 0; invalid = false }
}

private let reportCallback: IOHIDReportCallback = { context, result, _, type, id, bytes, length in
    guard let context else { return }
    let inbox = Unmanaged<ReportInbox>.fromOpaque(context).takeUnretainedValue()
    inbox.count += 1
    guard result == kIOReturnSuccess, type == kIOHIDReportTypeInput, id == 0, length == 64, inbox.count == 1 else {
        inbox.invalid = true; return
    }
    inbox.reply = Data(bytes: bytes, count: 64)
}

private final class NativeTransport: ReadOnlyTransport, UploadTransport {
    let device: IOHIDDevice
    let inbox = ReportInbox()
    let runLoop: CFRunLoop
    let cancellation: CancellationToken
    var attemptedReport = false
    private var phase = USBSessionPhase()
    var uploadAttempted: Bool { phase.armed }
    init(device: IOHIDDevice, cancellation: CancellationToken) throws {
        self.device = device
        self.cancellation = cancellation
        runLoop = CFRunLoopGetCurrent()
        let result = IOHIDDeviceOpen(device, IOOptionBits(kIOHIDOptionsTypeSeizeDevice))
        guard result == kIOReturnSuccess else { throw DeviceError.failure("Exclusive adapter access failed. Close the updater and other USB tools.") }
        IOHIDDeviceRegisterInputReportCallback(device, inbox.buffer, 64, reportCallback, Unmanaged.passUnretained(inbox).toOpaque())
        IOHIDDeviceScheduleWithRunLoop(device, runLoop, CFRunLoopMode.defaultMode.rawValue)
    }
    deinit {
        IOHIDDeviceUnscheduleFromRunLoop(device, runLoop, CFRunLoopMode.defaultMode.rawValue)
        IOHIDDeviceRegisterInputReportCallback(device, inbox.buffer, 64, nil, nil)
        IOHIDDeviceClose(device, IOOptionBits(kIOHIDOptionsTypeSeizeDevice))
    }
    func exchange(_ request: ReadOnlyRequest) throws -> Data {
        try phase.requireIdle()
        try cancellation.check()
        return try exchangeData(request.encoded())
    }
    func send(_ report: UploadReport) throws -> Data {
        let data = try report.encoded()
        try phase.prepare(report)
        return try exchangeData(data)
    }
    private func exchangeData(_ data: Data) throws -> Data {
        try cancellation.check()
        inbox.reset()
        CFRunLoopRunInMode(.defaultMode, 0.002, false)
        guard inbox.count == 0, !inbox.invalid else { throw DeviceError.failure("Unsolicited USB report. Reconnect the cap; no retry was sent.") }
        attemptedReport = true
        let result = data.withUnsafeBytes { bytes in
            IOHIDDeviceSetReport(device, kIOHIDReportTypeOutput, 0, bytes.bindMemory(to: UInt8.self).baseAddress!, 64)
        }
        guard result == kIOReturnSuccess else { throw DeviceError.failure("USB report failed. Reconnect the cap; no retry was sent.") }
        let deadline = CFAbsoluteTimeGetCurrent() + 5
        while inbox.count == 0 && !inbox.invalid && CFAbsoluteTimeGetCurrent() < deadline {
            try cancellation.check()
            CFRunLoopRunInMode(.defaultMode, 0.01, false)
        }
        guard CFAbsoluteTimeGetCurrent() < deadline, !inbox.invalid, inbox.count == 1, let reply = inbox.reply else {
            throw DeviceError.failure("Missing, late or invalid USB reply. Reconnect the cap; no retry was sent.")
        }
        // Give duplicate replies a chance to surface before accepting the exchange.
        CFRunLoopRunInMode(.defaultMode, 0.002, false)
        guard inbox.count == 1, !inbox.invalid else { throw DeviceError.failure("Multiple USB replies. Reconnect the cap; no retry was sent.") }
        try cancellation.check()
        return reply
    }
}

/// NSLock reserves the entire operation, including every await in callers. The worker owns all CF/HID objects.
public final class DeviceService: @unchecked Sendable {
    private let worker = DispatchQueue(label: "org.openlmea9.usb", qos: .userInitiated)
    private let lock = NSLock()
    private var busy = false
    private let stateDirectory: URL
    let safety: USBConnectionSafety
    public init(stateDirectory: URL) {
        self.stateDirectory = stateDirectory
        safety = USBConnectionSafety(directory: USBConnectionSafety.canonicalDirectory)
    }
    // Offline tests may isolate safety state; this is not exposed to CLI callers.
    init(stateDirectory: URL, safety: USBConnectionSafety) {
        self.stateDirectory = stateDirectory; self.safety = safety
    }

    private func reserve() throws {
        try lock.withLock {
            guard !busy else { throw DeviceError.failure("Another device operation is already running.") }
            busy = true
        }
    }
    private func release() { lock.withLock { busy = false } }
    public func reconnectRequired(for id: UInt64) async throws -> Bool {
        try reserve()
        return try await withCheckedThrowingContinuation { continuation in
            worker.async {
                let result = Result { try self.safety.blocked().contains(id) }
                self.release()
                continuation.resume(with: result)
            }
        }
    }
    public func inventory() async throws -> [DeviceIdentity] {
        try reserve()
        return try await withCheckedThrowingContinuation { continuation in
            worker.async {
                let result = Result {
                    let collection = try HIDCollection(exclusive: false)
                    defer { withExtendedLifetime(collection) {} }
                    return try collection.devices.map(identify).sorted { $0.id < $1.id }
                }
                self.release()
                continuation.resume(with: result)
            }
        }
    }
    public func backup(device: DeviceIdentity, to destination: URL, idleAcknowledged: Bool,
                       cancellation: CancellationToken, progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> BackupResult {
        guard !FileManager.default.fileExists(atPath: destination.path) else { throw DeviceError.failure("Choose a new backup name. Existing backups are preserved.") }
        return try await withIdleDevice(device: device, idleAcknowledged: idleAcknowledged, cancellation: cancellation) { transport in
            try BackupEngine().run(transport: transport, identity: device, destination: destination,
                                   cancellation: cancellation, progress: progress)
        }
    }

    /// One CHECK only. Never runs automatically on launch, refresh or tab navigation.
    public func readFirmware(device: DeviceIdentity, idleAcknowledged: Bool,
                             cancellation: CancellationToken) async throws -> FirmwareObservation {
        try await withIdleDevice(device: device, idleAcknowledged: idleAcknowledged, cancellation: cancellation) { transport in
            FirmwareObservation(device: device, version: try qualifiedFirmwareVersion(transport.exchange(.check)))
        }
    }

    public func pendingUpdate() throws -> PendingUpdate? { try UpdateStore(directory: stateDirectory).load() }
    public func appliedLens() throws -> AppliedLens? { try UpdateStore(directory: stateDirectory).loadApplied() }

    public func apply(profile: LensProfile, variant: FirmwareVariant = .metadataOnly, device: DeviceIdentity, idleAcknowledged: Bool,
                      preserveInstalledFirmware: Bool = false,
                      cancellation: CancellationToken, progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> PendingUpdate {
        guard try stockUploadQualified(for: device) else { throw DeviceError.failure("Prepare and verify the adapter’s stock upload path before installing custom firmware.") }
        let image = try ApplicationImage.personalized(profile, variant: variant)
        return try await upload(image: image, device: device, idleAcknowledged: idleAcknowledged,
                                cancellation: cancellation, recovering: false,
                                preserving: preserveInstalledFirmware ? variant : nil, progress: progress)
    }
    public func stockUploadQualified(for device: DeviceIdentity) throws -> Bool {
        try UpdateStore(directory: stateDirectory).qualified(for: device)
    }
    public func qualifyStockUpload(device: DeviceIdentity, idleAcknowledged: Bool, cancellation: CancellationToken,
                                   progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> PendingUpdate {
        return try await upload(image: nil, device: device, idleAcknowledged: idleAcknowledged,
                                cancellation: cancellation, recovering: false, progress: progress)
    }
    public func restoreStock(backupURL: URL, device: DeviceIdentity, idleAcknowledged: Bool,
                             cancellation: CancellationToken, progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> PendingUpdate {
        let backup = try VerifiedBackup(url: backupURL, device: device)
        let image = try ApplicationImage.stockRestoration(backup)
        return try await upload(image: image, device: device, idleAcknowledged: idleAcknowledged,
                                cancellation: cancellation, recovering: true, progress: progress)
    }
    private func upload(image candidate: ApplicationImage?, device: DeviceIdentity, idleAcknowledged: Bool,
                        cancellation: CancellationToken, recovering: Bool,
                        preserving variant: FirmwareVariant? = nil,
                        progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> PendingUpdate {
        let store = UpdateStore(directory: stateDirectory)
        if !recovering, let pending = try store.load(), pending.needsVerification {
            throw DeviceError.failure("The previous upload needs a reconnect and verification before another lens change.")
        }
        return try await withIdleDevice(device: device, idleAcknowledged: idleAcknowledged, cancellation: cancellation) { transport in
            guard !device.serial.isEmpty else { throw DeviceError.failure("A USB serial is required to bind this update and its backup to the same adapter.") }
            let folder = store.directory.appendingPathComponent("USBBackups", isDirectory: true)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            let backupURL = folder.appendingPathComponent("before-\(UUID().uuidString).ea9backup", isDirectory: true)
            _ = try BackupEngine(allowRecoveryVersion: recovering).run(transport: transport, identity: device, destination: backupURL, cancellation: cancellation, progress: progress)
            let backup = try VerifiedBackup(url: backupURL, device: device, allowRecoveryVersion: recovering)
            try backup.synchronizeRecoveryEvidence()
            if let variant {
                do { try ApplicationImage.requirePreservedFirmware(variant, in: backup) }
                catch {
                    // Refresh local evidence from the read already completed; retain
                    // unsupported-image backups and never send START on this path.
                    _ = try? LensInspection.publish(backup, to: store)
                    throw error
                }
            }
            // The loader copies four bytes of this READ address beyond START's payload.
            // Set the address scratch to zero and verify the response before arming it.
            guard try transport.exchange(.flashBlock(0)) == backup.flash.prefix(64) else { throw DeviceError.failure("Final idle preflight read did not match.") }
            let image = try candidate ?? ApplicationImage.stockRestoration(backup)
            let metadata = image.metadataOverride ?? Data(backup.flash[0x4000..<0x403a])
            var expectedMetadata = metadata
            expectedMetadata.replaceSubrange(0..<3, with: image.version)
            if recovering { try store.preserveBeforeRecovery() }
            var pending = PendingUpdate(transactionID: UUID(), device: device, backupURL: backupURL,
                image: image.data, version: image.version, setting: image.setting, createdAt: Date(),
                uploadedAt: nil, verifiedAt: nil, imageSHA256: digest(image.data), expectedMetadata: expectedMetadata)
            try store.save(pending) // Durable recovery record BEFORE the first write.
            try UploadEngine().run(transport: transport, image: image, metadata: metadata,
                                   cancellation: cancellation, progress: progress)
            pending.uploadedAt = Date(); try store.save(pending)
            return pending
        }
    }
    public func verifyUpdate(device: DeviceIdentity, idleAcknowledged: Bool, cancellation: CancellationToken,
                             progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> AppliedLens? {
        let store = UpdateStore(directory: stateDirectory)
        guard let pendingRecord = try store.load(), pendingRecord.needsVerification else { throw DeviceError.failure("No upload is waiting for verification.") }
        guard device.id != pendingRecord.device.id, device.serial == pendingRecord.device.serial else {
            throw DeviceError.failure("Physically unplug and reconnect the same adapter before verification. No reports were sent.")
        }
        let original = try VerifiedBackup(url: pendingRecord.backupURL, device: device, allowRecoveryVersion: true)
        return try await withIdleDevice(device: device, idleAcknowledged: idleAcknowledged, cancellation: cancellation) { transport in
            var pending = pendingRecord
            let destination = original.result.url.deletingLastPathComponent().appendingPathComponent("after-\(pending.transactionID).ea9backup", isDirectory: true)
            // A failed disk publication or prior verification keeps its evidence intact.
            let unique = FileManager.default.fileExists(atPath: destination.path) ? destination.deletingLastPathComponent().appendingPathComponent("after-\(UUID().uuidString).ea9backup") : destination
            _ = try BackupEngine().run(transport: transport, identity: device, destination: unique, cancellation: cancellation, progress: progress)
            let current = try VerifiedBackup(url: unique, device: device)
            let applied = try VerificationEngine().verify(pending: pending, current: current, original: original)
            try FirmwareObservationStore(directory: store.directory).save(FirmwareObservation(device: device,
                version: current.result.manifest.reportedFirmwareVersion))
            if let applied { try store.saveApplied(applied) }
            else {
                if FileManager.default.fileExists(atPath: store.appliedFile.path) { try FileManager.default.removeItem(at: store.appliedFile) }
                try store.saveQualification(device: device, transactionID: pending.transactionID)
            }
            pending.verifiedAt = Date(); try store.save(pending)
            return applied
        }
    }
    public func readLens(device: DeviceIdentity, idleAcknowledged: Bool, cancellation: CancellationToken,
                         progress: @escaping @Sendable (BackupProgress) -> Void) async throws -> AppliedLens? {
        if let pending = try pendingUpdate(), pending.needsVerification { throw DeviceError.failure("Reconnect and verify the pending upload first.") }
        let store = UpdateStore(directory: stateDirectory)
        return try await withIdleDevice(device: device, idleAcknowledged: idleAcknowledged, cancellation: cancellation) { transport in
            let folder = store.directory.appendingPathComponent("USBBackups", isDirectory: true)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            let url = folder.appendingPathComponent("inspect-\(UUID().uuidString).ea9backup")
            _ = try BackupEngine().run(transport: transport, identity: device, destination: url, cancellation: cancellation, progress: progress)
            return try LensInspection.publish(VerifiedBackup(url: url, device: device), to: store)
        }
    }

    private func withIdleDevice<T: Sendable>(device: DeviceIdentity, idleAcknowledged: Bool,
        cancellation: CancellationToken, operation: @escaping @Sendable (NativeTransport) throws -> T) async throws -> T {
        guard idleAcknowledged else { throw DeviceError.failure("Close the official updater and physically reconnect the USB cap first.") }
        try reserve()
        return try await withCheckedThrowingContinuation { continuation in
            worker.async {
                let result = Result {
                    try cancellation.check()
                    let sessionLock = try self.safety.acquire()
                    defer { sessionLock.release() }
                    var ids = try self.safety.blocked()
                    guard !ids.contains(device.id) else { throw DeviceError.failure("This connection requires a physical unplug/reconnect before another USB read.") }
                    let process = Process()
                    process.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
                    process.arguments = ["-x", "USB_Update"]
                    process.standardOutput = FileHandle.nullDevice
                    process.standardError = FileHandle.nullDevice
                    try process.run(); process.waitUntilExit()
                    guard process.terminationStatus == 1 else { throw DeviceError.failure("The official updater may be running. Close it before reading the adapter.") }
                    // Fail closed across a crash, quit or app relaunch during a transaction.
                    ids.insert(device.id)
                    try self.safety.writeBlocked(ids)
                    do {
                        let collection = try HIDCollection(exclusive: true)
                        defer { withExtendedLifetime(collection) {} }
                        guard collection.devices.count == 1, let target = collection.devices.first else {
                            throw DeviceError.failure("Connect exactly one LM-EA9 for USB reads.")
                        }
                        let current = try identify(target)
                        guard current == device, current.qualifiedDescriptor else { throw DeviceError.failure("The USB connection or descriptor changed. Refresh the adapter list.") }
                        let transport = try NativeTransport(device: target, cancellation: cancellation)
                        do {
                            let result = try operation(transport)
                            if !transport.uploadAttempted {
                                ids.remove(device.id)
                                try self.safety.writeBlocked(ids)
                            }
                            return result
                        } catch {
                            if !transport.attemptedReport { ids.remove(device.id); try self.safety.writeBlocked(ids) }
                            throw error
                        }
                    } catch {
                        // A conservative persisted marker may remain even after an open failure.
                        // Physically reconnecting provides a fresh registry identity.
                        throw error
                    }
                }
                // Close native handles and release the slot before resuming an awaiting UI caller.
                self.release()
                continuation.resume(with: result)
            }
        }
    }
}
