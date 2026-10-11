# AF 2.3.0 — 50mm test candidate

This candidate is prepared for **Contax Zeiss 50mm f/1.4**. It enables the
upstream-derived AF controller with the modular reference/completion policies and
October 11 correctness fixes. It was installed and byte-verified on October 11 after the
owner's physical USB-cap reconnect. The owner subsequently reported eventual
loaded 50mm focus with substantial hunting. **It is not camera-qualified**.
Original stock 1.8.0 has since been restored for comparison; its complete
application matches the original backup. Strict native verification remains
flagged because stock camera use before readback changed saved-motion settings.
The owner reports much less hunting with stock. See the [2.3 hardware record](../../../docs/evidence/af-23-upload-2026-10-11.md)
and [stock comparison record](../../../docs/evidence/stock-18-comparison-2026-10-11.md).
Do not substitute this image for original stock recovery.

| Property | Value |
|---|---|
| Loader / camera version | 2.3.0 / BCD 0x23 |
| Application writes | `0x5000..<0xa000`, 20,480 bytes |
| Profile | `0x9f00..<0xa000`, CRC-protected 256-byte row |
| Lens report | 50mm, f/1.4, Contax Zeiss name, profile revision 1 |
| Image SHA-256 | `39222b5f5b232045a7599da1afc45753bb8ea0f12c338501131f49e0dcb854a4` |
| Template SHA-256 | `8996767bfc8e8625739e1c7619a54db1dd0b8da8150526b9afa4c9a490434e88` |
| Hardware reports during preparation | 0 |

The [adjacent manifest](contax-zeiss-50-f1-4.manifest.json) preserves the original
offline preparation state and identifies the exact image/profile/template;
later installation results are in the hardware record. The [build manifest](../../../docs/evidence/af-hardening-build-manifest-2026-10-11.json)
pins production sources and toolchain dependencies. The [correctness audit](../../../docs/audits/firmware-correctness-2026-10-11.md)
records counterexamples, fixes and finite test limits. The [polish record](../../../docs/evidence/software-polish-2026-10-11.md)
connects the app, native admission, image and tests.

The committed image is byte-identical to both current native `ea9ctl prepare-af`
and Python profile personalization. Reproduce from the repository root after
building the pinned current template and packaged CLI:

```sh
python3 scripts/build-firmware.py --variant hardened-af
./scripts/build-macos-app.sh
dist/ea9ctl --state-directory /new/local/profile-state prepare-af \
  contax-zeiss-50-f1-4 /new/output/50mm.bin
```

Preparation is offline and requires a new output file. Upload must be a separately
requested action using the qualified native stock-loader path, a fresh same-unit
backup and physical reconnect/readback. Startup/idle/shutdown, homing, command
response and loaded AF-S must be qualified for this candidate. Lens metadata is
an explicit report setting; the passive lens cannot supply its aperture or focus
ring positions. Factory PID, physical timing, calibrated geometry and a runtime
USB management service are not claimed by this candidate.

Retain [the exact original 1.8 recovery bundle](../../recovery/stock-1.8.0/README.md)
and its private key. The recovery bundle and released 2.0/2.1/2.2 pins are unchanged.
