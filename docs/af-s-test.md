# A7C II acceptance: AF 2.9, Contax Zeiss 50mm f/1.4

The [AF 2.9 candidate](../firmware/candidates/2.9.0/README.md) and app
0.12.0/build 15 passed offline preparation. **AF 2.9 is uploaded and strictly
byte-verified after owner-confirmed physical reconnect**, including a separate
offline audit. **Camera acceptance failed:** the owner reports focus achievement
followed by immediate capture-time freeze and battery-required recovery.
Further AF 2.9 trials are held. See [the failure and finite protocol investigation](evidence/af-29-camera-failure-2026-10-12.md).
The fresh pre-upload stock backup
matches the [strictly verified restoration](evidence/stock-18-af28-recovery-2026-10-12.md).
See [the installation record](evidence/af-29-upload-2026-10-12.md).
The initial loaded-lens lifecycle check was requested; actual settings and a
controlled AF-S result remain unverified. Do not repeat this image's test. The
procedure below is the qualification plan for a separately prepared replacement.

AF 2.8 remains held after owner-reported preview freeze, poor focus response,
darker exposure and a shutdown hang requiring battery removal.
[Its failures](evidence/af-28-camera-failure-2026-10-12.md) and successful USB
verification remain recorded. Its f/1.4 display alone did not qualify exposure
or lifecycle. The original photograph from the older stock comparison was not
retained and is not required to continue.

AF 2.9 fixes demonstrated fault-service, transmit-completion and new-handshake
admission defects. It retains the controller/reference/aperture/motion observer;
those changes have not proven the owner's physical failures resolved. See
[implementation, factory basis and limits](evidence/af-29-link-service-2026-10-12.md).
No further AF 2.8 trials are requested.

AF 2.4 passed USB verification but failed focus acquisition, with a dark view
and no shown f-number in P/A. Further trials of that frozen image are suspended.
See [the failure investigation](evidence/af-24-camera-failure-2026-10-11.md),
[completed stock recovery](evidence/stock-18-af24-recovery-2026-10-11.md), and
[2.9 implementation and tests](evidence/af-29-link-service-2026-10-12.md).

## Prepared products and aperture policy

- App: `dist/Open LM-EA9.app`, version 0.12.0/build 15.
- CLI: `dist/ea9ctl`, locally signed, using the same DeviceKit transport.
- [50mm candidate and pins](../firmware/candidates/2.9.0/README.md): 20,480 bytes,
  application `0x5000..<0xa000`, profile at `0x9f00`, loader version 2.9.0.
- [Original stock recovery bundle](../firmware/recovery/stock-1.8.0/README.md):
  retain its separate private decryption key and the same-unit original backup.

The candidate declares fixed f/1.4 in known aperture fields, including optional
EXIF only when negotiated. The known `0x1b` channel returns that declaration;
opaque `0x34` instead follows its stock operand echo. A fixed declaration is a
compatibility policy, not a sensed wide-open iris. The unknown `pl[46]` relationship
remains a controlled compatibility hypothesis.
The physical aperture is **Unknown** in the app and is operated only by the
lens ring. Camera acceptance of this fixed policy, saved exposure and physical
stop-down remain unverified; F-- with working AF is not an established mode.
See [the aperture policy](manual-aperture-policy.md).

## USB installation and strict reconnect verification

Coordinate an upload only after confirming the adapter is connected through its
USB cap and TECHART Update is closed. A camera connected by USB is a different
device. No hardware operation is needed for offline candidate preparation.

1. Close the updater and other USB clients. Physically reconnect the USB cap,
   then check `dist/ea9ctl inventory`.
2. Select **Contax Zeiss 50mm f/1.4** on Device. In
   **USB tools → Experimental autofocus**, choose **Install Experimental AF 2.9.0**.
   The same-unit stock-upload qualification is required. The operation saves a
   fresh verified two-pass backup and durable journal before START.
