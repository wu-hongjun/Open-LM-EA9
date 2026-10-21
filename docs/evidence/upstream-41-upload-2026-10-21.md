# AF 4.1 upload — October 21, 2026

**Upload finished; owner-confirmed physical reconnect, strict byte/protected-data
verification, one camera cycle and log retrieval are pending.** Keep the adapter
off the camera until verification passes. This installs the existing crash-diagnostic
candidate for the original Contax Zeiss 50mm f/1.4; it does not establish a shutter
freeze, physical homing, exposure or optical AF fix.

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

## Required physical reconnect and strict verification

The owner must physically unplug/reconnect through the USB cap, keep both apps
closed and explicitly confirm before further USB reports. The loader remains in
upload mode and the native guard prohibits reports on that armed connection.
After confirmation, recheck process/image/journal/new-connection state, then run
strict native verification once. It must compare all 20,480 application bytes,
including the pristine 1K diagnostic tail, expected metadata and protected flash /
auxiliary windows. Only established loader scratch exclusions are permitted.
Independently audit the saved readback before camera use. A reported version or
matching file pin does not prove installed bytes.

## Camera cycle and log retrieval remain pending

After strict verification, guide one loaded-lens cycle: camera off and USB cable
disconnected, physical infinity/f/1.4, live-preview/startup check, then use powered-on
menus to confirm MF separately from still-photo A and Pre-AF Off if available.
The earlier AUTO wording does not establish actual focus mode. Wait ten quiet
seconds after movement stops, take at most one photo only with confirmed MF and
normal preview/aperture/motor behavior, then switch off once. Skip the photo if
these conditions cannot be confirmed. No restart or AF-S attempt is requested yet.

For freeze or abnormal drive, stop input, switch off, remove the battery if
unresponsive or movement continues, and do not retry. Do not leave a moving fault
powered to obtain logs. Power loss before persistence can still lose the retained
checkpoint; watchdog timing/reset/retention remain physically unqualified. A crash
latch intentionally blocks later motor/protocol initialization.

After camera off/unpowered and stopped motor, the owner returns it to the USB cap
and explicitly confirms reconnect with both apps closed. Only then retrieve one
guarded two-pass read-only backup. Audit protected data/code and decode the permitted
diagnostic-tail differences under 4.1 pins. A valid baseline is not proof normal
initialization or capture completed; a recovered page is an earlier foreground
summary, not exact crash registers/time. Camera acceptance remains unqualified until
actual observations and saved logs are reviewed.
