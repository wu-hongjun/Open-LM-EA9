# Visual macOS prototype validation

October 10, 2026, version 0.2.0/build 3. Native SwiftUI/AppKit, Swift IOHID.
Host: macOS 27.0.1, Apple Silicon, Xcode 27.0 / Swift 6.4. This record covers
the visual app and local workflow; the earlier
[hardware backup](macos-prototype-2026-10-10.md) and
[explicit version-read](macos-device-overview-2026-10-10.md) records remain
historical evidence.

## Automated and asset checks

[Test output](macos-visual-tests-2026-10-10.txt): 17 tests passed, comprising
7 LensCore and 10 DeviceKit tests. The two new tests check independent local
choice persistence, missing/imported-away IDs, preservation of the metadata
library, invalid choices, unsupported schemas and oversized choice documents.
Existing validation, atomic import/save, corruption preservation, closed USB
request set, qualification, complete backup comparison and failure tests pass.
The seed test now expects the confirmed Biotar 58mm f/2.

Nine original images, their application copies, the bundled credit manifest
and canonical inventory are checked against recorded digests/copies. The build
includes both SwiftPM resource bundles. Photos are loaded through the native
bundle rather than HTTP. The release package is ad-hoc signed and verifies with
`codesign --verify --deep --strict`. This is not a notarized distribution build.

The complete reference collection verifier also passes after adding the visual
sources and hashes. Previous reference digests were retained, except the
intentionally updated reference README. See
[photo provenance](../../references/visuals/README.md) and
[redacted build/result hashes](macos-visual-build-2026-10-10.json).
The [final packaging log](macos-visual-build-2026-10-10.txt) records successful
photo verification, compilation and signing.

## Native UI checks

The release app was opened with an isolated library under
`artifacts/macos-prototype/visual-redesign/ui-library`. Accessibility text and
rendered screenshots were inspected using native app control.

- Device opened first with a rendered LM-EA9 photograph, connected USB-cap
  status, **Not read** in the isolated history, and Lens Information.
- **Choose a lens** opened the secondary Lens Library. The adaptive grid
  displayed three columns at the default window size. All eight card photos
  were inspected, including the zoom and confirmed 58mm Biotar after scrolling.
- Preparing the 28mm profile returned to Device with its photo and **Prepared
  on this Mac · Not applied**. The adapter-setting label remained unavailable.
  Its separate choice JSON contains schema 1 and the stable 28mm profile ID.
- The compact photo/detail editor opened from a card. A manual aperture of
  f/1.4 on the f/2 lens showed validation and disabled Save. Closing presented
  Save/Discard/Cancel; Cancel preserved the draft. Revert restored Unknown.
  A valid f/5.6 was saved in the isolated library, producing revision 2 and a
  timestamp. The editor showed Saved on this Mac and disabled Save/Revert.
- USB tools opened as a secondary sheet. Version read and backup were disabled
  with the prerequisite unchecked. Expanding backup exposed the same guarded
  action. No prerequisite was asserted and no hardware read was started.
- Photo Credits showed all nine source links, attribution, the zoom variant
  note and the Biotar's CC BY-SA 2.0 license link.
- Inspection revealed repeated numeric accessibility labels. The final build
  combines each numeric specification into one accessible element, avoiding
  duplicated announcements while preserving visible layout.

The normal user library was byte-identical to its pre-test copy throughout the
isolated workflow. Normal storage was opened separately for the owner's
explicit Biotar correction. Only that profile's display name, minimum/maximum
focal length and outdated note were changed, plus its normal save revision and
timestamp. The stable ID and maximum aperture were preserved; the other seven
profiles were unchanged. No arbitrary local lens was selected in normal storage.

The final app was left open on Device with the connected adapter and the
existing dated **1.8.0** observation. Firmware history and reconnect-state bytes
were unchanged by this revision. Startup, tab navigation, local editing and
the tools/credit sheets do not send CHECK/READ reports. No new hardware backup,
firmware update, configuration write, motor command or recovery was performed.

## Scope of qualification

The visual flow was inspected on the current host, with unit tests for the
new persistence. Full VoiceOver, minimum-OS, clean-machine, sleep/unplug stress
and automatic hotplug behavior remain unqualified. Connection changes still
require refresh. Source image redistribution rights, beyond the licensed
Biotar, are not established for a public release. Current-lens discovery and
apply/read-back still require qualified custom firmware management support.
