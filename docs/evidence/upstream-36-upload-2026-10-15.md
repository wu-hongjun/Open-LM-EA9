# Upstream C 3.6 installation and camera cycle — October 15, 2026

**Upload complete; owner physical reconnect and strict byte verification pending.**
The owner explicitly requested resolving the pending 3.2 verification, then
installing 3.6 for the Contax Zeiss 50mm f/1.4 with the adapter on its USB cap
and the TECHART updater closed. The owner confirmed the first physical
unplug/reconnect. [3.2 strict verification](upstream-32-upload-2026-10-15.md)
and its separate offline audit passed before any 3.6 upload. No 3.2 camera cycle
occurred. Keep 3.6 off the camera until its separate verification passes.

## Image and upload

Release source: `89e6d0dd2142e57c930540faa68632794769622e`, already on origin/main.
The reviewed signed CLI is app **0.19/build 23**, SHA-256
`781231a3e6b6ef29e442cef982f92e4eb158d805ac315d226bf112eeb332d394`. No competing app, updater or CLI process was present at preflight.
Native offline `prepare-handoff-upstream` with the canonical original 50mm
profile matched the [frozen candidate](../../firmware/candidates/3.6.0/README.md):
20,480 bytes, SHA-256 `d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`,
including all 1,024 FF diagnostic bytes. It has no runtime profile row.
Nominal aperture is f/1.4; the actual manually operated iris remains Unknown.
[Offline release evidence](upstream-36-handoff-2026-10-15.md) records tests and
physical limits; those results do not qualify A7C II camera behavior.

Command: `dist/ea9ctl apply-handoff-upstream contax-zeiss-50-f1-4 --idle`,
using canonical native state. The native transaction retained exclusive access,
updater detection, same-unit qualification, fresh backup, durable journal,
exact acknowledgements and physical-reconnect guards. It exited 0 at
**2026-10-15T12:05:50.182349+00:00 UTC**
(**2026-10-15T08:05:50.182349-04:00 America/New_York**).
Transaction: `9B90BC32-4FA9-44BA-B9D3-DE65EEF0CBB1`. One START and 320 64-byte pages completed;
counts follow successful native-engine evidence, not an independent wire capture.
No CHECK/READ, end marker, retry or extra padding was sent after START on the
armed connection. Its reconnect marker remains retained. No journal or guard
was manually changed.

## Fresh backup and independent offline audit

The pre-upload backup reports 3.2.0, 131,072 flash bytes, two matching full-flash
and auxiliary passes, and 4,359 CHECK/READ exchanges. Its entire flash and
protected auxiliary data exactly match the just-completed strict 3.2 readback.
Flash SHA-256: `e163b1483e02f657a86cd1444f77a01fc77982ee11992b8edb2f3853827be29c`.
The original qualified boot-code hash is unchanged. Separate offline checks
validate all backup file sizes/digests, unit binding, planned/pending/committed
image equality, exact metadata length/version, upload completion and retained
reconnect marker. Raw dumps, unit identifiers, exchanges and canonical state
remain private. Original recovery and earlier released images/pins are preserved.

## Pending reconnect verification

The owner must physically unplug/reconnect through the USB cap, keep the updater
closed and adapter off the camera, and confirm that state before
`dist/ea9ctl verify --idle`. Require a new connection and the same unit, a fresh
matching two-pass backup, exact `[0x5000,0xa000)` including pristine log bytes,
exact known metadata, unchanged boot code, protected gap, retained upper flash,
user row, calibration and device-ID window. The sole metadata exclusion remains
six loader scratch bytes `[0x403a,0x4040)`. Repeat those checks in an independent
offline audit; a diagnostic prefix match is insufficient.

## Pending one-cycle camera check and logs

After strict verification, use the [coordinated 3.6 procedure](../upstream-handoff-test.md):
one loaded-lens cycle, separately selected MF, still-photo A, Pre-AF Off where
available, EV0, Auto ISO, physical focus infinity and iris f/1.4. Record actual
settings, preview, aperture, motor/quiet idle and shutdown. Take at most one
photo only if preview/aperture/motion are normal and MF is confirmed. Stop for
freeze or abnormal drive; remove the battery if unresponsive or motion continues.
No restart or AF-S precedes result/log review. These settings and outcomes are
currently unverified; no camera cycle has been requested or reported for 3.6.

After the owner confirms power-off, return to the USB cap and physical reconnect,
save a fresh native read-only two-pass backup and run the offline decoder.
Compare flash outside `[0x9c00,0xa000)` and protected auxiliary data with this
installation's verified pre-camera readback. Terminal shutdown/fail-stop flushes
v2 records; a ten-second idle does not. Battery loss can leave incomplete/blank
logs. Preserve actual camera frames privately and publish sanitized observations.
