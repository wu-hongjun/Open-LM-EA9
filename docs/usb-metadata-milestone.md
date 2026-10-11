# USB lens metadata milestone

This milestone uses the original LM-EA9 bootloader to install a personalized
application image. It does not add an application USB service or modify the
bootloader. SwiftUI/AppKit and Swift IOHID remain the Mac stack; the first
firmware candidate is a small C fork of the inspected reference. Rust remains
a later option after the camera behavior and hardware interfaces are measured.

## First qualification procedure

1. Close the official updater and reconnect the cap. Inventory sends no reports.
2. `ea9ctl qualify-stock --idle` exclusively opens one descriptor-matched adapter,
   pins its loader SHA-256, checks the MCU and flash geometry, and saves two
   matching full-flash reads plus factory-data snapshots in a private backup.
3. Confirm that the active stock application matches the recovered 1.8.0 image.
   Re-upload exactly the saved application region `[0x5000,0x20000)` and preserve
   the known loader metadata bytes. No application behavior is changed by this
   stock qualification image. No reports follow the last data acknowledgement.
4. Physically unplug and reconnect. `ea9ctl verify --idle` requires a new registry
   entry with the same serial, then performs two complete reads. It compares the
   application bytes, protected code, metadata and factory-data snapshots before
   recording a successful stock upload path for this unit.
5. `ea9ctl apply contax-zeiss-50-f1-4 --idle` takes another fresh verified backup,
   then installs the pinned metadata-only candidate with the requested profile.
6. Physically reconnect again and verify. Only this read-back can label the
   profile “on adapter”; acknowledgements and a version string are insufficient.
7. With the camera off, remove the USB cap, attach the adapter and the 50mm lens,
   then test the A7C II in **manual focus**, initially with the aperture ring at
   f/1.4. Check startup, displayed focal length/aperture, a photograph's EXIF,
   and clean shutdown. This firmware has no motor-motion implementation linked.

Stock upload qualification establishes an actual application write/read-back
on this unit. It does **not** establish recovery from arbitrary power loss,
bootloader restoration, an independent recovery route, or camera compatibility.
Those limits remain recorded rather than inferred from a successful upload.

## Host coordination and recovery records

Production app and CLI operations share the original canonical reconnect marker
in `~/Library/Application Support/org.openlmea9.prototype`. CLI `--state-directory`
changes library/journal locations, never this hardware safety marker. A shared
nonblocking file lock is held from safety admission until native handles close
and the final marker is published, preventing cooperating app/CLI instances from
using stale idle state. Corrupt safety state stops reports.

Recovery records are published as private temporary files, synchronized using
checked macOS `F_FULLFSYNC`, renamed atomically, then their directory entries and
ancestors are synchronized. The fresh backup files and manifest are also
synchronized before START. Publication failure stops the operation before START.
This is explicit OS persistence handling; destructive host-power-loss behavior
and filesystem/storage guarantees have not been qualified.

Corrupt local journal or optional history remains visible independently of USB
discovery. Ordinary lens changes stay disabled, while stock restore can use a
validated unit backup after a safe physical reconnect. Recovery preserves copies
of pending, applied and qualification records before replacement. A valid pending
stock transaction can still be verified when old optional records are corrupt.
Stopping firmware programming requires an explicit incomplete-application and
recovery warning; no retry or disarm report is sent.

## Loader contract and erase footprint

The qualified boot-code SHA-256 for `[0,0x4000)` is
`8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895`.
Dispatch at `0x257c` accepts `95 27 68 18 01 01` START, `02 02` CHECK and
`03 03` READ. START initializes the application pointer to `0x5000`. In state 2,
every report is a 64-byte application chunk; the pointer advances by 64. There
is no length field, END command, launch command, host-addressed program command,
or demonstrated disarm operation. An ACK echoes the report, not flash contents.

The write wrapper at `0x2534` invokes the flash driver through `0x0450`; its
read/modify/erase/write implementation begins at `0x0e78`. It reads four old
64-byte pages, overlays the requested bytes, erases the aligned 256-byte row,
then writes all four pages. Thus each 64-byte transfer incurs a row erase.
The host bounds the complete image, sends no padding beyond it, never retries
a page, and prohibits every read/control command after START even on error.

START also writes 64 bytes at `0x4000` from RX+6, even though only 58 bytes remain
in the 64-byte report. Four overread bytes come from the last READ-address
scratch; the next two come from adjacent loader RAM. The host finishes preflight
with a verified READ at address zero, preserves the known 58 metadata bytes,
and replaces only the declared version within them. The final six metadata bytes
are recorded as a loader side effect. Verification compares the first 58 exactly
and every byte outside `[0x4000,0x4040)` and the planned application region.
The bootloader's remaining metadata row is preserved by the driver's row merge.

