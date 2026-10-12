# AF 2.8 loaded-lens failure — October 12, 2026

**Camera acceptance failed. Stop further AF 2.8 camera trials.** The owner
reports a frozen preview, intermittent/poor focus response, darker exposure on
a later restart, and finally a shutdown hang requiring battery removal. The
numeric aperture display was f/1.4. Successful USB installation remains a
separate fact; it does not qualify autofocus, exposure or lifecycle behavior.

## Owner observations, in order

1. “the preview freezes, I can see f1.4, motor doesn't do anything when trying
   to focus.”
2. “it shuts down normally, upon restart the motor starts to sort of focusing
   but is not very responsive when trying to reach focus.”
3. “i restarted again, exposure is off (darker) and the camera is irresponsive
   to shutdown, i had to take out the battery.”

The early normal shutdown does not override the later failed shutdown. The
owner restarted while reporting results; no additional restart or focus retry
was requested after the first failure. The exact onset of the preview freeze,
actual MF/AF-S/AF-C and Pre-AF settings, exposure mode, physical focus/iris-ring
positions, shutter speed, ISO, saved-photo exposure and optical lock remain
unverified. The intended setup was Contax Zeiss 50mm f/1.4 on C/Y-to-M and
LM-EA9, with A/MF/Pre-AF Off if available. Intended settings are not observations.
No new photo or repeat of the failure is required to accept the report.

## Conclusions and limits

- f/1.4 is a confirmed display observation, not a measured iris or proof that
  exposure/metadata behavior is correct in every frame.
- No movement in MF would be expected. Because the actual focus mode was not
  reported, the first no-movement observation is not diagnosed as an AF motor
  fault. Later motor response rules out the blanket claim that no motor response
  occurred in any session.
- The frozen preview and battery-required shutdown are failures regardless of
  focus mode. A darker reported view is accepted; no exposure magnitude or
  physical-iris cause is proven.
- Motor movement does not establish homing, valid encoder feedback, completion
  delivery, optical focus lock or sharpness. This is not a confirmed AF-S result.
- The [strict USB transaction](af-28-upload-2026-10-12.md) matched the entire
  pinned application/profile, known metadata, protected flash and checked
  factory data. That result is preserved, not relabeled as a camera pass.

## Bounded source inspection

The camera-failure follow-up inspected production initialization, foreground
status scheduling, homing, sensor/fault guards and shutdown ownership without
changing firmware or sending hardware reports. It did not reproduce the camera
hang or recover a live protocol trace. No cause has been established.

The measured-motion probe in `firmware/ea9/hosttest/test_motion_telemetry.c`
explicitly seeds `em_handshake_done = 1` and `g_homed = 1`. It exercises actual
status frames after those conditions but does not run the complete startup
exchange. The lifecycle probe calls homing/shutdown routines in a mechanical
simulation; the register-startup probe supplies modeled peripheral transitions.
Those finite checks do not model the A7C II's lens initialization, concurrent
hardware timing, complete preview/exposure behavior or all startup/fault paths.
Repeating them cannot turn this reported camera failure into a pass.

Current source marks handshake completion after replying to initialization
message 0x0a. Homing is gated by handshake, shutdown and session-fault state;
focus command execution is gated by a committed reference. After homing, idle
encoder feedback is sampled before foreground protocol service. Those gates,
real sensor transaction latency and startup reply ownership need integrated
comparison with recovered factory behavior. Shutdown park/powerdown handling
and status/query responses must remain serviceable across faulted, unhomed and
active-motion sessions. These are investigation targets, not proven diagnoses.
Do not disable feedback guards, alter PID gains or guess an aperture correction
from the present report.

Flash diagnostics are disabled in this release. Battery removal erased volatile
state; returning to the USB cap also power-cycles the application. A flash backup
can preserve the image/persistent state and detect changes, but cannot reconstruct
the lost runtime fault or E-mount traffic. The factory REA controller/writer
findings remain useful local baselines; full interrupt/peripheral/camera behavior
has not been reverse engineered or demonstrated equivalent.

## Recovery and next gate

The owner has been asked to keep the camera off, remove the adapter with power
disconnected, physically reconnect its USB cap to the Mac and keep the updater
closed. The owner subsequently confirmed USB-cap readiness and explicitly
requested restoration. Original same-unit stock 1.8 upload, post-upload physical
reconnect, strict two-pass verification and the separate offline audit passed. See
[the separate recovery transaction](stock-18-af28-recovery-2026-10-12.md). Camera
trials remain suspended.

All original backup files match their manifests; the full source flash hash is
`1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`.
The original 20,172-byte application hash is
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`,
and the complete 110,592-byte restoration slot hash is
`265f93797db99f2dbba5b649bf5b12bc19efadeaa8e9fe77ade5fca128d17173`.
The unit binding, loader/version, original application/slot and two-pass source
evidence were checked without opening a USB device. The public recovery bundle
checksum and standalone CLI signature also verify. AF 2.8's verified journal,
applied profile, dated observation, stock qualification and connection-marker
documents were copied into a new private recovery evidence directory before
any restoration. The original canonical records remain unchanged.

Use the normal native restoration path with its fresh two-pass pre-write backup,
durable same-unit journal and unchanged protected-flash rules. After upload,
require another physical reconnect and strict readback before camera use.
Stock recovery is a lifecycle/AF fallback; the earlier owner-reported stock
aperture/exposure limitations remain recorded. Do not claim those are fixed by
restoration. No replacement AF candidate is built or uploaded by this diagnosis.

Private recovery preparation is retained under ignored
`artifacts/private/af28-recovery-2026-10-12/`; raw unit/backup contents are not
published. See [the sanitized observations](af-28-camera-failure-2026-10-12.json).
