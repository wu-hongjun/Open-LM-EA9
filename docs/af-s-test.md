# A7C II acceptance: AF 2.5, Contax Zeiss 50mm f/1.4

The [AF 2.5 candidate](../firmware/candidates/2.5.0/README.md) and app
0.8.0/build 11 are prepared and tested offline. **2.5 has not been uploaded or
camera-qualified.** This procedure is a plan, not a record of passed checks.
The converter is now available. The last byte-verified hardware image was
original stock 1.8; its owner-reported exposure failure remains accepted.
An earlier photograph is unavailable and is not required to continue.

AF 2.4 passed USB verification but failed focus acquisition, with a dark view
and no shown f-number in P/A. Further trials of that frozen image are suspended.
See [the failure investigation](evidence/af-24-camera-failure-2026-10-11.md),
[completed stock recovery](evidence/stock-18-af24-recovery-2026-10-11.md), and
[2.5 implementation and tests](evidence/af-25-candidate-2026-10-11.md).

## Prepared products and aperture policy

- App: `dist/Open LM-EA9.app`, version 0.8.0/build 11.
- CLI: `dist/ea9ctl`, locally signed, using the same DeviceKit transport.
- [50mm candidate and pins](../firmware/candidates/2.5.0/README.md): 20,480 bytes,
  application `0x5000..<0xa000`, profile at `0x9f00`, loader version 2.5.0.
- [Original stock recovery bundle](../firmware/recovery/stock-1.8.0/README.md):
  retain its separate private decryption key and the same-unit original backup.

The candidate declares fixed f/1.4 consistently in the known range/current/
reply fields, including optional EXIF only when negotiated. It deliberately
rejects the factory request echoes that would imply an unavailable iris change.
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
   **USB tools → Experimental autofocus**, choose **Install Experimental AF 2.5.0**.
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
AF installation selects 2.5; plain `apply` selects metadata-only 2.0. Do not
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

If this first attempt is normal, later comparisons can alternate near/distant
subjects and repeat across matched lighting, focus area, target, physical iris,
exposure settings and focus mode. Preserve every failure. Stock and custom
aperture declarations differ; record their actual displays and evaluate saved
exposure separately rather than treating that variable as matched. Subsequent
A/P/Auto and physical stop-down exposure checks, stopped-down AF, AF-C, video
and heavier lenses are separate qualification steps.

For grinding, repeated stop impacts or continuous abnormal drive, switch off
immediately. Remove the battery if motion continues and do not retry. Sensor/
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
has previously passed strict readback on this unit. A **2.5-to-stock** round
trip, interrupted-write/power-loss and bootloader recovery remain unqualified.

## Historical evidence and result record

Preserve the [2.1 upload](evidence/af-50-upload-2026-10-10.md),
[2.2 upload](evidence/af-22-upload-2026-10-11.md) and
[lifecycle report](evidence/af-22-camera-lifecycle-2026-10-11.md),
[2.3 upload](evidence/af-23-upload-2026-10-11.md) and
[loaded-lens report](evidence/af-23-camera-lifecycle-2026-10-11.md), and
[2.4 upload](evidence/af-24-upload-2026-10-11.md). These observations do not
qualify 2.5. Historical pins are unchanged.

Use [the result template](evidence/af-s-camera-result-template.md). Keep original
photos and timing video private; publish only relevant hashes and extracted
metadata. Homing/origin, loaded braking and live camera timing have not been
measured on this unit. The simulated mechanical coefficients describe the
upstream author's adapter and do not establish factory parity here.
