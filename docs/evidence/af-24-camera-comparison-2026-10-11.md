# A7C II / Contax Zeiss 50mm f/1.4: AF 2.4 comparison

October 11, 2026. **AF 2.4 passed USB byte verification but failed the owner's
focus-acquisition attempt. Further 2.4 camera tests are suspended.** The owner
reports no movement without shutter input, movement on half-press without focus
acquisition/photo release, no motor movement on shutdown, a very dark view and
no displayed f-number after switching to P or A. They returned the adapter to
the Mac/USB cap. Exposure mode P/A is reported; actual focus mode, Pre-AF, iris,
shutter/ISO, target, movement duration, release response, display shutdown and
the exact aperture-display appearance remain unverified. No optical image was
obtained. We do not interpret missing aperture display as a proven F-- encoding
or successful unknown-aperture AF.

Owner replies retained verbatim:

> if I don't press shuttor, nothing moves, and IF I HALF PRESS SHUTTER, motor moves but it doesn't every get focus and camera cannot take photo because it cannot reach focus

> motor doesn't move when shut down. somehow the entire scene is super dark. I installed it back to the mount

> yes, it is back to connected to the mac. Note when I switched to P or A mode there is no shown F stop

The [failure investigation](af-24-camera-failure-2026-10-11.md) distinguishes
confirmed host counterexamples from the untraced hardware cause. Original
same-unit stock recovery passed normal strict verification after physical
reconnect and an independent audit. The new stock display/lifecycle and AF-S
comparison remain pending. See [the recovery record](stock-18-af24-recovery-2026-10-11.md).
The procedures below are
retained as the original test plan, **not instructions to retry AF 2.4 now**.
The [USB installation record](af-24-upload-2026-10-11.md) still correctly records
strict image equality; it does not qualify camera behavior.

The earlier stock-versus-2.3 result was qualitative and lacked matched AF mode,
Pre-AF, lighting/target and sharpness records. The dark view and missing f-number
make the next controlled stock baseline especially important.

## One loaded-lens lifecycle cycle first

1. Keep the camera off and disconnect its USB cable. Remove the adapter from the
   USB cap; mount the C/Y-to-M converter and Contax Zeiss 50mm f/1.4 securely.
   Set the lens focus ring to infinity and iris to f/1.4; support the lens.
2. Use still-photo **P**, initially **Manual Focus**, with **Pre-AF Off** if
   available. Switch on without pressing shutter or AF-ON. Record errors, any
   mount movement/motor sound, direction and approximate duration, and whether
   it stops. The candidate attempts bounded reference acquisition after handshake;
   absence/presence of sound alone does not establish the reference.
3. After any startup movement stops, wait a full **10 seconds untouched**.
   Record quiet/active idle, focal length and aperture display. Switch off once;
   record park motion, display shutdown and whether the motor ends. Leave it off
   until this first lifecycle result is reviewed.

Stop immediately for grinding, repeated pushing against a stop, continuous
drive for about two seconds, a camera error/hang, or motion that continues after
power-off. Switch off; remove the battery if motion continues. Do not retry that
session or remount a powered adapter. Reconnect on the USB cap for reviewed
recovery instead. A stable sensor value cannot be proven truthful by software.

## Controlled AF-S trials after a normal cycle

Select **MENU → Focus → AF/MF → Focus Mode → Single-shot AF**. Sony describes
AF-S as acquiring and then locking focus for a stationary subject.
[A7C II Focus Mode](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html).
Set **MENU → Focus → AF/MF → Pre-AF → Off** so idle pre-focusing does not
confound deliberate acquisition. [A7C II Pre-AF](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405_pre_af.html).
Use a central Spot area on a well-lit static textured target, initially about
3–5 m away, with no foreground/background target ambiguity. Record the actual
settings, not just the intended settings. Use either half-press with AF w/Shutter
enabled or AF-ON; record the trigger and use it consistently for both firmwares.

For the first attempt, press once; release after lock or about two seconds.
If motion is normal, record acquisition time, visible reversals/hunting, the
focus indicator and whether movement ends after release. Take a photo after a
reported lock and retain the original for full-size sharpness/EXIF inspection.
If the adapter becomes unresponsive after a failed attempt, stop and report it:
this candidate has sticky stall/timeout/feedback faults, so repeated presses do
not reliably distinguish loss of focus from an inhibited controller.

If the first attempt and shutdown are normal, repeat three near/far pairs
(approximately 1–2 m and a distant target), fully releasing between attempts.
Keep the mechanical focus ring, illumination, targets, camera position, focus
area and iris fixed across versions. Include failures. Finish with clean shutdown.
Then repeat the same controlled set on stock after a separately coordinated
restore/USB verification, or use previously recorded stock trials only if all
these conditions are known. No matched-stock result is assumed from memory.

After successful f/1.4 qualification, an optional set at physical **f/4** can
test manual stop-down. The iris changes immediately on the lens; the camera
still reports its saved fixed f/1.4 unless that metadata is changed separately.
The app's actual-aperture display stays Unknown. Record physical and reported
f-numbers separately, as well as exposure and EXIF; a numeric report is not iris
control or an optical measurement. Camera aperture-dial behavior remains a
separate observation to collect, not a promise that Sony hides every control.

## Observation sheet

| Observation | AF 2.4 | Stock 1.8 matched control |
| --- | --- | --- |
| USB exact bytes verified before camera | Passed, two full matching reads and independent audit | Latest recovery passed normal strict verification and independent audit before camera use |
| Still/Movie switch; exposure mode | P/A reported; Still/Movie switch unknown | Unreported |
| Actual AF mode; Pre-AF; focus area; trigger | Unreported | Unreported |
| Lens ring focus; physical iris; reported f-number | Rings unreported; no shown f-number in P/A; dark view | Unreported |
| Startup/errors and movement | No movement without shutter input reported; errors unreported | Unreported for this controlled set |
| Full 10-second quiet idle | Unreported | Unreported |
| First AF acquisition time/reversals/lock | Half-press moves motor; owner reports never achieving focus or releasing photo; timing/mode unknown | Unreported |
| Three near/far pairs; all failures | Unreported | Unreported |
| Original photo path; inspected sharpness/EXIF | Unreported | Unreported |
| Shutdown/display/motor | No shutdown movement reported; display shutdown unverified | Unreported for this controlled set |
| Manual f/4 trials after stable f/1.4 | Not attempted | Not attempted |

Every owner reply should be retained verbatim with the test conditions. A lock
indicator without an inspected image does not establish optical sharpness, and
the software's move-completion event does not establish focus lock. The
[full runbook](../af-s-test.md) retains upload/restoration details and the limits
of USB-only development.
