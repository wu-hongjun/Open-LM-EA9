# Original stock 1.8 recovery after AF 4.1 — October 21, 2026

**Original stock upload finished; owner-confirmed physical reconnect and strict
byte/protected-data verification are pending.** Keep the adapter off the camera
until that verification passes. The owner explicitly requested stock after a
reported one-minute shutter delay/freeze before one photo saved on 4.1; shutdown
worked afterward. No additional custom camera trial is requested.

[Sanitized receipt](stock-18-af41-recovery-2026-10-21.json) ·
[Preserved 4.1 camera/log evidence](upstream-41-camera-failure-2026-10-21.md) ·
[Original committed recovery source](../../firmware/recovery/stock-1.8.0/README.md).

## Original source and native restoration

The original same-unit backup passes every file size/digest, recognized boot code,
MCU and geometry check. It reports 1.8.0 and matches the unit’s identity and factory
auxiliary windows. Its hashes are:

- Original full source flash: `1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`.
- Vendor application, 20,172 bytes: `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
- Complete restoration slot `[0x5000,0x20000)`, 110,592 bytes: `265f93797db99f2dbba5b649bf5b12bc19efadeaa8e9fe77ade5fca128d17173`.

The original 58 known START metadata bytes are used. No key, decrypted private
backup or unit identifier is published; the encrypted committed recovery remains
intact. Process checks found both apps absent and descriptor-only inventory found
one qualified, unblocked cap connection, sending no reports.

`dist/ea9ctl restore-stock ORIGINAL.ea9backup --idle` ran once through unchanged
native safeguards and completed at **2026-10-22T01:53:37.214852+00:00 UTC**
(**October 21, 21:53:37.214852 America/New_York**), exit 0. Before START it saved and
synchronized a fresh complete two-pass flash/auxiliary backup, verified the final
idle scratch-address read, preserved prior recovery journal/history and published
a durable stock transaction. The fresh pre-restore flash exactly matches the
separately preserved post-camera 4.1 evidence:
`490aee27c5dcfb639f62a5108b346ec1bfa430ce911e4bb1b80d23a2d59ff7b5`.
Its 4,359 CHECK/READ exchanges, file digests, identity and geometry pass audit.

Successful pinned-engine completion implies one acknowledged START and 1,728
acknowledged 64-byte pages. These are engine-derived counts, not an independent
wire capture. No retry, CHECK/READ, end marker or padding followed START. No
bootloader, protected saved-record/gap or auxiliary write was issued. No post-return
USB report has been sent.

Filesystem-only checks confirm the pending journal’s exact original complete slot,
stock metadata and upload timestamp. The armed-connection marker remains; previous
blocked membership is preserved. Prior 4.1 journal/setting/qualification were archived
by native recovery, and applied setting, observation, qualification and library
remain unchanged until verification. No journal, safety marker or guard was manually
changed. All 156 release/recovery/pin artifacts and registry entries remain exact.

## Required final verification

The owner must physically unplug/reconnect through the USB cap, keep both apps
closed and explicitly confirm before further reports. Then use normal native
`verify --idle` once on the new connection, followed by an independent filesystem
audit. It must match the **entire original 110,592-byte slot and 58 known stock
metadata bytes**, preserve boot code and `[0x4040,0x5000)` against the fresh pre-restore
backup, and preserve checked factory auxiliary data. Only established six-byte
loader scratch is excluded; no relaxed verification exception is planned.

After success, native workflow should verify the stock journal, publish 1.8.0,
refresh stock qualification and clear the custom applied-lens record. Retain all
backups and existing markers through that native process. No new stock camera test
or additional 4.1 attempt is required for this restoration request. Stock camera
behavior and the earlier aperture/exposure limitations are not established by USB
readback alone.
