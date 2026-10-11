# Astra implementation audit remediation — October 10, 2026

The independent [Astra audit](../audits/astra-implementation-audit-2026-10-10.md)
identified two P1 host coordination gaps and three P2 recovery, cancellation and
durability issues. The reviewer examined the corrections and found no unresolved
P1 objection in that bounded source pass. This record covers the changed host;
the metadata firmware template is unchanged.

## Corrections

- Canonical hardware safety state is separate from caller-selected library and
  journal directories. The existing default reconnect marker was not cleared.
- A canonical nonblocking `flock` spans admission, safety loading/publication,
  the entire native transaction and native handle destruction. This coordinates
  cooperating app/CLI instances; it does not constrain third-party tools.
- Private recovery records use checked `F_FULLFSYNC`, atomic rename and directory
  synchronization. All fresh backup files and the manifest are synchronized
  before START. Synchronization failure stops preflight.
- Local journal/history errors preserve connection discovery and expose recovery
  tools. Normal lens changes fail closed. Valid pending stock verification is
  independent of corrupt optional history; recovery archives all three original
  records before replacement.
- Cancellation accurately names the USB operation and warns before stopping
  firmware programming. Quit retains its existing explicit interruption warning.

## Offline checks

- Expanded complete Swift suite: **32 passed** (7 LensCore, 25 DeviceKit).
- One additional targeted recovery-preservation regression passed after addition;
  current source contains **33 tests** total. This test checks intact corrupt
  source records, byte-identical private recovery copies and all three record types.
- Safety regressions check alternate libraries sharing the canonical production
  marker, blocked simulated IDs rejected before native access, competing lock
  ownership plus state reload after release, and corruption failing closed.
- The initial synchronization regression failed on macOS path alias/root traversal;
  directory synchronization now follows legitimate aliases and stops at `/`.
  The corrected full suite passed. Data-file opens still reject final symlinks.
- The independent reviewer separately ran the original 28-test Swift suite and
  sanitizer-enabled C framing/profile checks on seven prime-lens fixtures.
- No adapter report was sent during audit or remediation. The separate REA study
  remains offline, using the recovered firmware and existing captures.

Package validation and subsequent hardware measurements are recorded below as
they complete. OS synchronization is not destructive host-power-loss testing;
camera behavior and arbitrary interrupted-power recovery remain unqualified.

## Packaged build and stock verification

Prototype **0.3.0 build 5** was rebuilt and passed strict ad-hoc signature
verification. Both standalone CLI resource bundles now ship beside `ea9ctl`.
An offline prepare smoke check exposed the missing DeviceKit bundle; a subsequent
rebuild while the previous CLI was running also exposed unsafe in-place executable
replacement. Packaging now signs and verifies a new staged CLI inode and publishes
it by rename. The packaged offline prepare smoke check then passed.

Prepared Contax Zeiss 50mm f/1.4 image: **20,736 bytes**, SHA-256
`2b4c06eccce389aa580177d81d28c3aca4c581ccc59f2a194a5e2814bfdfe61c`.
Independently decoded row: focal length ×10 = 500, maximum/reported AV = 4352,
name `Contax Zeiss 50mm f/1.4`, CRC valid.

The owner subsequently confirmed a physical unplug/reconnect. Packaged
`ea9ctl verify --idle` completed stock verification successfully: two matching
complete flash reads, exact saved application-region equality, protected-region
and factory-data checks, and 58 known metadata bytes. The unit's stock upload
qualification was recorded. See [stock readback evidence](stock-upload-2026-10-10.json).
Only after this success was the custom 50mm upload started, with a fresh verified
backup required before START. Custom readback and camera checks remain separate.

The custom upload subsequently finished successfully: 324 data pages plus START,
the expected image SHA-256, and a fresh verified two-pass backup. The persisted
reconnect marker remains set and no post-upload HID report has been sent.
Build 5's native Device screen was inspected after launch: correct prepared
50mm lens, dated stock observation, pending custom verification, disabled Apply
and Verify on the armed connection. See [custom upload evidence](custom-50-upload-2026-10-10.json).

The owner then confirmed another physical reconnect. Custom verification completed
successfully with 4,359 exchanges and two matching complete flash passes. The
intended 20,736 application bytes, known metadata and protected/factory data all
passed. The applied-lens record was published and the verification connection's
temporary safety block cleared. Camera behavior remains unqualified.

Build 6 refreshes saved firmware observations during ordinary local-state refresh,
allowing completed CLI verification to update the app without another HID report.
The adapter image and DeviceKit upload/safety implementation are unchanged.

Build 6 packaging and strict app/CLI signature checks passed. Native Device
inspection after launch and Refresh showed firmware 2.0.0 and the USB-verified
Contax 50mm f/1.4 record with its timestamp, and no pending upload. Refresh sends
no HID reports. The owner was asked to perform the camera MF/EXIF/shutdown check;
those observations were still pending at this stage.

The subsequent A7C II photograph confirms all three requested EXIF fields:
50mm, f/1.4 and `Contax Zeiss 50mm f/1.4`. The owner reported Auto exposure mode
and an unknown focus mode; camera display and clean shutdown remain unconfirmed.
The reported absence of motor motion matches this metadata-only build. See
[camera metadata evidence](camera-50-metadata-2026-10-10.md). This physical
metadata result does not extend the audit's offline autofocus qualification.
