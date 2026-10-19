# AF 3.8 upload — October 19, 2026

**Upload complete; strict verification is pending an owner-confirmed physical
USB-cap reconnect. Keep the adapter off the camera until verification passes.**
No 3.8 camera test or post-camera log retrieval has occurred. The physical
homing failure and capture/shutdown freeze remain unresolved.

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

## Pending gates

The next required step is the owner's explicit physical unplug/reconnect
confirmation, with updater/app closed and adapter off-camera. Only then may
native strict verification read the complete application, expected metadata,
pristine diagnostic tail and unchanged protected/factory data. A separate
offline readback audit follows. A version match alone is insufficient.

One loaded-lens MF lifecycle/photo cycle is authorized after those gates pass;
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
