# A7C II / Contax Zeiss 50mm f/1.4: AF 2.4 comparison

October 11, 2026. **AF 2.4 passed native and independent USB byte verification. Camera results
are not yet recorded.** The owner was asked for the first loaded-lens lifecycle
cycle; AF-S acquisition remains the next step after a normal cycle.
Use this only after successful [USB installation and physical-reconnect byte
verification](af-24-upload-2026-10-11.md). A running/uploaded application is
not sufficient. The earlier stock-versus-2.3 result is qualitative: the owner
reported eventual 2.3 focus with more hunting and less hunting on stock, but
AF mode, Pre-AF, lighting/target and sharpness were not recorded. It is not a
matched control for 2.4. We need the following recorded settings for both versions.

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
| USB exact bytes verified before camera | Passed, two full matching reads and independent audit | Prior stock code audited; pending restore resolved by reviewed motion-record policy |
| Still/Movie switch; exposure mode | Unreported | Unreported |
| Actual AF mode; Pre-AF; focus area; trigger | Unreported | Unreported |
| Lens ring focus; physical iris; reported f-number | Unreported | Unreported |
| Startup/errors and movement | Unreported | Unreported for this controlled set |
| Full 10-second quiet idle | Unreported | Unreported |
| First AF acquisition time/reversals/lock | Unreported | Unreported |
| Three near/far pairs; all failures | Unreported | Unreported |
| Original photo path; inspected sharpness/EXIF | Unreported | Unreported |
| Shutdown/display/motor | Unreported | Unreported for this controlled set |
| Manual f/4 trials after stable f/1.4 | Not attempted | Not attempted |

Every owner reply should be retained verbatim with the test conditions. A lock
indicator without an inspected image does not establish optical sharpness, and
the software's move-completion event does not establish focus lock. The
[full runbook](../af-s-test.md) retains upload/restoration details and the limits
of USB-only development.
