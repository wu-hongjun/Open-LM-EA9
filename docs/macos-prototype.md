> Current app: **0.13.0, build 16** shows actual aperture as Unknown separately
> from the fixed camera f-number and packages the experimental AF 3.0 candidate.
> Automatic refresh, the Device dropdown and firmware-preserving lens changes
> remain. AF 3.0 upload and strict reconnect verification passed on October 14;
> camera acceptance subsequently failed with full-press freeze and battery-
> required recovery. Further AF 3.0 trials are held. See
> [the failure record](evidence/af-30-camera-failure-2026-10-14.md) and [the installation record](evidence/af-30-upload-2026-10-14.md), [the workflow](macos-device-workflow.md),
> [current validation](evidence/af-30-validation-2026-10-13.json) and
> [AF 3.0 milestone](evidence/af-30-candidate-2026-10-13.md).

# macOS prototype

> Current follow-up (prototype 0.3.0): the [USB metadata milestone](usb-metadata-milestone.md) adds a reviewed, bounded application upload, mandatory physical reconnect and full byte verification. Its first firmware candidate uses the reference C implementation with motor motion disabled. [Actual measurements](evidence/usb-metadata-milestone-2026-10-10.md) distinguish stock upload qualification, custom read-back and pending camera checks. The material below records the earlier research/prototype stage.

Version 0.2.0, October 10, 2026. Implements the user's authorized next step:
a visual Device-first overview, eight photographed lens profiles, local metadata editing and
verified read-only USB backup. The selected host stack is native Swift 6, SwiftUI, selective AppKit,
IOHID and CryptoKit. No external package, cloud account or Rust toolchain is
needed. Firmware language and the future management encoding remain open.

## Build and open

From the repository root, with Xcode and its command-line tools selected:

```sh
./scripts/swift-local.sh test
./scripts/build-macos-app.sh
open "dist/Open LM-EA9.app"
```

The package declares macOS 14 as its minimum. The packaging script builds for
the current host architecture, copies the resource bundle and native icon, and
ad-hoc signs/verifies the app. This is a local development build. Developer ID,
notarization, universal distribution, clean-machine and macOS 14 qualification
remain release work. See [the validation record](evidence/macos-prototype-2026-10-10.md)
for the original backup qualification, and [Device overview validation](evidence/macos-device-overview-2026-10-10.md) for version 0.1.1.
The current [visual validation](evidence/macos-visual-redesign-2026-10-10.md)
records the gallery, local preparation, compact editor and bundled-photo checks.
On a fresh checkout, restore the Git-ignored photos first using
`python3 references/visuals/fetch_assets.py`; see [photo provenance](../references/visuals/README.md).

`swift-local.sh` puts SwiftPM/compiler caches inside `.build` and disables
SwiftPM's nested process sandbox for this dependency-free local package. It
does not give the app administrative privileges. Open `apps/macos/Package.swift`
in Xcode for source navigation/debugging. Generated `.build`, `dist` and test
artifacts are excluded from Git; application source and scripts are tracked.

## Device overview

Every launch opens **Device**. It shows the LM-EA9 connection, firmware version
and **Lens Information**. **Refresh Connection** and startup discovery inspect
macOS HID properties without sending CHECK, READ or feature reports. Discovery
errors clear the displayed device list rather than retaining a stale connected
status. The current app monitors descriptors and local history every two seconds
and when it becomes active; automatic refresh sends no HID feature reports.

Firmware begins as **Not read** until a successful explicit **Read Version**
or backup. Open **Read version…** or **USB tools…** and prepare the connection
using the prerequisite checkbox first.
Read Version uses the same exclusive session, idle acknowledgement and persisted
reconnect guard as backup, and sends exactly one qualified CHECK, with no memory
reads. Qualified stock 1.8.0 and pinned custom 2.0.0, 2.1.0, 2.2.0, 2.3.0 and 2.4.0 responses are accepted. This is the
loader's reported version, not an installed-image or camera-behavior check.

A dated version observation is saved privately in Application Support as
`last-firmware-observation.json`. On later launches, a matching adapter's last
read is displayed with its timestamp. It is never represented as a fresh query.
USB descriptor version is not substituted for firmware. Anonymous adapters,
different serials, unqualified descriptors, corrupt or unsupported history do
not receive a cached version. **Read Version** explicitly refreshes it; startup,
connection refresh and tab navigation never do.

