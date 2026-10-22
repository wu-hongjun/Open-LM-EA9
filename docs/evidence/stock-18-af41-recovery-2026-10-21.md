# Original stock 1.8 recovery after AF 4.1 — October 21, 2026

**Original stock 1.8.0 is restored and strictly byte/protected-data verified after
owner-confirmed physical reconnect.** The complete original application slot and
known metadata match, and boot code, saved records and factory data are preserved.
The owner requested this restoration after the failed 4.1 camera attempt. Its logs
are saved; no further custom-firmware camera trial or new stock test is requested.

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

## Completed physical reconnect and strict verification

The owner replied “reconnected” to the USB-cap / both-apps-closed / off-camera
question. Process checks found no competing app/updater/CLI. The signed CLI and
original source pins matched, the uploaded stock journal was unchanged, and
one qualified adapter appeared on a new unblocked connection. Descriptor-only
inventory sent no reports.

Normal native `verify --idle` ran once and exited 0 at
**2026-10-22T02:19:39.461618+00:00 UTC**
(**October 21, 22:19:39.461618 America/New_York**). Two matching 131,072-byte flash
passes and two auxiliary passes completed, totaling 4,359 CHECK/READ exchanges.
No write, retry or post-return report was sent.

The independent filesystem audit checks every file size/digest, boot code,
MCU/geometry, same-unit identity and new connection, then verifies:

- All **110,592 bytes** `[0x5000,0x20000)` match the original stock slot exactly,
  including the 20,172-byte vendor application and all original upper-flash data.
- All **58 known stock metadata bytes** `[0x4000,0x403a)` match the original source.
- Boot code `[0,0x4000)` and the protected saved-record/gap `[0x4040,0x5000)`
  match the fresh pre-restoration backup; checked user row, calibration and
  device-ID windows match both fresh and original backups.
- Only the established six adjacent loader scratch bytes `[0x403a,0x4040)` are
  excluded. NVM status is checked for geometry, not volatile byte identity.
- Native workflow publishes the verified stock journal and 1.8.0 observation,
  refreshes same-unit stock qualification, and clears the custom applied-lens
  record. The local lens library and previous blocked-connection membership
  remain unchanged; the successful read connection is unblocked normally.

No verification exception, manual journal edit or marker bypass was used.
Readback full-flash SHA256:
`862ae4577fea347cf5fe94344028bb29e3856f787876a8550d814d0d8bba23da`.
This matches the [previous strictly verified stock readback](stock-18-af28-recovery-2026-10-12.json).
The only differences from the earliest untouched original full flash are 12
bytes in the preserved saved-record/gap; loader scratch happens to match too.
Those 12 bytes match the fresh pre-restoration backup. The original stock slot
and known metadata match completely.

All 156 release/recovery/pin artifacts, registry entries, original recovery and
4.1 camera evidence remain preserved. Raw backups, keys, identifiers and real
frames remain private. This completes the requested restoration. No new camera
test is required, and the earlier stock aperture/exposure limitations are not
claimed resolved by USB byte verification.
