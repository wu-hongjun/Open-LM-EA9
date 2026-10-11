# Reviewed stock restoration after camera use

October 11, 2026. This explicit recovery path handles the owner's stock 1.8
comparison, where the camera was used before the USB restore readback. It is
separate from normal upload verification and runs only when requested through
the CLI. It does not alter `VerificationEngine` or clear a blocked connection.

The [original comparison record](evidence/stock-18-comparison-2026-10-11.md)
retains the strict failure: 13 bytes changed in recovered stock motion fields,
while the full original application slot and protected/factory data matched.
Stock's save routine copies its live motion/settings record to flash; this is
consistent with the observed changes, but that physical save call was not traced.

`ea9ctl resolve-stock-after-camera REVIEWED.ea9backup --idle` requires an
uploaded, unverified, pinned stock 1.8 restoration journal; a validated two-pass
reviewed backup taken after upload; and a newly reconnected copy of the same
adapter. The normal exclusive lock, closed-updater check and persisted reconnect
guard still apply. The command sends CHECK/READ only and saves a fresh two-pass
full-flash/auxiliary backup. It sends no START or PAGE reports.

The fresh flash must match the reviewed flash **in its entirety**, the restored
`0x5000..<0x20000` slot must equal the journal's pinned stock image, boot code
must equal the pre-restore backup, and all 58 known START metadata bytes must
match. The pre-restore gap must remain exact except for this explicit list:

| Addresses (end exclusive) | Recovered motion role |
| --- | --- |
| `0x4100..<0x4102` | Latest raw encoder sample |
| `0x4106..<0x4108` | Protocol position |
| `0x410c..<0x4110` | Relative position |
| `0x4110..<0x4112` | Velocity delta |
| `0x4114..<0x4116` | Target |
| `0x411c..<0x411d` | Latched direction |
| `0x4120..<0x4122` | Timeout count |

This is not an exception for all 44 record bytes. Origin/reference, focal
configuration, park/menu settings, enable/completion flags, unknown padding and
every other gap byte must remain exact. User row, calibration and device ID
must match the original and reviewed backups; the NVM snapshot must match the
reviewed read. The six START bytes derived from adjacent loader RAM remain
outside the existing strict known-metadata comparison, but fresh-versus-reviewed
full-flash equality includes them.

On success, the native service publishes stock lens inspection history and
durably saves a private `RestoreResolutions` receipt containing the original
pending journal, reviewed/fresh backup paths, digests, accepted addresses and
`strictVerificationPassed: false`. Only then does it remove the active pending
pointer and synchronize the directory. The original `UpdateHistory` record
keeps `verifiedAt: nil`; it is never retroactively marked as a strict pass.
The old applied custom profile is archived. The previously qualified stock
upload record is retained; this review does not create a new qualification.

This allows a subsequent explicitly requested custom upload to take a fresh
pre-upload backup using the reviewed stock state, while preserving the failure
and all evidence. It does not write the motion record back, restore the
bootloader, or prove power-loss recovery. A mismatch leaves the pending
transaction intact and the failed-read connection blocked for physical reconnect.

The offline tests classify every byte of the 44-byte record, reject same
connections, fresh drift, outside-gap/application/metadata changes and altered
factory data, and verify durable receipt retention without marking the failed
journal verified. Existing strict upload verification tests remain unchanged.
The [AF 2.4 hardware record](evidence/af-24-upload-2026-10-11.md) reports actual
resolution/upload/readback results separately from this policy.
