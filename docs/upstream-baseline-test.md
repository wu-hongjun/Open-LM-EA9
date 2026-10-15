# Direct upstream 3.1 comparison on A7C II

The [fixed 50mm f/1.4 candidate](../firmware/candidates/3.1.0/README.md) is
uploaded and strictly byte-verified after physical reconnect. **Camera acceptance
failed; further 3.1 trials are held.** The owner reports aperture `--`, no shutter
release and no motor movement; shutdown worked. Actual focus mode and other
settings are unverified. See [the failure investigation](evidence/upstream-31-camera-failure-2026-10-14.md).
The procedure below is retained for future reviewed candidates, not a retry
request for this image. The image preserves the upstream implementation;
[the provenance](../firmware/upstream-baseline/README.md) lists all differences.
The previous verified hardware image was AF 3.0, whose full-press capture and
shutdown failed; further AF 3.0 trials are held. The owner returned the adapter
to the USB cap and the authorized 3.1 upload completed with a fresh two-pass
backup. Fresh two-pass readback and a separate offline audit matched the full
fixed image/metadata and unchanged protected flash/factory data. No further
camera trial or stock restoration is requested.
See [the installation record](evidence/upstream-31-upload-2026-10-14.md).

## Upload and exact reconnect verification

With the camera off/unpowered, move the adapter to its USB update cap, connect
the Mac and close TECHART Update. Confirm that physical state before reports.
App 0.14/build 17 offered **USB tools → Install Upstream Baseline 3.1.0** with
the original Contax Zeiss 50mm f/1.4 profile selected. Other/edited profiles are
unavailable because this image has fixed compiled metadata. App 0.14.1/build 18
disables this installation action following the failed camera result.

The explicit native CLI path is:

```sh
dist/ea9ctl inventory
dist/ea9ctl apply-upstream contax-zeiss-50-f1-4 --idle
# Physically unplug and reconnect the cap; keep it off the camera.
dist/ea9ctl verify --idle
```

The established updater/exclusive-access/qualified-loader/same-unit guards are
retained. Upload saves a fresh two-pass flash/auxiliary backup and durable journal
before START. It sends one START and 320 pages; no post-START CHECK/READ/retry is
permitted on the armed connection. A lost acknowledgement ends the attempt.
Reconnect physically before verification/recovery; do not delete markers.

Verification requires the **entire fixed 20,480-byte image**, known metadata,
protected boot code/gap/upper flash and factory auxiliary data. The sole metadata
exclusion remains `[0x403a,0x4040)` loader scratch. Follow with a separate offline
audit. Do not infer camera compatibility from USB equality. Keep the same-unit
stock recovery bundle and private key; no restoration is automatic.

## First camera cycle, after strict verification

Use the A7C II with the C/Y-to-M converter and 50mm lens, USB cable disconnected.
With the camera off, mount the verified adapter/lens. Set physical focus infinity
and iris f/1.4. Use still-photo A mode, MF, Pre-AF Off, EV 0 and Auto ISO where
available; record actual settings. MF is selected separately from the exposure
dial: **MENU → Focus → AF/MF → Focus Mode → Manual Focus**;
**Pre-AF → Off** is in that same AF/MF menu.
[Sony Focus Mode](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html),
[Sony Pre-AF](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405_pre_af.html).

1. Switch on without shutter/AF-ON input. Check updating preview, brightness,
   displayed f-number (expected f/1.4), movement/sound and whether it stops.
2. After any movement stops, wait ten seconds untouched and record quiet/active
   idle. If preview/motor are normal and MF is confirmed, take **one** photo;
   otherwise skip it. Do not force AF to obtain this photograph.
3. Switch off once and leave it off. Report startup, actual settings, saved-photo
   brightness if taken, motor stop and whether the display shuts down.

Freeze, shutdown nonresponse, grinding, repeated stop impacts or abnormal drive
for about two seconds ends the check: switch off, remove the battery if
unresponsive or motion continues, and do not retry. No saved image/settings
are required to accept a failure report.

Only after this cycle is normal request a single bounded AF-S attempt, Pre-AF
Off, central target, good light, roughly 3–5 m, physical iris f/1.4 and focus ring
infinity. Stop hunting without lock after about two seconds; release and switch
off if movement continues. If lock/motor behavior are normal, take one photo,
check sharpness and record shutdown. Motor arrival is not optical lock.

If upstream succeeds, use it as the base and add metadata management/AF changes
one at a time. If it fails too, preserve that result as evidence of an upstream/
body/configuration boundary rather than automatically attributing it to our
factory-derived controller. Exposure, optical rows, real IRQ/sensor latency and
full shutter exchanges remain separate qualification work.
