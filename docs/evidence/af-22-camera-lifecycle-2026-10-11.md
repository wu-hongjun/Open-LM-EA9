# AF 2.2 / A7C II unloaded lifecycle test — 2026-10-11

Status: **owner reports normal startup, quiet idle and normal motor shutdown**.
In the latest cycle the owner observed no motor movement without button input,
said the camera started normally, and reported quiet idle and normal motor
shutdown in response to the requested wait/power-off check. Display power-off,
startup motor sound, actual settings and homing remain unconfirmed. The earlier
attempt's normal motor sound and skipped wait are retained separately below;
they are not substituted for observations from this cycle.
This is a bare-adapter startup, idle and shutdown test while the C/Y-to-M converter
is unavailable. The planned configuration uses no optical lens or
shutter/focus-button command; focus lock and sharpness are not tested. The actual
configuration of the initial attempt has not been explicitly confirmed.

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

The ten seconds is an observation period for the owner to wait after startup
movement stops. It is not a delay or idle transition that the firmware should
produce. The owner has now reported quiet idle and normal motor shutdown after
the follow-up check. The actual elapsed wait was not measured. No additional
empty-adapter cycle is requested on the basis of these reports.

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
| Bare adapter / lens / converter actually mounted | Owner said they put it on; lens/converter configuration unconfirmed |
| Camera firmware / battery | Unverified |
| Initial still-photo exposure mode / focus mode / Pre-AF | Unverified |
| Settings changed after startup | Unverified |
| Startup normal / error text | Latest report: camera starts normally; no error text supplied |
| Motor sound | Earlier attempt: described as normal; latest startup sound unreported |
| Visible motion / direction / approximate duration / stopping | Latest startup: owner reports no movement without input; direction/duration unverified |
| Ten-second idle behavior | Latest follow-up: stayed quiet; elapsed duration not measured. Earlier attempt: wait skipped |
| Displayed aperture / other metadata if visible | Unverified |
| Shutdown motor behavior | Latest follow-up: motor shut down normally |
| Display power-off / shutdown park movement / duration | Unverified |
| Grinding / sustained drive / battery removal / other fault | Awaiting report |
| Video / timing evidence supplied | None supplied |

Owner responses, in order:

> I put it on, the motor sounded normal, I don't observe a 10sec idle

> I did not wait, it ic connected to the computer now, what should we do now?

> if I don't do anything and turn it on, the motor doesn't move, camera starts up normally

> it stay quiet and motor shut down normally

An OS HID descriptor inventory at **2026-10-11 08:55:26 America/New_York**
detected one matching adapter with the qualified descriptor (command exit 0).
It sent **zero HID reports** and did not read a fresh firmware version or flash
image. AF 2.2 installation verification remains the earlier, separately recorded
USB read-back. No upload or stock restoration was needed for this observation.
The later owner reports cover startup, quiet idle and motor shutdown; camera
display power-off was not explicitly reported. No USB commands or firmware
changes were performed while collecting those later camera observations.

## Interpretation and source review

Normal startup, quiet idle and normal motor shutdown are owner observations,
not proof of AF capability or correct reference acquisition. No startup movement
was observed, and no focus-button command was reported. The source still intends
to attempt bounded homing after a completed E-mount handshake in a fault-free
session, independently of a shutter/AF-ON press. Its configured home gate is
open; sensor/peripheral faults, shutdown and a camera STOP can prevent or cancel
the attempt. Small or invisible motion at an already retracted stop is also
possible. These are possible explanations, not a diagnosis of this camera cycle.
Normal camera startup alone does not establish the internal handshake or home
state. No change to motor duty, homing policy or protection was justified by the
report alone.

The reviewed `main.c`, `af_reference.c/.h`, `io_guard.c`, `diag.c` and Makefile
SHA-256 values match the [frozen AF 2.2 build manifest](af-reconcile-build-manifest-2026-10-10.json).
The candidate enables motor motion and disables diagnostic flash logging, so
there is no persistent homing/event trace to recover from this cycle. This was
an offline source review, without rebuilding or uploading. Full camera power-off,
physical reference/travel, motor response to a focus command, loaded AF-S lock
and sharpness remain unverified. Loaded focus testing follows when the converter
arrives; another bare-adapter cycle is not currently requested.

Responses are retained verbatim and separated from interpretation.
Owner-estimated durations are not measured latency. No E-mount trace, electrical
measurement, encoder reference or travel calibration is available in this test.
The [machine-readable record](af-22-camera-lifecycle-2026-10-11.json) retains
unknown values; the [loaded AF-S runbook](../af-s-test.md) follows once the converter
arrives and the unloaded lifecycle observations have been assessed.
