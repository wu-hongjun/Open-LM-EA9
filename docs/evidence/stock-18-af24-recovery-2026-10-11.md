# Stock 1.8 recovery after the AF 2.4 camera failure

October 11, 2026. Original same-unit stock recovery upload completed normally;
the owner physically reconnected the USB cap. **Normal native strict verification
and the independent readback audit passed.** Stock 1.8.0 is restored; the new
owner reports selectable aperture in P, AUTO overexposure and a later
**failed exposure check at physical f/1.4 / displayed f/2**, estimated one stop
over. Shutter/ISO, exposure mode/compensation, original photo analysis and
lifecycle remain unverified. AF-S qualification remains pending. The
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

## Owner stock observation and exposure-procedure correction

After the verified recovery, the owner replied:

> slightly better, on AUTO mode, it still somehow overrides the aperture and makes super blown out photos, on P mode I can select the aperture but I can only open to F2.0

This establishes an owner-reported stock aperture display/range and AUTO
overexposure, not inspected image clipping or measured AF performance. Actual
physical iris, requested AUTO aperture, shutter/ISO, compensation, focus mode,
Pre-AF, startup, ten-second idle and shutdown remain unverified. “Slightly better”
is not converted into an acquisition-time, focus-lock or sharpness result.

The [official Techart manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf)
says to return the camera to f/2 and set the working iris on the lens. This is
a virtual camera operating value, not a physical f/2 restriction. The recovered
stock boot routine `0x8a8c` also declares descriptor `0x18`, converted by `0x66b8`
to AV `0x1200`, f/2. The aperture-coded menu remains at `0x56cc` in the
[instruction-validated factory model](../../research/stock-1.8/stock_model.c).

The initial P recommendation was incomplete for this stock exposure comparison.
P/Auto can select another camera aperture while the passive iris stays unchanged;
compensation for that unperformed stop-down is a plausible overexposure cause.
It is not proven for these photos because the selected value and image/settings
are unavailable. F/2 in the camera does not mean f/2 on the lens or imply that
the f/1.4 lens is incompatible. The missing aperture in failed AF 2.4 remains a
separate unresolved communication symptom.

The next check supersedes P for the stock exposure baseline: ordinary indoor
light, still-photo **A**, body **f/2**, physical lens **f/1.4**, exposure
compensation **0**, Auto ISO, MF and Pre-AF Off if available. Take one photo only
if motor behavior is normal, then switch off and record saved-photo brightness,
shutter/ISO/aperture/ring, display/motor shutdown and an available local original
photo path. [Sony's A-mode explanation](https://www.sony.com/electronics/support/e-mount-body-ilce-1-series/ilce-1/articles/00032637)
describes holding the selected aperture while the body chooses shutter speed.
No corrected saved exposure or normal shutdown is assumed before a specific
owner observation or inspected original supports it.

The owner subsequently replied:

> preview looks correct, but when I switch to a slower f stop such as f4.5 the resulted photo is blown out

The preview is reported correct; a saved photo at the reported f/4.5 change is
reported overexposed. At that point the changed control was unconfirmed; the
owner later clarified “Camera aperture only.” The physical ring was not changed
for this adjustment. The prescribed A/body-f2 setup is not
assumed to be the actual setup, and a correctly exposed saved photo at body f2
has not been reported. Shutter, ISO, compensation, ring, EXIF and shutdown remain
unverified. The clarification establishes a body-only change, consistent with
compensation
for an unperformed electronic stop-down. No original photo or exposure settings
have been inspected, so the actual camera exposure adjustment is not measured.

The confirmed camera-only f/4.5 change, with the iris unchanged, is consistent
with exposure compensation for an unperformed stop-down.
For scale, the ideal aperture ratio is `(4.5 / 2)^2 = 5.0625`, about 2.34 stops;
this is a conditional calculation, not a measured camera adjustment or clipped
image analysis. Keep the stock body at f/2 and make physical stop-down changes
on the lens. A physical-ring-only adjustment was not reported for this photo.
Correct preview brightness
alone does not establish saved exposure. The next useful observations remain a
saved photo with the body held at f/2 and display/motor shutdown; none is assumed
from this control clarification. No further firmware transfer or USB report was
performed.

The owner then answered the body-f2 saved-exposure question:

> no, if my lens is at f1.4 but camera think it is at F2, it is one stop over exposed

Record this as an owner-reported failed stock exposure check at physical f/1.4
and camera f/2, with approximately one stop excess. That magnitude is an owner
estimate, not inspected image clipping or measured calibration. The causal
explanation in the reply is retained as the owner's interpretation. A camera
f/2 operating setting has not resolved exposure on this setup; the earlier
body-only f/4.5 change does not explain all reported overexposure.

The ratio `(2 / 1.4)^2` is about 2.04, or 1.03 stops, but that arithmetic alone
does not prove a metering error. Sony's
[Metering Mode guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0406_metering_mode.html)
describes measuring scene light to determine exposure. The physical aperture
already affects the light reaching the camera; lens signaling can also affect
its exposure calculation. Sony's
[Live View Display guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0414_live_view_disp_set.html)
also documents a preview setting that does not reflect shot brightness. The
owner's live-view setting, actual shutter/ISO, mode, compensation, metering and
flash settings remain unknown. No one-stop software correction is justified
by this observation alone.

Static review confirms the factory boot current AV `0x1200` (f/2) and descriptor
`0x18`, and the runtime `0x1b` response's dependence on camera-request state.
The custom range setter already keeps the wide and maximum descriptors equal;
it does not apply an additional one-stop-wider descriptor. This review is not
a camera wire trace or a new proven firmware bug. No new build/flash was made.

The next evidence is the existing original stock photo and its shutter/ISO,
mode, compensation and metering fields, with physical iris supplied by the
owner. The previously referenced photo directory was not mounted on the Mac;
no current photo/EXIF could be inspected. A path/settings clarification was
requested without asking for another photo. Display/motor shutdown and AF-S
remain unqualified. Avoid another gain/aperture correction or candidate upload
until that evidence distinguishes camera settings, metering and lens signaling.

This follow-up sent no hardware reports and uploaded no firmware. Stock remains
the last verified image; AF 2.4 remains suspended. A later custom version must
qualify fixed aperture reporting against metering and AF under A, P and Auto,
including manual stop-down; it cannot rely on the prototype's app label to
establish camera behavior.

## Initial requested stock cycle, retained as history

Start with a single lifecycle/display observation, after verification:

1. With the camera off and its USB cable disconnected, move the adapter from
   the cap to the A7C II with the C/Y-to-M converter and 50mm f/1.4. Support the
   lens and set its focus ring to infinity and physical iris to f/1.4.
2. The original request specified still-photo P, MF and Pre-AF Off if available;
   P is superseded by A/body f2 for the next stock exposure check. Switch on without
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
