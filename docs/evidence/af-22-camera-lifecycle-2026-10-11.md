# AF 2.2 / A7C II unloaded lifecycle test — 2026-10-11

Status: **procedure issued; awaiting the owner's first-cycle observations**.
No camera outcome is assumed. This is a bare-adapter startup, idle and shutdown
test while the C/Y-to-M converter is unavailable. The planned first cycle uses
no optical lens or shutter/focus-button command; focus lock and sharpness are
not tested.

The owner explicitly requested testing AF 2.2 startup, motor movement and
shutdown on the A7C II. The installed candidate is the USB-byte-verified
Contax Zeiss 50mm f/1.4 profile, loader version **2.2.0**, image SHA-256
`c963e7970f7b69aaa1115afb6a1aee95644f5a243352299689452d7c1f0c6d98`.
See [the completed installation evidence](af-22-upload-2026-10-11.md).
The local journal was checked offline before issuing these instructions; no
additional USB report, upload, rebuild or stock restoration was performed.

## First cycle

1. Use the bare LM-EA9, without a lens or the awaited C/Y-to-M converter. Keep
   fingers and objects clear of its moving mount; do not move it by hand.
2. Select still-photo mode and P or A exposure mode. Select Manual Focus and
   Pre-AF Off before mounting if those menus are available. Sony places these
   under MENU → Focus → AF/MF → Focus Mode / Pre-AF. Pre-AF is available only
   when an E-mount lens is mounted, so an unavailable menu is recorded rather
   than treated as a failed test prerequisite. Do not press the shutter or AF-ON.
3. With the camera switched off and its USB cable disconnected, unplug the
   adapter from its USB cap, remove the update cap, and mount the empty adapter
   on the camera. Record battery level and camera firmware if readily available;
   unavailable values remain unknown rather than blocking the observation.
4. Switch on once. Note normal startup or any error; visible movement and/or
   motor sound; direction relative to the camera (outward/extension versus
   inward/retraction); approximate duration; and whether it stops. Leave it
   idle for about ten seconds without focus-button input. Record any later
   movement or sound, the actual focus-mode/Pre-AF settings, and displayed
   aperture if available. Set MF/Pre-AF Off after startup if they could not be
   selected beforehand, and record that ordering.
5. Switch off once. Record park movement/sound, whether it stops, and whether
   the display and camera shut down normally. If the mechanism is already at
   its reference position, no visible shutdown park movement may occur.

Abort this cycle for grinding, repeated hard-stop pushing or continuous drive
lasting about two seconds. Switch off; if motion continues, remove the battery.
Do not perform repeated retries or a second cycle after an abnormal result.
Describe the fault before a separately assessed recovery/test step.

The two-second operator cutoff is a conservative test rule, not a measured
hardware deadline. The implemented startup reference policy has a nominal
300 ms drive cap and 500 ms settle cap. It runs after the E-mount handshake even
when MF is selected; this cycle intentionally observes that startup path.
Shutdown can skip a move when already parked, not homed or faulted. These are
software expectations from the [reconciliation design](../af-reconciliation.md),
not confirmed mechanical direction, reference accuracy or wall-clock timing.

If the initial focus settings could not be established before power-on, startup
motion may also reflect camera-requested focusing. Record that ambiguity; do not
label observed movement as proof that reference acquisition succeeded. Small or
invisible motion at an already retracted stop is likewise not a motor pass/fail
by itself. An empty mount cannot establish AF-S focus acquisition or lens loading.

Sony sources checked for this procedure:
[Focus Mode](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html),
[Pre-AF](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405_pre_af.html).

## Observation record

| Observation | Owner result |
| --- | --- |
| Bare adapter / lens / converter actually mounted | Awaiting report |
| Camera firmware / battery | Unverified |
| Initial still-photo exposure mode / focus mode / Pre-AF | Unverified |
| Settings changed after startup | Unverified |
| Startup normal / error text | Awaiting report |
| Motor sound / visible motion / direction / approximate duration | Awaiting report |
| Movement stopped / ten-second idle behavior | Awaiting report |
| Displayed aperture / other metadata if visible | Unverified |
| Shutdown park movement / duration / normal power-off | Awaiting report |
| Grinding / sustained drive / battery removal / other fault | Awaiting report |
| Video / timing evidence supplied | None supplied |

Actual responses will be retained verbatim and separated from interpretation.
Owner-estimated durations are not measured latency. No E-mount trace, electrical
measurement, encoder reference or travel calibration is available in this test.
The [machine-readable record](af-22-camera-lifecycle-2026-10-11.json) retains
unknown values; the [loaded AF-S runbook](../af-s-test.md) follows once the converter
arrives and the unloaded lifecycle observations have been assessed.