The Device card shows the last USB-verified adapter setting with its date.
The Device dropdown chooses a local preparation; **Apply profile** is a separate
USB action. **Edit library…** opens the secondary Lens Library tab. A passive
mounted lens cannot be electronically identified; the stored setting describes
what the camera is told. Older prototype stages did not yet read custom metadata.

## Lens workflow

Open **Lens Library** to browse the photo grid. **Prepare lens** saves a local
choice and returns to Device; the Device dropdown now switches profiles directly. Click a
photograph or sliders button to edit metadata in a sheet, then choose **Save
Lens** (Command-S). **Revert** restores the saved values. Closing the editor or
quitting protects unsaved edits with Save/Discard/Cancel. Invalid numeric fields
show an explanation and disable Save. Local metadata is never sent to the adapter.

The first launch seeds the library from the canonical
[requested inventory](../profiles/requested-lenses.json). A bundled copy is
checked against that file when packaging. Subsequent launches open the local
library rather than resetting it. All eight profiles retain their original
IDs and user-supplied names, including the 28–70 mm zoom. The Biotar is now
58 mm f/2 as confirmed by the owner; its legacy `zeiss-jena-biotar-55-f2` ID is
retained. Existing saved libraries are never silently reset. The macro's
calibration note is retained. **Photo Credits…** shows photo sources and variants.

For a zoom, enter a minimum, maximum and optional current focal length. Leave
the current setting blank if unknown. Nominal maximum aperture is a lens
specification; the optional aperture-ring setting describes a manually set
f-number. Neither setting is sensed through the passive mount. Calibration
remains explicitly unmeasured. The zoom's variable-aperture table, optical
model, camera-facing lens ID and focus-reference calibration are not invented.

The app saves to:

```text
~/Library/Application Support/org.openlmea9.prototype/profiles.json
```

The separate `prepared-lens.json` records only the locally chosen profile ID.
Neither file represents adapter configuration.

**Export saved library** in the library options or File menu writes versioned JSON using the native save panel.
Unsaved edits are excluded. **Import** validates and previews the profile
count/camera, then asks before replacing the local library. It preserves a
`profiles-before-import-<UUID>.json` copy of the prior file. Save current edits
or revert them before importing. An unreadable or newer-schema local file is
preserved, saving is disabled, and a valid import provides explicit recovery.

For development/UI checks, launch an isolated library:

```sh
open -n "dist/Open LM-EA9.app" --args --library-directory /tmp/ea9-ui-library
```

## USB backup workflow

Open **Device → USB tools…**, choose **Refresh Connection**, and expand
**Read-only USB backup**. Discovery sends no reports. Backup requires exactly one device
with the qualified descriptor. Close the official updater and other USB tools,
physically unplug/reconnect the USB cap, refresh, and check the prerequisite
box. Choose **Create Verified Backup…** and a new `.ea9backup` name.

The reconnect prerequisite is substantive: the stock loader treats reports as
flash data when an update session is already armed. Even a CHECK could then be
consumed as data. This app cannot determine that state without sending a
report. Exclusive access prevents concurrent host owners during explicit USB reads but
cannot clear a previously armed loader. See the
[measured investigation](usb-cap-investigation.md).

The backup qualifies the known CHECK response and bootloader code, confirms
chip/flash capacity, compares two complete main-flash reads and two reads each
of the user-fuse/calibration windows, then verifies the written files. Progress
and cancellation stay off the HID worker. Success publishes one private
package with a manifest and SHA-256 checksums. **Show in Finder** reveals it.
Existing backups are never overwritten. Failed/cancelled reads publish no
partial package.

After an uncertain exchange, cancellation, crash or interrupted session,
physically reconnect and refresh. The connection's registry ID is persisted in
`usb-reconnect-required.json` before the transaction and cleared on successful
completion. Relaunching the app does not bypass this guard. Conservative open
failures may also require reconnect. There are no automatic transport retries.
Refresh is manual; the prototype does not provide live hotplug notifications.

