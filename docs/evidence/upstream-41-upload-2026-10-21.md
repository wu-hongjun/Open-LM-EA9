# AF 4.1 upload — October 21, 2026

**AF 4.1 passed strict complete-image/protected-data installation verification,
but camera acceptance failed and further trials are held.** The owner confirms a
photo saved after a reported one-minute shutter delay/freeze; shutdown worked.
Actual focus mode remains unknown. Read-only logs are preserved and the owner
requested original stock restoration. Its upload is complete; physical reconnect
and strict verification are pending.
[Camera/log evidence](upstream-41-camera-failure-2026-10-21.md) ·
[Stock restoration](stock-18-af41-recovery-2026-10-21.md).

[Sanitized receipt](upstream-41-upload-2026-10-21.json) ·
[Candidate and pins](../../firmware/candidates/4.1.0/README.md) ·
[Offline acceptance](upstream-41-crash-diagnostics-2026-10-21.md) ·
[Installation/test/log procedure](../upstream-crash-diagnostic-test.md) ·
[Preservation ledger](upstream-41-upload-preserved-2026-10-21.json).

## Preflight and completed upload

The owner explicitly authorized 4.1 upload for the original 50mm f/1.4, reconnect
verification, one A7C II test, read-only logs, documentation and commit/push. The
owner confirms the adapter is on its USB cap with both apps closed. Starting commit
`12ef4e46cdd9959bd0edf0ccae8e2bfa1c8b8d45` was pushed and the tree clean.

Signed app 0.24.0/build 33, native CLI, full image/manifest and bundled resource pins
match the committed offline receipt. Native CLI SHA256 is
`2f24feab2fd010a5950d144ae24e31288fe2589248caaae439b438db609b14bc`.
Process checks found no updater, prototype app or competing CLI. Descriptor-only
inventory found one qualified, unblocked cap connection and sent no reports.
The prior 4.0 journal is strictly verified. Prepare-only output using a private
copy of the saved lens library matches all 20,480 pinned image bytes.

`dist/ea9ctl apply-crash-upstream contax-zeiss-50-f1-4 --idle` ran once through
unchanged canonical safeguards, exiting 0 at **2026-10-21T13:14:28.210134+00:00 UTC**
(**09:14:28.210134 America/New_York**). It saves a fresh complete two-pass backup,
retains exclusive access/same-unit stock qualification, verifies the final idle
address-scratch read, and synchronizes the durable transaction journal before START.
No guard, uploader source or firmware image changed for this installation.

The fresh backup reports 4.0.0, two matching 131,072-byte flash passes, two auxiliary
passes and 4,359 CHECK/READ exchanges. Independent filesystem checks validate every
file size/digest, known boot code, MCU/geometry, same-unit binding and the complete
prior 4.0 application. Its full flash matches the retained post-camera 4.0 evidence,
including all erased diagnostic bytes; user row, calibration and device-ID windows
also match. Full-flash SHA256:
`46c4d45590e03f9deb6bc325aaec531cef6511ee4a443a2b91e157cfcc815248`.

Uploaded image SHA256:
`fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641`.
Manifest SHA256:
`557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b`.
The original compiled 50mm profile keeps nominal f/1.4, lens ID 234 and Unknown
actual iris. Runtime lens-library edits do not alter this fixed image.

Successful pinned-engine completion implies one acknowledged START and 320
acknowledged 64-byte pages. These are engine-derived counts, not an independent
wire capture. No retry, CHECK/READ, end marker or padding followed START on the
armed connection. No report was sent after native upload returned.

Filesystem-only checks confirm the pending journal's exact planned/published image,
blank diagnostic tail, expected 4.1 metadata and upload timestamp. The armed-connection
marker remains and prior marker membership is preserved. Applied-lens, firmware
observation, qualification and lens-library bytes remain unchanged pending verification.
No canonical journal or safety marker was manually edited. All 156 release/recovery/
pin artifacts, all registry entries and original stock recovery remain exact. Raw
backups, keys, unit identifiers and real traffic stay private.

## Physical reconnect and strict verification passed

The owner explicitly replied “reconnected” to the USB-cap / both-apps-closed /
off-camera question. Process and descriptor preflight confirmed both apps and any
competing CLI absent, unchanged signed CLI/image/manifest pins, the unchanged
uploaded journal, and one qualified adapter on a new, unblocked connection.
Descriptor inventory sent no reports. No safety guard was bypassed.

`dist/ea9ctl verify --idle` ran once and exited 0 at
**2026-10-21T18:51:33.139498+00:00 UTC**
(**14:51:33.139498 America/New_York**). Two matching full-flash passes and two
auxiliary passes completed, totaling 4,359 CHECK/READ exchanges. No firmware writes,
retry or post-return reports were sent.

The independent filesystem audit validates every file size/digest, known boot code,
MCU/geometry, same-unit binding, new connection and reported firmware 4.1.0.
All **20,480 application bytes** `[0x5000,0xa000)` match the complete pinned image,
including all **1,024 pristine diagnostic bytes**. Expected metadata `[0x4000,0x403a)`
matches. Boot code, gap `[0x4040,0x5000)`, upper flash `[0xa000,0x20000)`, user row,
calibration and device-ID windows match the original fresh pre-upload backup.
Only established loader scratch `[0x403a,0x4040)` is excluded; NVM status is checked
for geometry rather than volatile byte identity.

Native publication of the verified journal, original 50mm f/1.4 applied setting
and firmware observation passes independent checks. Old blocked-connection
membership, stock qualification and library bytes remain unchanged. The successful
read connection is unblocked through the normal native workflow; no canonical
journal or safety marker was manually edited.

Readback full-flash SHA256:
`9dd187a9259879010d59ce4cca6d1aaff562b8d2a02b688524ce8a6d6da1f9f0`.
All 156 release/recovery/pin artifacts and every registry entry remain exact.
Raw backups, keys, identifiers and real traffic remain private. This proves the
installed bytes, not physical autofocus, capture or shutdown compatibility.

## Subsequent camera result and return to stock

The owner reports approximately one minute from pressing the shutter until a
photo was taken, a freeze, and successful shutdown afterward. A later clarification
confirms the photo file saved and explicitly requests stock restoration. Actual
MF/AF, Pre-AF, exposure, displayed aperture, preview and motor behavior remain
unverified; the requested setup is not recorded as a confirmed MF cycle.

One guarded read-only backup retained 16 valid diagnostic pages. Code and all
flash outside the reserved tail, protected auxiliary data and canonical records
are unchanged. Five power-on baseline pages, one handshake/shutdown snapshot,
and a later startup `cs-rise-wait` summary survived. Storage is full. These software
records do not reconstruct the owner’s one-minute wall time or establish the shutter
root cause. No extra camera attempt is requested to obtain missing settings.
[Completed analysis](upstream-41-camera-failure-2026-10-21.md).

At the owner’s request, original same-unit stock 1.8.0 upload completed after
preserving the camera logs and another matching fresh backup. The
[recovery record](stock-18-af41-recovery-2026-10-21.md) tracks required physical
reconnect and strict complete-slot/protected-data verification. No source/image
change or verification exception was used for restoration. App 0.24.1/build 34 holds
ordinary 4.1 installation, retains backup/recovery and leaves original pins intact.
