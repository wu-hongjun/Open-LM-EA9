import Foundation
import Testing
import LensCore
import DeviceKit
@testable import OpenLensAdapter

@MainActor @Test func bankPreviewUsesProfileSwitchingAndInhibitsEveryUSBAction() throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let model = AppPreview.make("bank",directory: folder)
    #expect(model.currentBankState?.configured.id == "zeiss-jena-biotar-55-f2")
    #expect(model.deviceLensSelectionID == "contax-zeiss-35-f1-4")
    #expect(model.bankActionLabel == "Test profile switch…")
    #expect(!model.canUseBankAction && !model.canRollbackBank && !model.canRequestDeviceRead)
    model.performPreparedBankAction(); model.rollbackBank(); model.verifyBankChange(); model.readAdapterLens()
    #expect(!model.busy && model.pendingBank == nil)
}

@MainActor @Test func bankPendingCameraApplicationNeverLooksCommittedOrReflashes() throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let model = AppPreview.make("bank-pending",directory: folder)
    #expect(model.currentBankState?.pendingCameraBoot == true && model.bankSelectionMatches)
    #expect(model.currentBankState?.committed.id == "zeiss-jena-biotar-55-f2")
    #expect(model.currentBankState?.configured.id == "contax-zeiss-35-f1-4")
    #expect(model.bankActionLabel == "Waiting for camera" && model.selectedLensState == "Queued for camera")
    #expect(model.installedProfileText.contains("pending camera startup"))
    #expect(!model.canUseBankAction && model.currentBankState?.configured.actualAperture == nil)
}

@MainActor @Test func bankSwitchRequiresCurrentConnectionReadAndExactBankMetadata() throws {
    let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer { try? FileManager.default.removeItem(at: folder) }
    let preview = AppPreview.make("bank",directory: folder.appendingPathComponent("preview"))
    let cached = try #require(preview.previewBankObservation)
    let model = AppModel(directory: folder.appendingPathComponent("normal"),inventory: { [] },reconnect: { _ in false })
    model.bankObservation = cached; model.devices = [cached.device]; model.stockUploadQualified = true
    model.chooseDeviceLens("contax-zeiss-35-f1-4")
    #expect(model.canUseBankAction && !model.canApplyLens) // never fall back to 4.7
    // A data-only UI fixture cannot bypass the service's receipt/backup gate.
    model.performPreparedBankAction()
    #expect(model.errorMessage != nil && !model.busy)
    model.chooseDeviceLens("contax-zeiss-28-70-f3-5")
    #expect(!model.canUseBankAction && model.preparedLensIssue != nil)
    let encoded = try JSONEncoder().encode(cached.device)
    var changed = try #require(JSONSerialization.jsonObject(with: encoded) as? [String: Any]); changed["id"] = 999
    model.devices = [try JSONDecoder().decode(DeviceIdentity.self,from: JSONSerialization.data(withJSONObject: changed))]
    model.chooseDeviceLens("contax-zeiss-35-f1-4")
    #expect(!model.canUseBankAction && model.bankActionHint.contains("Read"))
}