The package includes device serial/unit data. It is private local evidence,
with a `0700` directory and `0600` files. The app sends nothing to a server.
Complete flash read-back is verified; restoring an adapter from the backup is
**not qualified**. Other factory auxiliary rows and unique-ID words are outside
this backup. No install, restore, arbitrary memory access, feature report,
reset, motor command or profile-apply action exists in the app.

## Command-line diagnostics

The packaged CLI uses the same DeviceKit pipeline as the GUI:

```sh
./dist/ea9ctl inventory
./dist/ea9ctl backup /path/to/new-backup.ea9backup --idle
```

`--idle` acknowledges the same closed-updater/physical-reconnect prerequisite.
Inventory prints a redacted summary and sends no reports. Backup prints only
the destination, size, flash digest and exchange count. The manifest retains
private identity. `--state-directory PATH` can isolate the persistent reconnect
guard for development; use the shared default in normal operation. Run only
one USB client at a time.

Verify a saved package later without USB access:

```sh
python3 tools/verify_macos_backup.py /path/to/backup.ea9backup
```

This checks file sizes/hashes, the loader digest, chip/geometry and recorded
scope/counts. It does not independently prove the manifest's claimed hardware
read history or authenticate its creator.

## Module boundaries and future work

| Module | Responsibility |
| --- | --- |
| `LensCore` | Seed inventory, metadata validation, versioned local JSON, atomic saves/import preservation |
| `DeviceKit/Backup` | Closed CHECK/READ codec, qualification, read comparison, manifest and atomic package publication |
| `DeviceKit/FirmwareObservation` | Dated device-reported version, bounded private history, response qualification |
| `DeviceKit/NativeHID` | Descriptor discovery, exclusive session, owned run loop/callback buffers, deadline/cancellation/reconnect handling |
| `OpenLMEA9` | SwiftUI presentation, AppKit file panels/quit handling, draft versus saved state |
| `EA9CLI` | Headless access to the identical read-only service |

The device service reserves the entire operation using a lock, runs all native
HID lifetime operations on one worker thread, and returns Sendable value types.
It does not rely on actor isolation across `await` to serialize a transaction.
Every native report is constructed from the closed request enum. Callback data
is copied before the next report; mismatched type, ID, length, duplicate input,
unsolicited input or deadline failure stops the session. Swift's two
`@unchecked Sendable` classes are the cancellation token and device service;
their mutable cross-thread state is lock protected. Native objects/pointers
never cross into SwiftUI.

This prototype chooses the audit's pure Swift host alternative: shared Rust
code would currently add an FFI/build boundary without a firmware contract to
share. A future pure Rust codec can replace a bounded internal codec after
the firmware/management schemas earn that reuse. The Mac transport remains
native. The app is prepared for a separate management backend; stock backup
access does not establish application USB reachability or autofocus quality.

Next qualification includes a reachable management service, profile read-back,
firmware packaging/restoration evidence, body-specific optical/motion tests,
sleep/unplug stress and full VoiceOver/keyboard testing on supported OS builds.
See [system design](system-design-recommendation.md) and the separate
[profile/backup format contract](macos-prototype-formats.md).

Primary implementation sources: Apple's local SDK
`IOKit.framework/Headers/hid/IOHIDDevice.h` (exclusive opening, callback and
run-loop lifetime) and
[IOHIDDeviceSetReport](https://developer.apple.com/documentation/iokit/1588656-iohiddevicesetreport);
[Swift PackageDescription](https://docs.swift.org/package-manager/PackageDescription/PackageDescription.html).
Hardware behavior comes from the pinned local bootloader analysis and measured
USB evidence, rather than generic USB API documentation.


## Experimental AF milestone (0.4.0, build 7)

USB tools now includes an **Experimental autofocus** disclosure with explicit AF
and metadata-only installation actions. Both save a recovery backup, use pinned
images and require physical reconnect plus byte verification. AF uses 2.1.0;
metadata-only remains 2.0.0. Ordinary lens changes preserve verified AF capability.
An unknown/unverified firmware state does not imply that motor movement is disabled.
The landing page and secondary Lens Library retain their existing visual layout.
See [the 50mm AF-S runbook](af-s-test.md) for the first physical test and restoration.
No AF hardware upload or camera qualification occurred while building this version.
