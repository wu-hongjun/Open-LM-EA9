# AF 2.3 / A7C II bare-adapter test plan and result record

October 11, 2026, America/New_York. **Planned; not yet started.** The adapter must
first complete [2.3 upload and physical-reconnect byte verification](af-23-upload-2026-10-11.md).
Earlier 2.1/2.2 observations are separate historical records and do not qualify
this image.

This test uses an empty LM-EA9, with no optical lens or C/Y-to-M converter.
It checks camera startup, visible/sounded motor response, idle and shutdown.
It cannot establish optical autofocus, lens-load behavior, encoder zero or
mechanical travel calibration. No persistent event trace is enabled.

## Stage A — one lifecycle cycle, no focus-button input

1. Use still-photo **P or A** exposure mode. Select **MF** and **Pre-AF Off** if
   available before mounting. Record unavailable settings or changes made after
   startup rather than guessing the initial mode. Sony's menu paths are
   MENU → Focus → AF/MF → Focus Mode and Pre-AF. Its guide notes Pre-AF requires
   a mounted E-mount lens; availability with this responder must be observed.
2. With the camera off and its USB cable disconnected, unplug the adapter from
   the cap, remove the update cap and mount the empty adapter on the A7C II.
   Keep fingers/objects clear of the moving mount and do not move it by hand.
3. Switch on once, without touching shutter/AF-ON. Record normal startup or
   error text; mount movement or motor sound; extension/retraction relative to
   the camera; approximate duration and whether motion stops. Record displayed
   aperture and the actual focus-mode/Pre-AF settings if available.
4. After any startup movement stops, leave it untouched for approximately
   **ten seconds**. This is an observation period, not a firmware idle timer.
   Record whether it remains quiet or starts moving again.
5. Switch off once. Record any park movement, stopping, continued sound and
   whether the display actually turns off. Report these observations before
   progressing to Stage B. Leave the camera off while awaiting assessment.

The replacement intends bounded reference acquisition after a completed
fault-free handshake; a fault, shutdown or camera Stop can suppress/cancel it.
No visible movement at startup is inconclusive without internal telemetry.
It does not prove either successful homing or a failed motor.

## Stage B — one brief focus-button request, only after normal Stage A

Detailed instructions will be issued after Stage A is assessed. Planned scope:
still-photo **AF-S**, Pre-AF Off, one approximately half-second half-press, then
release and observe stopping, followed by power-off. Do not take a photo or
repeat the request to force movement. The camera may send no useful movement
command without an optical image. Lack of movement or lack of focus lock is
inconclusive; movement demonstrates only some command/motor-path activity.
Releasing the button is not assumed to guarantee a particular E-mount Stop
message; its resulting behavior must be recorded.

## Stop conditions

Stop immediately for grinding, repeated hard-stop pushing, abnormal movement or
continuous drive for roughly two seconds. Switch the camera off; if movement
continues, remove its battery. Do not retry or return it to a powered USB cap
while the mechanism is still driving. Describe the result before the recovery
step is assessed. This operator cutoff is a conservative observation rule,
not a measured firmware deadline or travel calibration.

## Result record

| Observation | Result |
|---|---|
| Upload / physical-reconnect byte verification | Upload acknowledged; byte verification pending |
| Empty adapter, no converter, camera USB disconnected | Unconfirmed |
| Initial still-photo exposure mode / MF / Pre-AF | Unconfirmed |
| Camera startup / errors | Unconfirmed |
| Startup movement / sound / direction / approximate duration | Unconfirmed |
| Motor stopping / ten-second idle | Unconfirmed |
| Displayed aperture | Unconfirmed |
| Shutdown motor / park / display off | Unconfirmed |
| Stage B eligibility to proceed / actual settings | Not assessed |
| Half-press motor response / release / shutdown | Not tested |
| Grinding, continued motion, battery removal or other fault | Unconfirmed |

Actual observations and owner statements will be appended separately from
interpretation. No optical lens, focus accuracy, measured timing or reference
calibration is qualified by this procedure.

Sony sources checked October 11, 2026:
[A7C II Focus Mode](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html)
and [Pre-AF](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405_pre_af.html).
