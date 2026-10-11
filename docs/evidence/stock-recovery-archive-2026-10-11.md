# Committed stock 1.8.0 recovery source — 2026-10-11

The owner asked to commit and push all project changes and save the original
1.8.0 recovery firmware in Git. The destination is the public
[wu-hongjun/Open-LM-EA9 repository](https://github.com/wu-hongjun/Open-LM-EA9).

The [recovery bundle](../../firmware/recovery/stock-1.8.0/README.md) contains the
original 20,172-byte vendor application, matched against the updater cache and
the original two-pass adapter flash dump. It also contains an AES-256-GCM encrypted
archive of all six original `.ea9backup` files. This retains exact START metadata,
the upper flash prefix/duplicate, factory snapshots and same-unit identity for
restoration. The key is stored in the app's private RecoveryKeys directory with
a second private evidence copy; neither key nor decrypted backup is published.

Public application SHA-256:
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
Original full 128 KiB flash SHA-256:
`1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`.
Archive sizes and checksums are recorded in the bundle manifest and
[machine-readable evidence](stock-recovery-archive-2026-10-11.json).

Verification performed entirely offline:

- Original backup manifest, every file digest, loader hash and flash geometry
  passed the existing backup verifier.
- The committed application equals both the original flash application slice
  and cached official vendor image.
- The encrypted archive unpacked into a new private `.ea9backup`; every file,
  including the original manifest, is byte-identical to the original source.
- Seven [recovery checks](stock-recovery-archive-tests-2026-10-11.txt) passed:
  pinned product admission, successful unpack/private permissions, incorrect key,
  authenticated tampering, existing destination preservation, path traversal and
  duplicate archive entries. Rejected inputs publish no new backup.

No USB report, stock upload, bootloader write or camera test was performed for
this archival work. The earlier stock upload/readback result remains valid;
AF-to-stock, arbitrary interrupted-transfer/power-loss and bootloader restoration
remain physically unqualified. AF 2.2 is still awaiting physical reconnect and
readback, as recorded in [its separate upload evidence](af-22-upload-2026-10-11.md).
