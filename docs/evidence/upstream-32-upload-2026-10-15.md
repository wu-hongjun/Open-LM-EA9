# Upstream C 3.2 installation and diagnostic cycle — October 15, 2026

**Upload complete; owner physical reconnect and strict byte verification pending.**
The owner explicitly requested 3.2 for the Contax Zeiss 50mm f/1.4 and confirmed
that the adapter was on its USB update cap with the official updater closed.
Keep the adapter off the camera until reconnect verification passes.

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

## Pending reconnect verification

Require the owner's physical unplug/reconnect confirmation before native
`dist/ea9ctl verify --idle`. It must see a different connection and the same
unit, then complete a fresh matching two-pass readback. Compare every byte of
`[0x5000,0xa000)`, including the blank diagnostic tail, exact known metadata,
unchanged boot code, protected gap, upper flash and auxiliary data. The sole
metadata exclusion is the established six loader scratch bytes
`[0x403a,0x4040)`. Repeat those comparisons in an offline audit. No guard removal
or relaxed diagnostic-image matching is permitted.

## Pending one-cycle camera check and log retrieval

Use [the coordinated procedure](../upstream-startup-diagnostic-test.md): one
loaded-lens cycle with A mode, separately selected MF, Pre-AF Off where available,
EV 0, Auto ISO, physical focus infinity and iris f/1.4. Record actual settings,
preview, displayed aperture, motor/idle and shutdown. Take at most one photograph
only if preview/aperture/motor behavior are normal and MF is confirmed. Stop on
freeze or abnormal drive; remove the battery if unresponsive or motion continues.
No AF-S attempt or restart precedes log retrieval.

After the owner confirms the adapter is unpowered, returned to its USB cap and
physically reconnected with the updater closed, save a new native read-only
two-pass `backup`, then run the offline startup decoder. Require the immutable
prefix to match 3.2 and compare flash outside `[0x9c00,0xa000)` plus all factory
auxiliary data against this installation's verified pre-camera readback. Real
camera exchange records remain private; publish sanitized stages, counts,
checksums, outcomes and uncertainty. A blank log alone does not locate a failure.
Do not call `inspect` to bypass whole-image equality after diagnostic self-writes.
