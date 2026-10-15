# Upstream C 3.6 installation and camera cycle — October 15, 2026

**Upload and strict physical-reconnect verification passed; one camera cycle and log retrieval requested.**
The owner explicitly requested resolving the pending 3.2 verification, then
installing 3.6 for the Contax Zeiss 50mm f/1.4 with the adapter on its USB cap
and the TECHART updater closed. The owner confirmed the first physical
unplug/reconnect. [3.2 strict verification](upstream-32-upload-2026-10-15.md)
and its separate offline audit passed before any 3.6 upload. No 3.2 camera cycle
occurred. The owner then explicitly confirmed the separate physical reconnect
for 3.6. Its native verification and independent offline audit passed before
requesting the camera cycle.

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

## Completed reconnect verification

The owner explicitly confirmed physical unplug/reconnect through the USB cap,
updater closed and adapter off the camera. Native `dist/ea9ctl verify --idle`
required a new connection and the same unit before reports, completed two
matching full-flash and auxiliary passes, and exited 0 at
**2026-10-15T12:23:54.944275+00:00 UTC**
(**2026-10-15T08:23:54.944275-04:00 America/New_York**).
It reports **3.6.0**, 131,072 flash bytes and 4,359 CHECK/READ exchanges.
No writes or retries were sent during verification.

The independent offline audit revalidates all backup file sizes/digests and
compares every application byte `[0x5000,0xa000)`, including all 1,024 pristine
diagnostic bytes. Known metadata matches exactly; boot code, protected gap,
retained upper flash, user row, calibration and device-ID window are unchanged.
The six established loader scratch bytes `[0x403a,0x4040)` remain the sole
metadata exclusion. No diagnostic-prefix relaxation or manual journal/guard
change was used. Full flash SHA-256:
`7b15614f706b6a937b586d4ab3fed76306a73e7d2ed02df421d529586f93ac7f`.

The native service published canonical applied-lens and dated firmware records
for 50mm f/1.4 / 3.6.0, cleared the successful read connection's marker and
retained the original armed upload connection's marker. Raw state, unit data,
backups and exchange logs remain private. USB equality proves installed bytes;
it does not qualify camera capture, exposure, autofocus or shutdown.

## Pending one-cycle camera check and logs

After strict verification, the owner was asked to use the [coordinated 3.6 procedure](../upstream-handoff-test.md):
one loaded-lens cycle, separately selected MF, still-photo A, Pre-AF Off where
available, EV0, Auto ISO, physical focus infinity and iris f/1.4. Record actual
settings, preview, aperture, motor/quiet idle and shutdown. Take at most one
photo only if preview/aperture/motion are normal and MF is confirmed. Stop for
freeze or abnormal drive; remove the battery if unresponsive or motion continues.
No restart or AF-S precedes result/log review. These settings and outcomes are
currently unverified. One cycle has been requested; no results have been reported.
The owner was asked to confirm power-off, USB-cap return and physical reconnect
with the observations before any post-camera reports.

After the owner confirms power-off, return to the USB cap and physical reconnect,
save a fresh native read-only two-pass backup and run the offline decoder.
Compare flash outside `[0x9c00,0xa000)` and protected auxiliary data with this
installation's verified pre-camera readback. Terminal shutdown/fail-stop flushes
v2 records; a ten-second idle does not. Battery loss can leave incomplete/blank
logs. Preserve actual camera frames privately and publish sanitized observations.
