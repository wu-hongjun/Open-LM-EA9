# AF 3.8 upload — October 19, 2026

**AF 3.8 passed strict USB byte verification after the owner-confirmed physical
reconnect, followed by an independent filesystem audit.** Camera acceptance
subsequently failed; read-only log retrieval is complete and further 3.8 trials
are held. The owner reports normal shutdown, hunting and a motor reset followed
by blocked further photos. [Camera evidence](upstream-38-camera-failure-2026-10-20.md).

[Machine-readable receipt](upstream-38-upload-2026-10-19.json) ·
[Candidate](../../firmware/candidates/3.8.0/README.md) ·
[Offline acceptance](upstream-38-readiness-2026-10-19.md) ·
[Coordinated camera/log procedure](../upstream-readiness-test.md).

## Preflight and transaction

The owner explicitly authorized uploading AF 3.8 for the original Contax Zeiss
50mm f/1.4, followed by reconnect verification, one camera cycle and log
retrieval. Source commit `114f0d7693b6d362f50c9402bd4d53623c940602` was pushed and the working
tree was clean. App 0.21.0/build 27's signed CLI has SHA-256
`1d993380476f6d7797398d2304f36ea0a6f162a45bb7db73762f13db25194d9c`. Preflight found one qualified adapter on an unblocked
connection, no competing updater/app/CLI and the completed 3.7 verification
journal. Inventory sent no reports. Native prepare-only output exactly matched
the complete pinned application and pristine diagnostic tail.

`dist/ea9ctl apply-readiness-upstream contax-zeiss-50-f1-4 --idle` ran once with
canonical native state and exited 0 at **2026-10-19T16:09:00.054953+00:00 UTC**
(**2026-10-19T12:09:00.054953-04:00 America/New_York**). The native path retained
exclusive access, same-unit/stock-upload qualification, fresh backup, durable
journal, acknowledgements and the reconnect guard.

The pre-upload backup performed two matching 131,072-byte flash reads and two
auxiliary passes (4,359 read/check exchanges). It reports 3.7.0, matches the
immutable 3.7 code prefix and passes independent size/digest/boot/MCU-geometry
and same-unit checks. The complete flash and protected auxiliary windows match
the retained October 19 post-camera 3.7 backup. Existing diagnostic evidence is
preserved in both that older backup and the fresh pre-upload backup.

Image SHA-256: `8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`. Manifest SHA-256:
`be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0`. The fixed profile remains 50mm, nominal f/1.4,
lens ID 234; actual iris is Unknown. Library edits cannot change this compiled
image. Aperture policy, capture/shutdown ownership and controller remain 3.7's.

Successful pinned native execution implies one acknowledged START and 320
acknowledged 64-byte pages; these are engine-derived counts, not a separate wire
capture. No CHECK/READ, retry, end marker or extra padding followed START on the
armed connection. No hardware report was sent after the uploader returned.
The independent post-upload audit used files only and confirmed planned/frozen/
journal image equality, original profile, preserved metadata source and retained
armed-connection marker. It does not substitute for readback.

## Reconnect and strict verification

The owner explicitly confirmed physical USB-cap reconnect with the updater/app
closed and the adapter off the camera. Before reports, preflight rechecked the
signed CLI and image pins, uploaded journal, absence of competing processes,
one qualified adapter and a new unblocked connection. Inventory sent no reports.

`dist/ea9ctl verify --idle` ran once and exited 0 at
**2026-10-19T16:14:45.430257+00:00 UTC**
(**2026-10-19T12:14:45.430257-04:00 America/New_York**).
Two matching full-flash reads and two auxiliary passes completed (4,359
read/check exchanges). No firmware writes or retries were sent.

The independent filesystem audit then confirmed:

- All backup file sizes/digests, MCU geometry, qualified boot hash, same-unit
  binding and a new registry identity. Reported version and metadata are 3.8.0.
- Exact equality of all 20,480 application bytes `[0x5000,0xa000)` with the pinned
  image, including all 1,024 blank log bytes `[0x9c00,0xa000)`.
- Exact expected metadata `[0x4000,0x403a)` and unchanged boot code,
  `[0x4040,0x5000)`, upper flash `[0xa000,0x20000)`, user row, calibration and
  device-ID windows. Only the established six loader scratch bytes
  `[0x403a,0x4040)` are excluded; volatile NVM status is checked for geometry.
- Native publication of verified journal, original 50mm f/1.4 setting and
  firmware observation. The old armed upload marker remains; the native
  engine cleared the successful read-connection marker. No manual state edits.

Readback full-flash SHA-256:
`e7874dca81e26825669acc9b3e8b38b19422f7e9de5bdbc2e9223897e8e1f17c`. All 136 historical artifacts, old registry entries
and original stock recovery remain exact. No image, manifest or CLI changed.
These checks qualify installation bytes, not camera capture, focus or shutdown.

## Historical camera guidance and subsequent result

One loaded-lens MF lifecycle/photo cycle was requested after those gates passed;
AF-S is a later gate. The runbook requires confirmed MF, Pre-AF Off where
available, physical infinity/f/1.4, normal preview/motor behavior, ten-second
idle, at most one photo and one shutdown. Unknown settings remain unknown; a
failed or unconfirmed MF gate skips the photo. Stop on a freeze or abnormal
drive, remove the battery if unresponsive, and do not restart/retry. Preserve a
fresh read-only backup after the owner confirms return to the USB cap.

All 136 historical artifacts, prior registry entries and original stock recovery
remain exact. No firmware/image/manifest/CLI pin changed for this upload; no
journal or safety record was manually altered. Raw backups, unit identifiers,
real frames and operands remain private. 3.6/3.7 camera-failure holds persist;
installation is not camera acceptance or factory parity.

The owner subsequently reported hunting, apparent focus for one photo, then a
motor reset and no further photos. Shutdown was normal and exposure was AUTO;
actual focus mode and file-saving status remain unknown. Read-only retrieval
on October 20 found 14 valid pages and drive-phase homing failure 17, with code
and protected data unchanged. No further camera attempt is requested. See the
[full evidence and limits](upstream-38-camera-failure-2026-10-20.md). Historical
pristine installation verification remains intact; the post-camera diagnostic
backup is not relabeled as full-image verification.
