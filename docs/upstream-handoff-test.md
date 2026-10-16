# Upstream AF 3.6 — held camera procedure and log retrieval

**Camera capture/shutdown failed; further 3.6 trials are held.**
The owner reports shutter-press freeze and shutdown nonresponse. A read-only
backup and log review followed. See the [failure record](evidence/upstream-36-camera-failure-2026-10-15.md).
The steps below preserve the requested historical procedure; they are not a
request to repeat it. Backup/recovery remain coordinated separately.
See the [live installation record](evidence/upstream-36-upload-2026-10-15.md).
No camera action is requested by this document alone.
The [candidate](../firmware/candidates/3.6.0/README.md) and
[offline validation](evidence/upstream-36-handoff-2026-10-15.md) do not establish
A7C II stability. The prior 3.2 transaction passed its normal guarded verification
after owner-confirmed physical reconnect. The owner then separately authorized
3.6 installation; its own physical reconnect and strict verification also passed.
Never delete/edit the pending journal or reconnect marker to bypass it.

## Separate upload and byte verification

After explicit authorization, confirm the adapter is on the USB cap, the
TECHART updater is closed and the saved original profile is the unedited
Contax Zeiss 50mm f/1.4. App 0.19/build 23 exposes **USB tools → Install Upstream AF 3.6.0**. Its CLI equivalent, for that future coordinated operation:

```sh
dist/ea9ctl apply-handoff-upstream contax-zeiss-50-f1-4 --idle
# Stop. Owner must physically unplug/reconnect and confirm the new connection.
# Keep the adapter off the camera until strict verification has passed.
dist/ea9ctl verify --idle
```

The fresh same-unit two-pass backup, durable journal and protected data checks
remain mandatory. START arms the connection: no CHECK/READ/control/end marker or
retry is sent afterward on that connection. An acknowledgement is not byte
verification. Require the complete 20,480-byte pristine image, including all
blank log pages, and existing protected metadata/flash/auxiliary checks. The
six established loader scratch bytes remain the sole metadata exception.
Record an independent offline comparison of the verification backup before
camera use. A decoder prefix match cannot substitute for this gate.

## One initial loaded-lens cycle

After the strict gate succeeds, coordinate one cycle before AF-S. With the
A7C II off and camera USB disconnected, mount the LM-EA9, C/Y-to-M converter and
50mm lens. Set the physical focus ring to infinity and iris to f/1.4. Select
still-photo A, EV0, Auto ISO, **Manual Focus separately in Focus → AF/MF → Focus
Mode**, and Pre-AF Off where available. Record actual settings; unknown settings
stay unknown. The A exposure dial alone does not select MF.

1. Switch on without shutter/AF-ON. Note preview updating/brightness, aperture
   display (nominal f/1.4), motor movement/sound and whether it stops.
2. If responsive and quiet, wait ten seconds after movement stops. If the preview
   freezes or aperture stays `--`, skip photo/AF and switch off once.
3. Only if preview, aperture and motion are normal and MF is confirmed, take one
   photograph. Record whether it saves and its exposure; preserve its local path
   for optional EXIF inspection. Switch off once and leave it off.

For a freeze, shutdown nonresponse, grinding, repeated stop impacts or abnormal
continuous drive for about two seconds, stop: switch off; remove the battery if
unresponsive or motion continues; do not retry or restart for missing details.
Report the exact trigger (startup/half/full press), saved-photo status and
shutdown behavior. No further camera cycle or AF-S is needed before log review.

This candidate intentionally starts no new parking drive on shutdown. Motor
silence is not proof of AF failure or physical infinity. Physical iris remains
manual and Unknown to the adapter; the nominal f-number cannot track ring changes.
Do not introduce exposure offsets based only on a mismatched f-number report.

## Read-only logs and next AF-S decision

With the camera off/unpowered and motor stopped, return to the USB cap and
physically reconnect, updater closed. Confirm that state before a new read-only
native backup. Use new private paths:

```sh
dist/ea9ctl backup /new/after-36.ea9backup --idle
python3 scripts/decode-startup-diagnostics.py /new/after-36.ea9backup --output /new/after-36.json
```

Trace v2 persists only on terminal shutdown after UART disable, or terminal
fail-stop. The ten-second idle does **not** flush 3.6. Battery removal, full/torn
storage or an unentered terminal path can leave blank/incomplete logs. First 24
and latest 24 RAM retention is bounded; a summary reports planned events, while
the decoder reports how many survived. A shutdown marker proves reaching that
software point, not electrical power removal or a successful next boot.

Decoder identity checks require the exact version, complete published image and manifest
pins, immutable prefix, and per-page structure/CRC; a native manifest also needs
two flash/auxiliary reads and the full flash hash. It explicitly does not verify
installation. Page `state: valid` means structure/CRC only; `recordTrust` and cohort checks separately identify inconsistent, partial or unassociated evidence. CRC is not authentication. Camera-written diagnostic pages mean ordinary `inspect` no longer
recognizes a pristine image; use `backup` plus the decoder after camera use.
Compare all outside-log flash and auxiliary data separately. Do not erase/reset
logs; raw unit dumps and actual camera exchanges stay private.

Only after a successful preview/MF-capture/idle/shutdown cycle and log review,
plan a separate bounded AF-S comparison with actual AF-S and Pre-AF Off settings,
a bright stationary target, infinity focus-ring position and physical f/1.4.
Record lock/release, hunting, motion and saved-photo sharpness. Neither a green
indicator nor host tests qualify optical accuracy. AF-C/video, zoom changes,
other lenses and factory parity remain later acceptance work.

A separately prepared [3.7 tracing candidate](../firmware/candidates/3.7.0/README.md)
now has its own [future installation/test procedure](upstream-targeted-trace-test.md).
No 3.7 flash occurred during preparation; this 3.6 failure hold remains intact.