3. After upload, physically unplug and reconnect the cap. Keep the adapter off
   the camera and the updater closed. Confirm the new connection prerequisite
   and verify the pending update.
4. Require exact candidate/application/profile, protected bootloader/gap,
   retained upper flash, known metadata and factory-data verification. Only
   after success may the adapter be moved to the powered-off camera.

Equivalent CLI sequence from the project root:

```sh
dist/ea9ctl inventory
dist/ea9ctl apply-af contax-zeiss-50-f1-4 --idle
# Physically unplug and reconnect the USB cap.
dist/ea9ctl verify --idle
```

`--idle` acknowledges prerequisites; it cannot perform a physical reconnect.
The normal Device dropdown preserves the verified installed variant. Explicit
AF installation selects 2.9; plain `apply` selects metadata-only 2.0. Do not
rebuild a pinned image or change its local profile between upload and readback.
Do not run extra CHECK/READ/client commands while the stock loader is armed;
an ordinary read can be interpreted as the next firmware page. Lost
acknowledgement/cancellation ends the transfer without retry. Reconnect before
recovery. The journal and protected-flash rules are unchanged.

## Initial loaded-lens display, exposure and lifecycle

Start with the camera off and its USB cable disconnected. Mount the verified
adapter, C/Y-to-M converter and 50mm lens. Set the physical focus ring to
infinity and iris to f/1.4. Use still-photo A, MF and Pre-AF Off where available,
EV 0 and Auto ISO. Record actual settings; leave unavailable settings unknown.
Confirm MF before taking the initial photograph. If MF cannot be selected or
confirmed, skip that photograph and report the available settings; do not
half-press to force an autofocus attempt during this lifecycle check.

1. Switch on without shutter or AF-ON input. Record startup/errors, any mount
   movement or motor sound, whether it stops, preview brightness and the actual
   displayed f-number. The candidate should declare f/1.4; a missing/different
   display fails this check rather than establishing unknown-aperture support.
2. After any movement stops, leave it untouched for ten seconds. Record quiet
   or active idle. If the motor is normal, take one photograph of an ordinary
   indoor scene in MF. Record saved brightness, shutter speed, ISO, compensation
   and displayed f-number. A correct preview alone does not pass exposure.
3. Switch off once. Record whether display and motor stop normally and any park
   movement. Leave the camera off before reviewing these results.

An owner-reported failure is sufficient to stop or fail acceptance. A retained
image is useful for EXIF/quantitative analysis, but its absence is not a gate.
Do not infer a universal one-stop correction from the earlier stock observation.
If the lifecycle or aperture/exposure check fails, investigate before AF trials.

## Physical stop-down and exposure modes

After a normal initial lifecycle and saved A-mode exposure, use the same stable
scene and EV/ISO/metering setup. Change only the physical iris from f/1.4 to f/4;
keep the declared camera report at f/1.4 and leave the app unchanged. Take one
saved A-mode photo and record brightness and shutter/ISO. The body should adjust
for the reduced light without a fictitious electronic stop-down. Repeat the
physical f/1.4 and f/4 pair in P, keeping MF/Pre-AF Off where available.

Qualify Auto as well, recording its actual focus/exposure settings. If it does
not offer MF or forces autofocus, defer its saved-exposure pair until the first
bounded AF-S check passes; do not repeatedly hunt to obtain a photo. A saved
exposure failure stops that check and requires investigation. The unavailable
old stock photo is not a prerequisite and need not be recreated.

## One bounded AF-S attempt, then matched comparison

After a normal initial lifecycle, use Single-shot AF, Pre-AF Off and a central
focus area. Keep the physical iris at f/1.4, focus ring at infinity and the
same recorded exposure setup. Aim at a well-lit stationary contrast target
about 3–5 m away.

