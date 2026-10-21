# AF 4.0 — separate upload, one camera cycle and logs

**Offline preparation only. Nothing was flashed in this milestone.** Do not repeat
held 3.9 camera trials.4.0 is an experimental fixed Contax Zeiss 50mm f/1.4 candidate,
not an accepted camera release. [Image and pins](../firmware/candidates/4.0.0/README.md).

## Coordinated installation

With explicit owner authorization, confirm the adapter is on its USB cap, the
camera is disconnected, TECHART Update and Open LM-EA9 are closed. Use the signed
native CLI, its exact image/resource pins and the existing durable upload journal.
Resolve any pending transaction before a new upload; never edit a journal or safety
marker by hand. `--state-directory` does not isolate the canonical USB guard or lock.

Explicit commands `prepare-reference-upstream` and `apply-reference-upstream`
select 4.0 only. Historical commands retain their original images. Preparation with
a new private state directory and output returns before device inventory; applying
requires the normal verified backup and stock qualification gates. The app exposes
4.0 under USB tools → Experimental autofocus and keeps3.9 installation disabled.
No generic profile change silently upgrades firmware.

After upload, send no further reports until the owner physically unplugs/reconnects
and explicitly confirms. Strict native verification must compare the complete
20,480-byte application, including the erased diagnostic tail, and protected flash,
user row, calibration and device-ID windows against the unit's prior backup. Use
only the established metadata scratch exclusions. Independently audit saved files
before camera use. An image pin or reported version alone is not installed-byte
verification. If any check fails, stop and preserve evidence.

## One initial cycle, after verification

With A7C II OFF and its USB cable disconnected, mount the adapter, C/Y-to-M converter
and 50mm f/1.4. Set physical focus to infinity and iris to f/1.4. Select still-photo A,
EV 0 and Auto ISO; separately confirm **MF** and Pre-AF Off. A exposure mode is not MF.
If MF cannot be confirmed, skip the photo and record the focus mode as unknown.

Switch on without shutter or AF-ON input. Check live preview, brightness and aperture
(expected f/1.4), then wait 10 seconds after any movement stops. Only if these are
normal and MF is confirmed, save **one** photo. Switch off once and leave it off;
do not restart or attempt AF-S in this cycle. Record actual settings, movement,
quiet idle, preview/aperture, whether a file saved, its exposure and shutdown.
A second controlled AF-S comparison follows only after this cycle/log review.

For frozen preview, grinding, repeated stop impacts or abnormal continuous drive
for about 2 seconds, stop; switch off, remove the battery if unresponsive or motion
continues, and do not retry. Once unpowered and stopped, return to the USB cap,
physically reconnect with both apps closed, and explicitly confirm readiness for
read-only log retrieval. Leave unavailable observations unknown.

## Read-only retrieval

Perform the existing guarded two-pass backup; do not relax installation verification
to permit logs. Preserve raw dumps, identifiers, keys and real frames privately.
Audit all changes against the pristine installed readback: only the diagnostic tail
may differ. Decode using the 4.0 registry and image/manifest pins. A later logged
backup is diagnostic evidence, not pristine full-image verification.

Inspect home-phase tags, drive qualification/settle evidence, normal servo snapshots,
consumed requests, capture owners/local TX returns and shutdown breadcrumbs. Local
send return does not prove body acceptance; a missing footer does not prove a hang.
Keep the actual focus mode uncertain unless confirmed. No repeated camera attempt
is needed to fill missing observations. Record findings before another candidate.
