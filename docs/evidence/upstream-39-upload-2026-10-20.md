# AF 3.9 upload — October 20, 2026

**AF 3.9 passed strict USB byte verification after physical reconnect and an
independent full-image/protected-data audit. Camera acceptance subsequently
failed; read-only log retrieval is complete and further trials are held.** The
owner reports two photos followed by blocked further capture and normal shutdown.
[Camera/log evidence](upstream-39-camera-failure-2026-10-20.md).

[Sanitized receipt](upstream-39-upload-2026-10-20.json) ·
[Candidate and pins](../../firmware/candidates/3.9.0/README.md) ·
[Offline acceptance](upstream-39-homing-2026-10-20.md) ·
[One-cycle procedure](../upstream-homing-test.md).

## Preflight and upload

The owner explicitly authorized AF 3.9 for the original Contax Zeiss 50mm f/1.4,
reconnect verification, one A7C II cycle, documentation and commit/push. Commit
`d47003e72f87433b26c1e69f4aa991b273c07a0d` was already pushed and the tree clean. App 0.22.0/build 29's
signed native CLI digest and complete image/manifest pins matched the committed
preparation receipt. No competing updater, prototype app or CLI was running.
Descriptor-only inventory found one qualified adapter on an unblocked connection
and sent no reports. The previous 3.8 journal was strictly verified; no pending
transaction was bypassed. Native prepare-only output using a private copy of the
current library matched all 20,480 pinned bytes.

`dist/ea9ctl apply-homing-upstream contax-zeiss-50-f1-4 --idle` ran once with the
canonical native safeguards. It exited 0 at **2026-10-21T01:04:55.493674+00:00 UTC**
(**2026-10-20T21:04:55.493674-04:00 America/New_York**). The complete fresh backup precedes
START; the engine preserves exclusive access, same-unit qualification, durable
journal, per-page acknowledgements and the physical-reconnect guard.

The pre-upload backup reports 3.8.0, with two matching 131,072-byte flash passes
and two auxiliary passes, 4,359 CHECK/READ exchanges. An independent filesystem
verification checks every file's size/digest, qualified boot hash, MCU/geometry,
same-unit binding, and the immutable 3.8 prefix. Pre-upload flash SHA-256:
`479e95c3ff4d3954d75af2afaffb6199846da016ffe9c32ea254b0344594173d`. Comparison with the retained October 20 post-camera 3.8
backup confirms exact complete-flash and protected auxiliary-data equality.
Existing camera evidence is preserved. The uploader also validates its final idle read
before START, keeping the loader's address scratch in its required state.

Image SHA-256: `87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44`.
Manifest SHA-256: `9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a`.
The fixed original 50mm profile retains nominal f/1.4, lens ID 234 and an Unknown
actual iris. This transaction installs the already reviewed candidate; no source,
image, profile layout, controller or guard was changed during the upload task.

The successful pinned native path implies one acknowledged START and 320
acknowledged 64-byte pages. Counts are engine-derived, not a separate wire
capture. No retry, CHECK/READ, end marker or extra padding followed START on the
armed connection, and no report was sent after the uploader returned.
Filesystem-only auditing confirms planned/frozen/journal image equality,
expected metadata from the backup, uploaded timestamp and retained armed
connection marker. The prior marker set is preserved; applied lens, firmware
observation, stock qualification and lens library remain unchanged pending
verification. No canonical journal or safety marker was manually edited.

## Physical reconnect and strict verification

The owner explicitly confirmed physical USB-cap reconnect with both apps closed
and the adapter off-camera. Preflight rechecked the signed CLI/image/manifest,
unchanged uploaded journal, absence of competing processes and one qualified
adapter on a new unblocked connection. Inventory sent no reports.

`dist/ea9ctl verify --idle` ran once and exited 0 at
**2026-10-21T01:12:24.166263+00:00 UTC** (**2026-10-20T21:12:24.166263-04:00 America/New_York**).
Two matching 131,072-byte flash passes and two auxiliary passes completed,
4,359 CHECK/READ exchanges. No firmware writes or retries were sent.

The independent filesystem audit confirmed:

- Every backup file's size/digest, recognized boot code and MCU/geometry, same
  unit binding and the new connection identity; firmware/version metadata 3.9.0.
- All 20,480 application bytes `[0x5000,0xa000)` match the pinned image, including
  all 1,024 blank diagnostic bytes. This is complete-image verification, not a
  log-prefix comparison or a version-string check.
- Exact expected metadata `[0x4000,0x403a)`; unchanged boot, gap `[0x4040,0x5000)`,
  upper flash `[0xa000,0x20000)`, user row, calibration and device-ID windows.
  Only the established loader scratch `[0x403a,0x4040)` is excluded. Volatile NVM
  status is validated for geometry, not required to be byte-identical.
- Native publication of the verified journal, original 50mm f/1.4 setting and
  firmware observation. The prior blocked-connection set is retained exactly;
  the native engine clears the successful read-connection marker. Stock upload
  qualification and library bytes remain unchanged. No manual state edits.

Readback full-flash SHA-256: `be84ddc1c99e618280175af8af44b12e632abb5ab311edbb4d49a60dbe6a1798`.
All 141 historical release/recovery artifacts and original stock recovery remain
exact, as do candidate/manifest/CLI pins. These checks establish installation
bytes, not camera focus, capture, exposure, shutdown or factory parity.

## Historical camera guidance and subsequent result

The menu sequence was clarified before camera results: switch on once without
shutter/AF-ON input, check normal initial preview/motor behavior, then use the
powered-on menus to confirm MF and Pre-AF Off before any shutter press. No extra
power cycle is needed for menu setup. Startup focus mode remains unknown unless
observed; the MF gate applies before the photo.

The agreed test is one loaded-lens lifecycle/photo cycle with MF confirmed:
physical infinity/f/1.4, still-photo A, confirmed MF separately from exposure
mode, Pre-AF Off if available, EV0/AutoISO, normal live preview/motor behavior,
ten-second quiet idle, at most one photo and one shutdown. If MF is unknown,
skip the photo. Stop for a freeze or abnormal drive, switch off and remove the
battery if unresponsive; no restart/retry. AF-S is a later gate after review.
Return to the cap and confirm reconnect before one read-only backup/log review.
Unavailable settings or outcomes stay unknown.

All 141 historical release/recovery artifacts, prior registry entries and original
stock 1.8 recovery remain exact. Candidate 3.9 image/manifest/resource/CLI pins are
unchanged. Raw backups, keys, unit identifiers, camera frames and operands remain
private. The 3.6/3.7/3.8 holds remain. This upload is not camera acceptance,
a physical homing/shutter cure or factory parity.

The subsequent report records two photos followed by blocked further capture,
with normal shutdown. AF-S is tentatively recalled with explicit uncertainty;
focus mode remains unconfirmed and saved-file status is unknown.
One read-only backup confirms phase 17 with a 300-tick drive phase, 20-tick stillness
anchor age and 17 later consumed requests, with code/protected data unchanged.
See the [camera evidence](upstream-39-camera-failure-2026-10-20.md); installation
verification remains a historical fact, distinct from failed camera acceptance.