Half-press once, noting motion, time, indicator, hunting and whether acquisition
stops after release. Stop the attempt if it continues hunting without locking
for about two seconds; release the button and switch off if movement continues.
Take a photo only if focus locks and motion is normal; inspect center sharpness.
Record shutdown. An actuator termination event is not optical focus lock, and
USB verification does not establish sharpness.
Sony defines Single-shot AF as locking after acquisition for a stationary
subject; select and record the actual mode rather than inferring it from the
exposure dial. [A7C II Focus Mode guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html).

If this first attempt is normal, later comparisons can alternate near/distant
subjects and repeat across matched lighting, focus area, target, physical iris,
exposure settings and focus mode. Preserve every failure. Stock and custom
aperture declarations differ; record their actual displays and evaluate saved
exposure separately rather than treating that variable as matched. Subsequent
A/P/Auto and physical stop-down exposure checks, stopped-down AF, AF-C, video
and heavier lenses are separate qualification steps.

For frozen preview, incorrect aperture display, shutdown nonresponse, grinding,
repeated stop impacts or continuous abnormal drive, stop immediately. Switch off;
if the camera does not respond, remove the battery and do not retry. Remove the battery if motion continues and do not retry. Sensor/
mechanical faults inhibit further driving until reset; healthy bounded
termination allows another camera command but does not authorize repeated
failed focus attempts.

## Fallback and restoration

For motor-disabled custom firmware, use **Install Metadata Only for Prepared
Lens**, or:

```sh
dist/ea9ctl apply contax-zeiss-50-f1-4 --idle
# Physically reconnect the cap.
dist/ea9ctl verify --idle
```

For factory AF, use **Restore Stock from Backup…** with this unit's original
verified stock 1.8 backup, or:

```sh
dist/ea9ctl restore-stock /absolute/path/to/original.ea9backup --idle
# Physically reconnect the cap.
dist/ea9ctl verify --idle
```

An AF backup cannot replace the original stock source. Recovery checks the
qualified loader and matching unit, writes the saved application slot
`[0x5000,0x20000)` and metadata, and does not write bootloader code. Restoration
has passed strict readback on this unit, including the October 12
**2.8-to-stock** round trip. The restored full flash matches the stock snapshot
immediately before 2.8 installation. Interrupted-write/power-loss and bootloader
recovery remain unqualified.
The 2.9-to-stock hardware round trip has not yet run.

## Historical evidence and result record

Preserve the [2.1 upload](evidence/af-50-upload-2026-10-10.md),
[2.2 upload](evidence/af-22-upload-2026-10-11.md) and
[lifecycle report](evidence/af-22-camera-lifecycle-2026-10-11.md),
[2.3 upload](evidence/af-23-upload-2026-10-11.md) and
[loaded-lens report](evidence/af-23-camera-lifecycle-2026-10-11.md), and
[2.4 upload](evidence/af-24-upload-2026-10-11.md), and
[2.8 camera failure](evidence/af-28-camera-failure-2026-10-12.md). These observations do not
qualify 2.9. Historical pins are unchanged.

Use [the result template](evidence/af-s-camera-result-template.md). Keep original
photos and timing video private; publish only relevant hashes and extracted
metadata. Homing/origin, loaded braking and live camera timing have not been
measured on this unit. The simulated mechanical coefficients describe the
upstream author's adapter and do not establish factory parity here.

## AF 2.9 retained motion-telemetry acceptance

After separate byte verification, use the initial MF/Pre-AF Off lifecycle check
before bounded AF-S. The mount should stay physically quiet at idle. The new
observer cannot measure optical lock and a USB readback cannot observe live
E-mount motion flags. Record any unexpected focus-busy indication, shutter
blocking, continued hunt or delayed settling alongside physical movement. Noise
of four or more encoder counts can keep movement asserted; owner-unit noise is
unmeasured. A quiet motor alone does not establish correct telemetry.

Keep the first AF-S attempt bounded and preserve all failures. Release the
half-press and confirm motor shutdown. Completion/Stop now deliberately does
not clear measured coast: simultaneous completion and movement is possible.
Camera acceptance, actual settling, sharpness and hunting need the controlled
comparison; this runbook is not a record of successful hardware tests.
