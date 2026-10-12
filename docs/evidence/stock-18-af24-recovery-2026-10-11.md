# Stock 1.8 recovery after the AF 2.4 camera failure

October 11, 2026. Original same-unit stock recovery upload completed normally;
the owner physically reconnected the USB cap. **Normal native strict verification
and the independent readback audit passed.** Stock 1.8.0 is restored; the new
camera display/lifecycle and controlled AF-S comparison remain pending. The
[machine-readable record](stock-18-af24-recovery-2026-10-11.json) carries the
observed transaction state, counts and digests. The
[AF 2.4 failure investigation](af-24-camera-failure-2026-10-11.md) retains the
camera replies and separate mechanical counterexamples.

## Upload and evidence boundaries

Recovery transaction: `0FBD0A31-B440-4033-AD5B-7F105B688DF2`. Native `restore-stock`
completed with exit 0 at 23:55:53 UTC / 19:55:53 local. The original same-unit
backup and saved CLI were verified offline before transfer. Native transport
required an exclusive qualified USB device with the updater/app absent. A fresh
two-pass 128 KiB flash/auxiliary backup was synchronized, followed by a durable
recovery journal and the original full application slot:

- Application range: `0x5000..<0x20000`, 110,592 bytes.
- Application-slot SHA-256: `265f93797db99f2dbba5b649bf5b12bc19efadeaa8e9fe77ade5fca128d17173`.
- Original 20,172-byte vendor application SHA-256: `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
- Original 58 known START metadata bytes, version 1.8.0; the adjacent six
  loader-RAM-derived bytes remain excluded under the established strict rule.
- One START and 1,728 pages, each acknowledged exactly by the successful native
  engine. Counts follow engine/image evidence; no independent wire trace exists.
- No bootloader, protected-record write, read-after-START or verification
  exception was used. A physical reconnect precedes further reports.

The fresh pre-recovery flash SHA-256 is
`adcbcafc21c0ad44c25286f6684b15867f2b9d371b5ae04e612669f1b4f4e9e0`, exactly the
prior verified AF 2.4 image. Camera use did not change persistent flash. That
does not identify the runtime failure: flash logging was disabled, and the cap
power cycle erased volatile controller state. Private raw backups, unit identity,
calibration, journals and the recovery key remain excluded from Git.

## Reconnect verification

The owner replied “reconnected” after upload. Descriptor-only inventory found
one qualified device on a different unblocked connection; it sent zero reports.
The frozen native CLI completed normal `verify --idle` with exit 0 at
00:03:54 UTC October 12 / 20:03:54 local October 11. Two full flash and auxiliary
read passes matched, recording 4,359 CHECK/READ exchanges. The independent offline
before/after audit also passed:

- The complete original stock application slot and all 58 known START metadata
  bytes match the original same-unit source.
- Boot code and `0x4040..<0x5000` protected gap match the fresh pre-recovery backup;
  the saved-motion record was not reset to its original pre-camera values.
- Factory user-row, calibration and device-ID bytes match both the pre-recovery
  and original same-unit backups.
- Reported firmware is 1.8.0. The native verified journal/history and refreshed
  stock qualification were published; stale custom applied-lens history was
  removed. The app's firmware observation is back to 1.8.0.
- Post-recovery full-flash SHA-256 is
  `6a89393b01cad5a931e289ee1aaf03c7a3e0b840b7bf5c1c6261d03b51575f6b`.
  Original full-flash equality is not claimed because protected saved-motion
  changes from the earlier reviewed camera session remain preserved.

This transaction used normal strict verification, not the earlier reviewed
saved-motion resolution. Successful USB verification establishes restored bytes;
it does not substitute for the planned camera baseline below.

## Planned stock camera comparison

Start with a single lifecycle/display observation, after verification:

1. With the camera off and its USB cable disconnected, move the adapter from
   the cap to the A7C II with the C/Y-to-M converter and 50mm f/1.4. Support the
   lens and set its focus ring to infinity and physical iris to f/1.4.
2. Select still-photo P, MF and Pre-AF Off if available. Switch on without
   shutter/AF-ON input. Record startup/errors, motor movement and whether it
   stops, the exact aperture display, view brightness, shutter speed and ISO.
   Unknown/unavailable settings remain unverified; stock lens metadata is not
   assumed to identify this physical lens.
3. After any movement ends, wait a full ten seconds untouched and switch off
   once. Record idle, display shutdown and motor behavior. Leave the camera off
   for review. Do not half-press during this first check.

If stock also has a dark view or missing f-number, record that before AF; it
would not establish an AF-controller cause. If the lifecycle/display check is
normal, coordinate one AF-S attempt on a well-lit static textured target around
3–5 m, central Spot and Pre-AF Off. Release after lock or about two seconds;
record actual settings, hunting, focus indication and whether motion stops.
Retain an original photo only if acquisition permits it, then inspect sharpness
and EXIF. There is no measured matched comparison yet and no request to retry
the failed 2.4 candidate.

Stop for grinding, repeated stop impacts, continuous drive for about two seconds,
camera error/hang or motion continuing after power-off. Switch off; remove the
battery if motion continues, and do not retry. The
[historical runbook](../af-s-test.md) retains upload/restoration boundaries.
