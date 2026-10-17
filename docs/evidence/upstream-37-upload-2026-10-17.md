# AF 3.7 upload — October 17, 2026

**Upload completed; physical reconnect and strict byte verification are pending.
Keep the adapter off the camera.** The owner reported connecting the adapter to
the Mac and explicitly accepted uploading the prepared Contax Zeiss 50mm f/1.4
tracing candidate. No camera test or post-upload USB read has occurred.

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
armed connection. No reports were sent after the native uploader returned.

Before START, the backup completed two matching 131,072-byte flash reads and two
auxiliary passes, with 4,359 read/check exchanges. It reports 3.6.0; its full flash
SHA-256 is
`504a69512dbd707454112a26d29e6da8cbe0abbfd1a3c1580b5c2d99d4123c61`.
Its complete flash and protected auxiliary windows exactly match the retained
post-camera 3.6 backup. The original qualified boot-code hash and immutable 3.6
prefix match; the existing diagnostic pages are preserved in that backup.

After the uploader exited, a filesystem-only audit rechecked all backup sizes/
digests, unit binding, pending/planned/frozen image equality, expected metadata
and original 50mm settings. It confirmed the uploaded journal awaits verification
and the armed upload connection's marker remains retained. No journal or safety
marker was manually altered. Raw backups, unit identifiers, state and logs stay
private. Earlier images, pins and original stock recovery were not changed.

## Pending reconnect gate

The owner was asked to physically unplug/reconnect through the USB cap, keep
TECHART Update and Open LM-EA9 closed, leave the adapter off the camera and reply
“reconnected.” No further hardware report is permitted before that confirmation.
The next native verification must require a new connection and the same unit,
then compare the complete pristine application/log tail, known metadata and
protected flash/auxiliary data. An independent offline audit follows. Only the
six established loader scratch bytes `[0x403a,0x4040)` are excluded from metadata
preservation; a decoder prefix match cannot replace full installation verification.

Camera behavior remains unqualified. The existing 3.6 capture/shutdown failure
hold remains intact. A camera cycle will be coordinated only after the strict
verification gate, using the separate test/log procedure.
