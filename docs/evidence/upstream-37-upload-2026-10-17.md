# AF 3.7 upload — October 17, 2026

**AF 3.7 passed strict USB byte verification after the owner-confirmed physical
reconnect, followed by an independent filesystem audit. One camera cycle has
been requested; its results and log retrieval remain pending.** The owner
explicitly accepted uploading the prepared Contax Zeiss 50mm f/1.4 tracing
candidate. Camera acceptance and a shutter-freeze fix remain unestablished.

[Machine-readable receipt](upstream-37-upload-2026-10-17.json) ·
[Candidate](../../firmware/candidates/3.7.0/README.md) ·
[Offline acceptance](upstream-37-tracing-2026-10-15.md) ·
[Coordinated test/log procedure](../upstream-targeted-trace-test.md)

## Preparation and image identity

Source commit `2af44ff736d28abe46bbd0313f1469fb353c6f5d` was already pushed to
origin/main; the working tree was clean. The signed native CLI is app
0.20.0/build 25, SHA-256
`b9c9f77f80ef80e0fd59c97de0d878d62ef68fd5a30b7d1fe4995479a4cf8e67`.
Preflight found one qualified LM-EA9, no competing updater/app/CLI, a completed
3.6 verification journal and an unblocked connection. Inventory sent no reports.

Native offline preparation with the canonical original 50mm profile exactly
matched the frozen 20,480-byte application, including its 1,024 erased log bytes:

- Image SHA-256: `6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5`.
- Manifest SHA-256: `15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b`.

The reported nominal aperture is f/1.4; actual iris remains Unknown. This build
has a fixed compiled 50mm profile and no runtime lens-profile row. Its previous
offline tests do not establish a fix for the shutter freeze or camera stability.

## Native transaction and independent filesystem audit

The explicit command was
`dist/ea9ctl apply-trace-upstream contax-zeiss-50-f1-4 --idle`, with canonical
native state. The native engine retained exclusive access, stock-upload/unit
qualification, a fresh backup, durable evidence/journal, exact acknowledgements
and the reconnect guard. It exited 0 at **2026-10-17T16:55:49.727247+00:00 UTC**
(**2026-10-17T12:55:49.727247-04:00 America/New_York**).
Transaction: `EEE6BE73-2861-4A3C-B31E-11FB62F67789`.

The successful pinned engine implies one acknowledged START and 320 acknowledged
64-byte pages. These are source/native-engine counts, not an independent wire
capture. No CHECK/READ, retry, end marker or extra padding followed START on the
armed connection. No reports were sent after the native uploader returned until
the owner explicitly confirmed the physical reconnect described below.

Before START, the backup completed two matching 131,072-byte flash reads and two
auxiliary passes, with 4,359 read/check exchanges. It reports 3.6.0; its full flash
SHA-256 is
`504a69512dbd707454112a26d29e6da8cbe0abbfd1a3c1580b5c2d99d4123c61`.
Its complete flash and protected auxiliary windows exactly match the retained
post-camera 3.6 backup. The original qualified boot-code hash and immutable 3.6
prefix match; the existing diagnostic pages are preserved in that backup.

After the uploader exited, a filesystem-only audit rechecked all backup sizes/
digests, unit binding, pending/planned/frozen image equality, expected metadata
and original 50mm settings. At that point the uploaded journal awaited verification
and the armed upload connection's marker remained retained. No journal or safety
marker was manually altered. Raw backups, unit identifiers, state and logs stay
private. Earlier images, pins and original stock recovery were not changed.

## Reconnect and strict verification

The owner explicitly replied “reconnected” to the physical USB-cap reconnect
request, with the updater/app closed and the adapter off the camera. Before any
reports, filesystem/process preflight rechecked the signed CLI/image pins,
uploaded 3.7 journal and absence of competing updater/app/CLI processes.

`dist/ea9ctl verify --idle` ran once, with canonical state. Native verification
required a new connection and the same qualified unit, retained exclusive access
and performed two matching full flash reads and two auxiliary passes (4,359
read/check exchanges). It exited 0 at **2026-10-17T17:04:42.854458+00:00 UTC**
(**2026-10-17T13:04:42.854458-04:00 America/New_York**). No firmware writes or
retries were sent. Full readback flash SHA-256:
`15e78dfa658c36e24843d717959a9971d2c801163fed98d48eb5d47bc3e7d115`.

An independent filesystem-only audit then confirmed:

- Every native backup file's size/digest, MCU geometry, boot hash and same-unit
  binding; the reported version and metadata are 3.7.0.
- Exact equality of all 20,480 application bytes `[0x5000,0xa000)` with the frozen
  image, including all 1,024 pristine diagnostic bytes `[0x9c00,0xa000)`.
- Exact expected metadata `[0x4000,0x403a)` and preservation of boot code,
  `[0x4040,0x5000)`, upper flash `[0xa000,0x20000)`, user row, calibration and
  device-ID windows. Only the six established loader scratch bytes
  `[0x403a,0x4040)` are excluded; volatile NVM status is checked for geometry.
- Native publication of the verified journal, applied original 50mm f/1.4
  setting and firmware observation. The old armed upload-connection marker is
  retained; the successful read-connection marker was cleared by the native
  engine. Neither journal nor safety state was manually changed.

All 131 previously inventoried historical artifacts and the original stock 1.8.0
recovery application remain exact. No firmware, image, manifest or CLI was
modified for this verification. Private readback/log digests are in the
machine-readable receipt; raw data and unit identifiers remain private.

## Pending owner camera cycle

After both verification gates passed, the owner was given the separate procedure
for one loaded-lens MF lifecycle/photo cycle: A mode, confirmed MF, Pre-AF Off
where available, EV 0/Auto ISO, physical infinity/f/1.4, normal live preview,
ten-second idle, at most one photo and one shutdown. If MF cannot be confirmed,
skip the photo. Stop for freeze or abnormal drive; remove the battery if
unresponsive and do not restart/retry. AF-S is a later gate.

No camera outcome is recorded yet. Once unpowered and stopped, the owner must
return the adapter to its cap and explicitly confirm physical reconnect with
the updater/app closed before read-only log retrieval. The existing 3.6
capture/shutdown failure hold remains intact; installation verification does not
establish physical motion, capture, shutdown, optical AF or factory parity.
