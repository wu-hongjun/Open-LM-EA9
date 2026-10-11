# Original Techart LM-EA9 1.8.0 recovery bundle

This bundle preserves the vendor application and the complete original backup
for the owner's adapter. The owner described the official update as **0.1.8**;
the cached vendor image and USB loader identify **1.8.0**, with camera version
byte `0x18`. This bundle is an original stock restore source.

- `application.bin`: the original 20,172-byte vendor image at `0x5000`, recovered
  from TECHART Update's download cache and matched byte for byte against two-pass
  adapter readback. SHA-256:
  `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
- `original-unit-backup.aesgcm`: encrypted ZIP containing the exact original six
  `.ea9backup` files, including the 128 KiB flash dump, START metadata, upper
  flash copy/prefix, factory snapshots and same-unit manifest. AES-256-GCM
  authenticates the archive; the 32-byte key is stored separately outside Git.
- `recovery.json`: version, provenance, sizes and checksums without a unit serial.

The full original flash SHA-256 is
`1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`.
The AES file is eight ASCII bytes `EA9REC01`, a 12-byte nonce, and ciphertext
including the 16-byte authentication tag. AAD is defined in the unpack tool.

The repository is public. Encryption retains the exact same-unit recovery data
without publishing device identifiers or factory-specific snapshots. The key is
not embedded in the app or committed. Its canonical local location is
`~/Library/Application Support/org.openlmea9.prototype/RecoveryKeys/stock-1.8.0.key`;
a second private copy is retained with the recovery-archive evidence. Preserve
the key separately when backing up or moving the project. The unencrypted
original backup also remains in the app's private USBBackups directory.

## Verify or recover a private backup

From the repository root, public file checks require only Python:

```sh
python3 tools/recover_stock_backup.py verify
```

To unpack, use Python 3.9+ and the tested cryptography dependency in a virtual
environment. Choose a new output directory whose parent already exists:

```sh
python3 -m venv .venv-recovery
.venv-recovery/bin/python -m pip install -r tools/recovery-requirements.txt
.venv-recovery/bin/python tools/recover_stock_backup.py unpack \
  --key "$HOME/Library/Application Support/org.openlmea9.prototype/RecoveryKeys/stock-1.8.0.key" \
  --output /path/to/NEW.ea9backup
python3 tools/verify_macos_backup.py /path/to/NEW.ea9backup
```

Unpacking opens no USB device. It authenticates the ciphertext, limits archive
entries and sizes, verifies every original file digest, stock application,
bootloader, version and flash geometry, then publishes private files. Incorrect
keys, altered ciphertext and existing destinations are rejected. The restored
manifest retains the original serial so the native uploader can enforce same-unit
restoration. It must not be used as a generic backup for another adapter.

The app's Restore Stock action can select the unpacked `.ea9backup`. The CLI
equivalent is below; perform it only when restoring stock is intended, after
closing TECHART Update and physically reconnecting the USB cap:

```sh
dist/ea9ctl restore-stock /path/to/NEW.ea9backup --idle
# Physically unplug and reconnect the USB cap after upload completes.
dist/ea9ctl verify --idle
```

The native restore writes `[0x5000,0x20000)` and original START metadata, preserving
the retained upper flash content as well as the main application. The short
`application.bin` alone is insufficient for exact restoration of the legacy
upper-row changes. Bootloader, fuse and calibration writes are not performed.
Stock upload/readback passed earlier on this adapter; AF-to-stock and interrupted
transfer/power-loss recovery remain physically unqualified. See the
[AF installation/restoration runbook](../../../docs/af-s-test.md).

The vendor binary is attributed to Techart and is not covered by the custom
firmware's MIT license. It is committed at the owner's request for restoration.
