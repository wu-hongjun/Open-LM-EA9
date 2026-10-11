# Device-first macOS prototype follow-up

October 10, 2026. Version 0.1.1, native SwiftUI/AppKit and Swift IOHID.
This follows the user's requested hierarchy: connection, firmware and Lens
Information on launch, with the lens library in a secondary tab.

## Implementation

- Every launch selects **Device**. The overview shows connection status, a
  dated firmware observation, and Lens Information with **Open Lens Library**.
- The secondary **Lens Library** retains the eight original profiles, local
  metadata validation, import/export and Save/Revert. Leaving an unsaved lens
  for Device uses the same Save/Discard/Cancel protection as profile switches.
- Stock USB cannot report a mounted lens. The card states this explicitly;
  the local selection is never displayed as detected hardware metadata.
- Read-only backup remains available in a collapsed disclosure on Device.
- Startup, connection refresh and tab navigation inspect HID properties only.
  Version queries require the existing idle/reconnect acknowledgement and an
  explicit **Read Version** action. This sends one CHECK, no memory READs.
- Firmware history is bounded, dated, stored privately and associated through
  matching nonempty serial/manufacturer/product and qualified descriptors.
  A cached value is labelled **Last read**; corrupt or mismatched history is
  ignored. USB descriptor version is never used as firmware version.
- Firmware reads share backup's updater-absence check, exclusive HID session,
  deadline/callback validation, cancellation and persisted reconnect guard.
  Native handles close and the operation lock releases before an awaiting
  caller resumes. Discovery errors clear stale displayed devices.
- Profile and backup formats remain schema 1. Newly created backup manifests
  identify application version `0.1.1-prototype`. Original v0.1.0 evidence and
  the previously verified hardware backup are preserved.

## Automated validation

[Full test output](macos-device-overview-tests-2026-10-10.txt): all 15 Swift
Testing tests pass (5 LensCore, 10 DeviceKit). The new tests cover qualified
CHECK response versus an echo, short report or unsupported version; matching
cache identity across reconnect versus another/anonymous/unqualified device;
private history round-trip and invalid/oversized/schema failures; and an
unacknowledged version read rejected before native access or state mutation.
The existing complete-backup, qualification and failure tests continue to pass.

[Redacted build, source hashes and result record](macos-device-overview-build-2026-10-10.json).

## Native UI and connected-device checks

The packaged release opened with Device selected. Accessibility and rendered
layout inspection confirmed the connected/recognized USB cap, firmware initially
**Not read yet**, Lens Information and its eight-profile count, and a collapsed
backup disclosure. **Read Version** was disabled until the prerequisite was
acknowledged.

**Open Lens Library** selected the second tab and exposed all eight profiles.
A temporary f/5.6 aperture-ring draft was entered without saving. Returning to
Device presented Save/Discard/Cancel. Cancel kept the library selected and the
draft intact; Discard returned to Device. Reopening Lens Library showed the
original unknown ring setting, revision 1 and Save disabled. No profile file
was saved during this test.

The official updater was absent. The adapter retained the previously measured
idle connection following the user's unplug/reconnect and successful read-only
backup; no START command intervened. An explicit GUI **Read Version** completed
one CHECK and displayed **1.8.0**, with **Last read Oct 10, 2026 at 8:13:35 PM**
in the host's UI time zone (`2026-10-11T00:13:35Z` in local history). The CHECK
operation sends no memory READ, feature, update, reset or motor request. This
confirms the reported loader version only. The successful operation cleared
its reconnect marker and stored the observation privately.

Expanding backup enabled **Create Verified Backup…** under the same prerequisite.
Its native destination panel was opened and cancelled; no new backup transaction
was started. The previously verified 128 KiB hardware backup remains untouched.

After these checks, the library toolbar's persistence on Device was corrected:
toolbar actions now live at the tab container and the window toolbar is hidden
on Device. The final source passed all 15 tests again. The retained pre-toolbar
release executable and observation are private evidence under
`artifacts/macos-prototype/device-overview/`; the DeviceKit and AppModel code
used for the hardware query is unchanged by this presentation-only correction.


The final release package passed `codesign --verify --deep --strict`. It was
reopened after quitting on Lens Library and selected **Device**, displaying the
same dated 1.8.0 observation with the prerequisite unchecked. Navigating to
Lens Library exposed its toolbar; returning to Device removed it. The rendered
overview and accessibility state were inspected again, and the app was left
open on Device. Local history bytes and read timestamp remained unchanged
across relaunch/navigation, and the saved profile JSON is byte-identical to its
pre-test state. Firmware history has file mode `0600`.

This follow-up did not repeat the full hardware backup or intentionally induce
unplug/sleep/timeout/cancellation. Those remaining qualification limits and the
original backup evidence are in [the prototype record](macos-prototype-2026-10-10.md).
Connection changes in an already-open app currently require **Refresh Connection**.
No new installed-image, recovery, mounted-lens or autofocus claim is made.
