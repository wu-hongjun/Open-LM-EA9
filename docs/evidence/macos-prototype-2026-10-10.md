# macOS prototype validation

October 10, 2026. Historical record for version 0.1.0; see the separate
[0.1.1 Device overview follow-up](macos-device-overview-2026-10-10.md). Scope: native Mac lens editor and **read-only** LM-EA9 backup.
The user authorized the prototype and connected-device testing. No firmware
update, application launch bridge, reset, arbitrary register/feature request,
motor command or metadata write to the device was performed.

## Environment and build

- Host: Apple Silicon, macOS 27.0.1.
- Xcode 27.0 (`27A266a`), Swift 6.4, SDK macOS 27.0.
- SwiftPM package declares macOS 14; native build produced arm64 executables.
- No external Swift packages, Rust installation or Intel translation needed.
- `scripts/swift-local.sh test`: 11 Swift Testing tests pass, 5 LensCore and
  6 DeviceKit. The XCTest compatibility output reports zero XCTest cases;
  the following Swift Testing output is the actual test result.
  [Full test output](macos-prototype-tests-2026-10-10.txt).
- [Build, source hashes and redacted result manifest](macos-prototype-build-2026-10-10.json).
  The final packaged CLI's SHA-256 equals the retained hardware-tested binary.
- `scripts/build-macos-app.sh`: release package, bundled inventory, native icon
  and local ad-hoc signature. `codesign --verify --deep --strict` succeeds.
- The first sandboxed build needed compiler cache relocation; release dSYM
  generation required execution outside the restricted tool sandbox. This
  changed build execution permissions, not application USB commands or device
  state. A local `open` launched the packaged app successfully.

## Automated checks

The test suite covers the eight seed profiles and unknown settings; the
user-supplied zoom/Biotar designations; invalid focal/aperture/zoom data;
unsupported schemas, unknown fields, duplicate IDs and oversized documents;
revision/time persistence; failed import preservation and successful import
backup; and preservation of corrupt libraries.

Device tests cover golden CHECK/READ bytes and address bounds; complete package
publication, recorded counts, every file's digest and private directory mode;
second-pass mismatch with no publication; failed version/loader/geometry
qualification before further requests; simulated timeout/cancellation/short
reply with no retry; and an existing backup preserved with zero requests.
Simulated loader data uses an internal test-only expected-digest injection.
The public device service always uses the production pinned digest.

## Connected-device test

1. The official `USB_Update` process was absent (`pgrep -x` exit 1). The adapter
   was in the previously qualified idle state following the user-reported
   unplug/reconnect and earlier read-only tests; no START command intervened.
2. Prototype inventory found one LM-EA9 with the exact qualified descriptor;
   inventory sent no reports. Serial/location are retained privately.
3. The release `ea9ctl` ran the identical DeviceKit service used by the GUI.
   It exclusively opened the adapter and completed **4,359 exchanges**:
   CHECK, loader qualification, DID/NVM, two main-flash passes and repeated
   user/calibration reads. No retry occurred.
4. While backup owned the adapter, a second descriptor-only `ea9ctl inventory`
   failed with IOKit `0xe00002c5`. This demonstrates exclusive access between
   these two processes on this Mac/device. It is not a universal claim about
   privileged drivers or every competing application.
5. The two 131,072-byte flash reads matched. Their SHA-256 is:

   ```text
   1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01
   ```

   This equals all three earlier complete research backups. The separately
   qualified `[0,4000)` code digest is:

   ```text
   8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895
   ```

6. Offline verification rehashed all five binary files and checked geometry,
   read counts and scope. The `[5000,5000+20172)` application bytes also equal
   the recovered official `EA9-VER-1-8-0.bin` exactly. No private image bytes or
   serial are copied into this public report.
7. The backup directory has mode `0700`; its files have mode `0600`.
   The successful session cleared its persisted reconnect marker.

Private evidence, excluded from Git:

```text
artifacts/macos-prototype/
  ea9ctl-hardware-tested
  usb-backup-transcript.txt
  offline-backup-verification.json
  device-state/usb-reconnect-required.json
  backups/LM-EA9-prototype-2026-10-10.ea9backup/
  ui-library/...
  LM-EA9-lens-library.json
  initial-release-build.txt
```

The native service deliberately preserves a reconnect marker before its first
report; it remains after uncertain failure, cancellation or a crash. Real
unplug/late-report/cancel stress was not intentionally induced on the adapter.
The existing [reconnect evidence](usb-cap-reconnect-2026-10-10.json) is separate
from this app's simulated failure tests.

## Native UI checks

Computer-use inspection of the actual packaged SwiftUI app confirmed:

- All eight sidebar profiles, Sony A7C II context and explicit local-save state.
- Setting the 28 mm lens's aperture ring to f/1.4 shows the validation reason
  and leaves Save disabled; f/5.6 enables Save.
- Saving f/5.6 updates the isolated local JSON to revision 2. The GUI displays
  “Saved on this Mac,” the revision and save time. Device metadata remains
  “Not applied.”
- Zoom min/max are 28/70 mm; active focal length and aperture ring begin
  unknown. Editing active focal length to 50 mm and switching sections presents
  Save/Discard/Cancel. Discard returns to the saved value.
- Backup discovery shows the qualified connected adapter. Create Backup is
  disabled until the prerequisite is checked; it then opens the native save
  panel. Cancelling that panel returns without starting a device transaction.
- Native export saves eight profiles to JSON; native import previews eight
  profiles for Sony A7C II and confirms replacement. Completing import returns
  to the saved profile. Offline comparison finds export and stored library
  identical, with one preserved pre-import copy.
- The rendered dark-mode layout was inspected for labels, spacing, sidebar
  visibility and scroll behavior. Native accessibility exposes named editable
  fields/buttons and the required confirmation controls. Full VoiceOver,
  keyboard-only and light-mode qualification remain pending.
- The isolated test instance quit normally before final packaging. Test edits
  stayed under `artifacts/macos-prototype/ui-library`; default user profiles
  were not used for test edits.
- The final package reopened with the normal Application Support library:
  eight original profiles, revision 1, unknown manual aperture/zoom settings.
  The offline package verifier also rejected a deliberately tampered copy of
  `flash.bin`; the original backup was preserved.

The two-pass hardware backup was executed through the shared headless service.
The GUI's destination panel was tested and cancelled; a second full hardware
backup from the GUI was not repeated. Local validation was tightened afterward
to reject unknown import fields and cap file reads; the full test suite passed
again. The UI and HID implementation stayed the same.

## Remaining qualification

This validates the prototype on this connected unit and current Mac. It does
not establish backup restoration, application USB reachability, camera metadata
application, autofocus performance, other bootloader/chip variants, Intel or
older supported macOS versions, Developer ID/notarization, clean-machine
installation, power-loss durability, or USB sleep/unplug stress. These gates
remain in [the system recommendation](../system-design-recommendation.md).
