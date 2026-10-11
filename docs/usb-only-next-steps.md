# USB-only development boundary

> Current follow-up (prototype 0.3.0): the [USB metadata milestone](usb-metadata-milestone.md) adds a reviewed, bounded application upload, mandatory physical reconnect and full byte verification. Its first firmware candidate uses the reference C implementation with motor motion disabled. [Actual measurements](evidence/usb-metadata-milestone-2026-10-10.md) distinguish stock upload qualification, custom read-back and pending camera checks. The material below records the earlier research/prototype stage.

October 10, 2026. The user reports that the adapter was unplugged and that USB
is the only available connection. No multimeter, logic analyser or SWD probe
is available for the current work.

The adapter has re-enumerated with the same identity and a new registry entry.
The [reconnect evidence](evidence/usb-cap-reconnect-2026-10-10.json) records
repeat CHECK, application-vector and qualified memory reads against the saved
baseline, including a third complete flash read that matches both earlier
backups. All 2,062 request/reply exchanges were verified offline. This supports
restart/reconnect repeatability. It is not an
instrumented measurement of power removal, reset timing or pin voltage.

## What we can proceed with

1. Keep the original loader and preserve its complete main-flash backup,
   user-fuse and calibration evidence. Use the known native HID CHECK/READ
   transport for read-only identification, backup/export and image comparison.
2. Build and validate pure E-mount framing, metadata/profile models and image
   packaging against archived captures and the reference implementation. Keep
   unknown autofocus/optical fields explicit. A host test cannot establish A7C II
   timing or physical focus accuracy.
3. Prototype the Mac lens library, local profile editing, device identification
   and backup workflows. The user's profiles can be edited and validated locally
   before a settings-write service exists. Show pending edits separately from
   device-confirmed metadata. Do not expose an Apply-to-device action until its
   transport and persistence path are qualified.
4. Build an offline, motor-disabled application candidate and establish its
   vector/linker map, USB lifecycle and resource use before an installation
   experiment. This can evaluate Rust and C without choosing the production
   stack prematurely. SwiftUI/AppKit remains the proposed Mac prototype.
5. Specify the application update/read-back procedure using the known loader,
   including padding, erase footprint, interruption handling and restoration of
   the saved application. Keep this separate from changing the bootloader.

The [native Mac prototype](macos-prototype.md) now implements local lens editing
and read-only backup within this boundary. See its separate
[validation evidence](evidence/macos-prototype-2026-10-10.md). Custom firmware,
application management and restoration remain unqualified; the app adds no
device-write operation.

## What USB alone has not established

The stock loader's inspected cap path remains in its USB loop. READ copies
memory; it supplies no demonstrated GPIO control, reset, arbitrary bootloader
programming or application-launch operation. A 4-byte HID feature descriptor
does not establish an alternative management service.

An application installed at `0x5000` can follow the normal application boot path,
but adding a USB driver there does not make it reachable through the unchanged
cap path. The [launch-extension proposal](management-entry-design.md) therefore
remains conditional on recovery and execution qualification. A successful backup
or a clear protection bit does not prove the bootloader can be restored.

Cap continuity, supply/PA23 voltages, mode contention, USB electrical quality and
SWD pad access remain unmeasured. The alternate-cap design cannot be selected
from software register samples alone. Independent debug/restore qualification
requires access beyond the currently available USB connection. Record these as
pending hardware constraints rather than silently dropping them.

Continue useful host and offline firmware work within this boundary. Do not
guess stock launch commands or repurpose the existing uploader as a bootloader
programmer. A concrete write experiment requires its own reviewed procedure,
backup scope and recovery evidence.

See [the initial investigation](usb-cap-investigation.md),
[the complete backup follow-up](usb-cap-followup.md), and
[the system recommendation](system-design-recommendation.md).
