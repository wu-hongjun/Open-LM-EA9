# Stock 1.8 recovery after the AF 2.8 camera failure

October 12, 2026, America/New_York. **Original stock 1.8 is restored;
physical reconnect, strict two-pass native verification and a separate offline
readback audit passed.** The
owner explicitly requested stock 1.8 restoration and confirmed that the adapter
is on its USB cap with the official updater closed. Descriptor-only inventory
found exactly one qualified adapter on a fresh, unblocked connection, sending
no reports. The original same-unit source and CLI signature verify offline.

The [AF 2.8 failure record](af-28-camera-failure-2026-10-12.md) preserves frozen
preview, intermittent poor focus response, darker exposure and a later shutdown
hang requiring battery removal. AF 2.8's successful earlier strict USB
verification remains recorded separately. Further camera trials of that image
are suspended. Recovery does not establish a cause for those failures or fix
the earlier owner-reported stock aperture/exposure limitations.

## Source and protected evidence

- Original full source flash SHA-256:
  `1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`.
- Original stock application, 20,172 bytes at `0x5000`, SHA-256:
  `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
- Full restoration slot `[0x5000,0x20000)`, 110,592 bytes, SHA-256:
  `265f93797db99f2dbba5b649bf5b12bc19efadeaa8e9fe77ade5fca128d17173`.
- Original 58 known START metadata bytes, loader version 1.8.0.
- Qualified loader SHA-256:
  `8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895`.

Every original backup file matches its manifest; recorded source reads were two
matching complete flash and auxiliary passes. Offline verification checks the
MCU/geometry, original application/slot, unit binding and existing AF 2.8 verified
journal. The public encrypted recovery bundle remains intact; no decryption or
key publication was needed. The private AF 2.8 evidence snapshot and original
backups are retained. Canonical markers/journals were not deleted or bypassed.

## Native restoration

The normal `dist/ea9ctl restore-stock ORIGINAL.ea9backup --idle` path acquires
the shared USB lock, checks the absent updater and exclusive same-unit descriptor,
qualifies the loader and saves a fresh two-pass full flash/auxiliary backup
before writing. It synchronizes recovery evidence, resets the idle READ address
scratch, preserves the previous journal/history and writes a durable stock
journal before START. The planned transfer is one START and 1,728 acknowledged
64-byte pages, with no retry or CHECK/READ/end marker after START. Bootloader,
protected gap/record and factory auxiliary writes are excluded.

Native upload exited 0 at 19:46:53 UTC / 15:46:53 America/New_York. Transaction
`1D8FBD3A-7229-4C43-9FA8-EA6600679CF8` contains the exact original full slot,
original known stock metadata and a successful upload timestamp; no verification
timestamp is present. A separate offline audit checked the journal/source and
all pre-recovery backup files. One START and 1,728 exactly acknowledged pages
follow successful native engine/image evidence; no independent wire capture is
claimed. The armed upload-connection marker remains retained.

The fresh pre-recovery backup records two matching full flash and auxiliary
passes, with 4,359 CHECK/READ exchanges. Its flash hash is
`43c71108aa7a39d28f0d293a28074e0b0b1f35dd5693509fc5154a5d038f8a98`,
exactly the previously verified AF 2.8 readback. Persistent flash was unchanged
through the failed camera sessions. The application/profile is still exact;
this does not identify or recover the runtime failure. No post-START report,
retry, bootloader/protected-gap/record/factory-data write or verification
exception was used.

A camera/cap power cycle loses
volatile state; a flash backup cannot reconstruct the lost runtime fault or
E-mount traffic.

## Completed reconnect verification

The owner replied “reconnected.” Descriptor-only inventory detected a different
qualified connection; normal native `verify --idle` validated the same unit
and exited 0 at 19:50:06 UTC / 15:50:06 America/New_York. The new backup has
two matching complete flash and auxiliary passes, with 4,359 CHECK/READ
exchanges. A separate offline audit verified every backup-file digest and
repeated the strict comparisons:

- The complete original application slot `[0x5000,0x20000)` and all 58 known
  stock metadata bytes `[0x4000,0x403a)` match the original same-unit source.
- Boot code `[0,0x4000)` and the protected gap/saved-motion record
  `[0x4040,0x5000)` match the fresh pre-recovery backup.
- Checked factory user-row, calibration and device-ID bytes match both the
  fresh pre-recovery and original backups.
- Only the established six adjacent loader-RAM metadata bytes
  `[0x403a,0x4040)` are excluded. No verification exception or relaxed rule was used.
- The native journal/history is verified, stock-upload qualification refreshed,
  custom applied-lens history cleared and firmware observation published as
  1.8.0. The successful read connection's marker was cleared by the service;
  the armed upload-connection marker remains retained. No marker was bypassed.

Post-recovery full flash SHA-256 is
`862ae4577fea347cf5fe94344028bb29e3856f787876a8550d814d0d8bba23da`.
A separate bytewise round-trip check confirms all 131,072 bytes match the stock
snapshot taken immediately before AF 2.8 installation. This is not equality
with the untouched initial original source: the protected saved-motion record
from earlier camera use is deliberately preserved. The original complete
application slot and known metadata are nevertheless exact.

The stock USB restoration gate is complete. USB equality establishes restored
bytes, not camera AF, optical sharpness or exposure accuracy. No stock camera
test has occurred after this restoration.

Raw logs, pre/post backups, journals, unit identity and recovery paths remain
private. Sanitized evidence is in
[the transaction record](stock-18-af28-recovery-2026-10-12.json). Private logs
are retained under ignored `artifacts/private/af28-recovery-2026-10-12/`.
