# Upstream C 3.2 installation and diagnostic cycle — October 15, 2026

**Upload and strict physical-reconnect verification passed. No 3.2 camera cycle was performed.**
The owner explicitly requested 3.2 for the Contax Zeiss 50mm f/1.4 and confirmed
that the adapter was on its USB update cap with the official updater closed.
The owner subsequently requested resolving this transaction before a separate
3.6 installation and explicitly confirmed physical reconnect on October 15.

## Image and preflight

The release source is `c43e39079c9151acf9e9f9b0e61f47ab204c8b22`, already pushed to origin/main.
Signed CLI from app 0.15.0/build 19 matched its published SHA-256
`8530a9576cd82ef68e52398d5746d8ec7ec0c61a8d683c7f0f9d00ab30853a7d`.
Descriptor-only inventory found one qualified adapter on an unblocked connection.
The previous 3.1 journal had completed verification; the same-unit stock-upload
qualification remained present. Canonical state was not edited manually.

Native offline `prepare-startup` with the original 50mm f/1.4 profile matched
[the fixed candidate](../../firmware/candidates/3.2.0/README.md) exactly:
20,480 bytes, SHA-256 `e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
All 1,024 diagnostic bytes were FF. There is no runtime lens-profile row.
The declared aperture is nominal f/1.4; the manually operated actual iris remains
unknown. This upstream C diagnostic repairs a reproduced first-window RX race,
restores stock lens ID 234 as a compatibility control and adds bounded startup/
handshake records. Upstream servo, map/prediction and board configuration are
preserved. The [preparation record](upstream-32-startup-diagnostic-2026-10-15.md)
contains the software tests and remaining physical limits; no factory-equivalence
or A7C II compatibility claim follows from those tests.

## Upload and offline audit

Command: `dist/ea9ctl apply-startup contax-zeiss-50-f1-4 --idle` with canonical
native state. Exclusive access, updater detection, same-unit qualification,
fresh backup, durable journal, exact acknowledgements and reconnect guards
remained enabled. Native exit status was 0 at **2026-10-15T04:30:16.715786+00:00**
(**2026-10-15T00:30:16.715786-04:00 America/New_York**).
Transaction: `23FD8342-6BF8-41A2-8250-4AF6F46DF246`. One START and 320 64-byte pages completed;
these counts follow the native successful-engine/image evidence, not an
independent wire capture. No CHECK/READ, end marker, retry or extra padding
followed START on the armed connection. Its reconnect marker remains retained.

The pre-upload backup contains two matching full-flash and auxiliary passes,
131,072 flash bytes and 4,359 CHECK/READ exchanges. Firmware reported 3.1.0;
the application matches pinned upstream 3.1. Whole-flash equality with the last
strict 3.1 readback is **True**.
Flash SHA-256: `07f3dc251d953a128e0c0b10c6a4e172c5620a360be7507511a57f68c1c1ff4d`.
The original qualified boot-code hash still matches. A separate offline audit
checked all backup files against their size/hash manifest, unit binding,
planned/pending/committed image equality, the upload timestamp and retained guard.
Raw backups, unit identifiers, factory data, journals and exchange logs remain
private. Original stock recovery and all earlier pinned firmware are unchanged.

## Completed reconnect verification

The owner confirmed physical unplug/reconnect through the USB cap, updater
closed and adapter off the camera. Native `dist/ea9ctl verify --idle` required
a different connection and the same unit before reports, completed two matching
full-flash/auxiliary passes, and exited 0. Verification completed at
**2026-10-15T12:02:46.874568+00:00 UTC**
(**2026-10-15T08:02:46.874568-04:00 America/New_York**).
The reviewed, signed CLI from app **0.19/build 23** was used for this later step;
its SHA-256 is `781231a3e6b6ef29e442cef982f92e4eb158d805ac315d226bf112eeb332d394`.
The original upload CLI/version evidence above remains unchanged.

The readback reports **3.2.0**, 131,072 flash bytes and 4,359 CHECK/READ
exchanges, with no writes or retries. A separate offline audit validates every
backup file against its size/hash manifest and repeats all strict comparisons:
exact 20,480-byte application including all 1,024 blank diagnostic bytes, exact
58 known metadata bytes, unchanged boot code, protected gap, retained upper
flash, user row, calibration and device-ID window. The six established loader
scratch bytes `[0x403a,0x4040)` are the sole metadata exclusion. No diagnostic
prefix relaxation or manual journal/guard change was used.

Full readback SHA-256: `e163b1483e02f657a86cd1444f77a01fc77982ee11992b8edb2f3853827be29c`.
Canonical applied-lens and dated firmware-observation records were published by
the native service. Its successful read-connection marker was cleared, while
the original armed upload connection's marker remains retained. Raw backups,
unit data, exchange logs and state remain private.

## Camera disposition

No 3.2 camera cycle, photograph or log retrieval occurred. The owner requested
verification followed by a separate **3.6** installation for the same 50mm
f/1.4 profile. This strict pass resolves the original transaction without
claiming camera capture, exposure, focus, shutdown or factory parity. Coordinate
the next installation and one-cycle test through the
[3.6 procedure](../upstream-handoff-test.md); its upload needs its own physical
reconnect and complete byte verification before camera use.
