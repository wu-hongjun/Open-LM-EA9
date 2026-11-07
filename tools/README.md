# Local utilities

- `recover_stock_backup.py`: verify the preserved stock bundle or unpack it with
  the separate private key. See [recovery](../firmware/recovery/stock-1.8.0/README.md).
- `test_stock_recovery.py`: offline archive/recovery checks.
- `verify_macos_backup.py`: independently validate native `.ea9backup` packages.
- `inspect_camera_metadata.swift`: inspect an existing local photo's metadata.

Native USB operations live in `apps/macos/Sources/DeviceKit` and `ea9ctl`.
Old firmware experiments and research tools remain under the
[archive tag](../docs/history.md). Vendor build dependencies are ignored local
installs in `tools/firmware-deps`; they are not application resources.
