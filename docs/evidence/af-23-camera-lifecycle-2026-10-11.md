# AF 2.3 / A7C II loaded-lens observation and lifecycle test plan

October 11, 2026, America/New_York. **AF 2.3 was USB-byte-verified. The owner then
tested it with the Contax Zeiss 50mm f/1.4 and C/Y-to-M converter and reported
eventual focus with substantial hunting.** The adapter completed
[2.3 upload and physical-reconnect byte verification](af-23-upload-2026-10-11.md).
Earlier 2.1/2.2 observations are separate historical records and do not qualify
this image.

The requested procedure below used an empty LM-EA9, with no optical lens or
C/Y-to-M converter. The owner instead confirmed a loaded-lens test; execution
of the requested bare-adapter stages is unconfirmed. The planned lifecycle
procedure checks camera startup, visible/sounded motor response, idle and shutdown.
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
| Upload / physical-reconnect byte verification | Passed: two complete flash/auxiliary passes; independent offline audit passed |
| Actual optical configuration | Owner confirmed Contax Zeiss 50mm f/1.4 with C/Y-to-M converter; camera USB state unreported |
| Initial still-photo exposure mode / MF / Pre-AF | Unconfirmed |
| Camera startup / errors | Unconfirmed |
| Startup movement / sound / direction / approximate duration | Unconfirmed |
| Motor stopping / ten-second idle | Unconfirmed |
| Displayed aperture | Unconfirmed |
| Shutdown motor / park / display off | Unconfirmed |
| Stage B eligibility to proceed / actual settings | Not assessed |
| Half-press motor response / release / shutdown | Trigger, release and shutdown unreported |
| Grinding, continued motion, battery removal or other fault | Unconfirmed |
| Optical focus acquisition | Owner reports eventual focus; lock and photograph sharpness unverified |
| Hunting / focus indicator | Owner reports substantial hunting and frequent purple focus indicator; indicator meaning unestablished |
| Return to USB cap / updater closed | Owner confirmed both for stock comparison |

Owner statements:

> It sort of works, but it hunts a lot for getting focus. SHould we flash the stock 1.8.0 firmware so I can have a comparison?

> with the 50mm lens and C/Y-to-M converter, it eventually achieves focus, but I see the purple focus indicator a lot and it hunts a lot

> Back on USB cap; updater closed

The converter is now available. Focus mode, Pre-AF, focus-button trigger, target,
lighting and lens-ring settings were not supplied. Eventual acquisition is an
owner observation, not verified sharpness, green-lock evidence or calibration.
The purple indicator is not interpreted as an adapter fault or a particular
Sony focus state without more evidence. Earlier 2.2 bare-adapter shutdown
observations do not qualify 2.3 loaded shutdown. The requested
[same-unit stock 1.8 comparison](stock-18-comparison-2026-10-11.md) subsequently
produced the owner's report that stock hunts much less. Its original application
slot matches the post-camera USB readback, while strict native verification
remains flagged for changed saved-motion settings. Both camera reports are
qualitative and lack recorded matched conditions. The owner's requested unknown
aperture behavior is assessed in [manual aperture policy](../manual-aperture-policy.md).

Sony sources checked October 11, 2026:
[A7C II Focus Mode](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html)
and [Pre-AF](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405_pre_af.html).