The custom upload covers `[0x5000,0xa100)`, 20,736 bytes / 324 pages, plus START.
It cannot address boot code, fuse rows or calibration rows. Stock restoration
covers exactly `[0x5000,0x20000)`, 110,592 bytes / 1,728 pages, plus START.
An interruption can leave an incomplete application; reconnect before recovery.
The saved original stock application is usable with `restore-stock BACKUP --idle`
and subsequent reconnect/verify. Recovery may read an unknown metadata version,
but still requires the pinned loader, exact descriptor, MCU, flash geometry,
matching unit identity and two matching backups before writing.

## Profile and firmware behavior

The reference is pinned at `d52ed06cc449918f938e0695fbf29a0c4141f2b2`.
Its archived source remains unchanged. Our fork and inherited host tests are in
`firmware/ea9`; their MIT license and Microchip notices are retained.
`metadata_main.c` uses its startup, clock, UART, EIC, framing and shutdown paths.
It establishes the reference's zero-duty bridge state, releases the motor,
and services protocol traffic. Homing, braking and motor-drive functions must
be absent from the linked image; the build checks this and excludes flash logging.

The reserved 256-byte row at `0xa000` contains:

| Offset | Bytes | Field |
| --- | --- | --- |
| 0 | 8 | ASCII `EA9LENS1` |
| 8 | 2 | Schema 1, little endian |
| 10 | 2 | Length 256 |
| 12 | 2 | Selected focal length, millimetres × 10 |
| 14 | 2 | Maximum aperture on the native APEX scale |
| 16 | 2 | Manually selected reported aperture |
| 18 | 2 | Stock adapter lens ID 234; no invented Sony lens IDs |
| 20 | 4 | Local profile revision |
| 24 | 80 | NUL-padded printable ASCII profile ID, max 79 bytes |
| 104 | 64 | NUL-padded printable ASCII lens name, max 63 bytes |
| 168 | 84 | Reserved; must be zero |
| 252 | 4 | CRC-32/ISO-HDLC of bytes 0–251, little endian |

Apertures are quantized to the reference's 1/8-stop descriptor scale,
`AV = 4096 + 32 × round(16 × log2(f-number))`. Nominal f/1.4 becomes 4352;
f/2 becomes 4608; f/2.8 becomes 4864. With no current aperture supplied, the
reported value defaults to the profile maximum, explicitly a user-selected
report setting rather than a physical measurement. The fixed reported range
matches this manual setting because the adapter cannot actuate a lens iris.
Zoom profiles require a manually supplied active focal length. Optical rows
remain the stock table, uncalibrated for these lenses.

`em_set_focal_length` updates both focal pairs in 0x05 and 0x28 and the 0x06
defocus ladder. Aperture updates use the reference's 0x05/0x1b setters and the
camera-requested optional 0x28 copy. The name occupies the 0x3f text field;
its display or EXIF use by the A7C II remains a camera test. Transmit recomputes
checksums after edits. Invalid profiles halt before the handshake or motion.

## Build, state and evidence

`python3 scripts/build-firmware.py` fetches the pinned official Arm GNU 14.2.rel1,
Microchip SAMD21 DFP 2.0.4 and ARM CMSIS 5.9.0 archives when missing and checks
the digests in `firmware/dependencies.json`. DFP 2.0.4 supplies the register-union
API used by the reference. Startup vector member names are adapted to it.
The build links at `0x5000`, reserves the profile row and generates the bundled
template and Swift digest pin. The zero-profile template cannot run as a lens;
the app must personalize it. `scripts/test-firmware.py` runs inherited checks
and actual transmitted-frame checks with images generated by the Swift codec.

The native service persists its connection block before any transaction, and
`pending-update.json` before START. An upload success retains that connection's
block. A physical reconnect yields a fresh registry ID; verification also binds
the serial. Journals and backups contain unit data and remain private under the
app's Application Support directory. History and failed-read evidence are retained.
The read-only request type remains separate from the bounded upload type.

See the [milestone evidence](evidence/usb-metadata-milestone-2026-10-10.md) for
actual test results and hardware state. Earlier read-only documents describe
their earlier stage; this is the reviewed application-write procedure extending
that boundary. The separate bootloader-launch proposal remains unqualified.


## Experimental AF admission

The closed image allowlist admits the separately pinned 2.1.0 and 2.2.0 AF templates.
Backup, durable journals, firmware history, inspection and reconnect verification
recognize both versions. A matching version string alone cannot identify an AF
image: verification also requires its exact executable prefix and canonical lens
row. Stock restoration retains the original 1.8.0 source pin and unit checks,
including recovery from an unknown current version. The explicit metadata-only
fallback follows the same protected-range and reconnect rules.
[AF-S installation and restoration runbook](af-s-test.md).

The current Device dropdown prepares a profile locally and applies it using the
verified installed variant. AF upgrades are explicit in USB tools; the CLI AF
actions now select 2.2. Automatic connection/local-history refresh sends no HID
feature reports. See [the current app guide](macos-device-workflow.md) and
[AF 2.2 design](af-reconciliation.md).
