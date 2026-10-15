# Upstream C 3.6 installation and camera cycle — October 15, 2026

**Strict USB verification passed; camera capture/shutdown failed. Further 3.6 camera trials are held.**
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

## Camera failure and completed read-only log retrieval

The requested one-cycle procedure is preserved in the
[held runbook](../upstream-handoff-test.md). The owner subsequently reports
inability to take a photo, slight motor movement when trying to focus, a frozen
camera on shutter press and shutdown nonresponse. Actual focus mode, Pre-AF,
aperture, physical ring settings, exact half/full-press stage, saved-file status
and battery-removal action remain unverified. This is a failed capture/shutdown
result, not a confirmed controlled MF or AF-S trial. No further 3.6 trial was
requested. The owner was told to stop and remove the battery if unresponsive.

After the owner reported returning the lens to the computer, root interpreted
the existing cap-return context and saved a new native read-only backup. The
native service found a new qualified same-unit connection, completed two matching
flash/auxiliary passes and 4,359 CHECK/READ exchanges, and exited 0 at
**12:30:35 UTC / 08:30:35 America/New_York**. No upload, restore, erase or retry
was sent. Full flash SHA-256:
`504a69512dbd707454112a26d29e6da8cbe0abbfd1a3c1580b5c2d99d4123c61`.

A separate offline audit finds all flash changes confined to
`[0x9c00,0xa000)` diagnostics, with every other flash byte and protected auxiliary
window unchanged from this installation's strict readback. The immutable code
prefix matches 3.6. The decoder identifies 13 valid writer-consistent pages,
three erased pages, no invalid/inconsistent/unassociated pages, and a complete
48-event retained first/last snapshot with 6,429 event evictions. A connected
breadcrumb, sticky `servo-wrong-way` fault and later shutdown UART-disable
marker narrow the observation. They do not establish shutter cause, motor
polarity, reply delivery or physical camera shutdown. The marker precedes the
post-flush shutdown tail, which is unobserved.

[Failure evidence and source interpretation](upstream-36-camera-failure-2026-10-15.md)
and [independent Astra32 review](../audits/astra-32-af36-capture-failure-2026-10-15.md)
retain limits. App0.19.1/build24 marks 3.6 held and disables ordinary installation
while preserving backup/recovery. Original firmware, manifest/digest pins and
stock recovery remain exact; the successful USB verification is not relabeled
a failed byte comparison. Raw camera frames, dump, identities and full decoded
records remain private. No additional firmware upload or stock restoration was
performed after this failure.
