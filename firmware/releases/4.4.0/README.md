# 4.4.0 fallback

Known upstream-based fallback, retained byte-for-byte. It declines the `0x0C`
speed offer and stays at 750 kbaud with native lens ID `0xC540`. The compiled
profile is the original upstream 50mm f/1.8. The owner reported AF in stills
and video and successful manual stop-down use on the A7C II.
[Camera record](../../../docs/evidence/upstream-stock-speed-44-2026-11-06.md).

The application is 20,480 bytes at `[0x5000,0xa000)`, SHA-256
`cf442fa02e4854914b602b4646c689984e9b12de2595adf20a0a1cebaa738a27`.
Its image, manifest and patches are unchanged. The original build and replay
pipeline remain under `archive/pre-4.5-baseline`; active development uses the
[working 4.5 sources](../../src/).

Native fallback admission accepts exact original stock, 4.5 or 4.6 after the
existing qualification and fresh backup. Physical reconnect and complete-image/
protected-data verification remain mandatory. The daily UI offers working 4.5
and the separate 4.6 candidate; this fallback is available through the explicit
native CLI, not an experimental install panel.
