# 3.1.0 — direct upstream baseline, Contax Zeiss 50mm f/1.4

**Uploaded and strictly byte-verified after physical reconnect. Not camera-qualified.**
This is the pinned upstream implementation, with documented lens configuration and build
compatibility changes. It replaces our controller and capture-scheduler work
for a clean comparison. AF 3.0 remains held after its capture/shutdown failure.

| Property | Value |
| --- | --- |
| Upstream commit | `d52ed06cc449918f938e0695fbf29a0c4141f2b2` |
| Loader / camera tag | 3.1.0 / BCD 0x31 |
| Image / range | 20,480 bytes, `[0x5000,0xa000)` |
| Image SHA-256 | `528225e6f6472da0d92479da2b3e475a32f82735347231b6dc7c3d0dc7e8b39f` |
| Fixed declared / actual aperture | Nominal f/1.4 / Unknown, physical ring only |
| Lens ID | Upstream 50496; not our previous 234 |
| Flash margin / static RAM / stack | 4,892 / 2,728 / reserved 8,192 bytes |
| Runtime lens profiles | Unsupported; fixed original 50mm f/1.4 profile |

No profile row is added to the firmware. Every image byte is pinned; the host
rejects lens edits/other profiles before USB. Metadata editing stays local for
this baseline. The original protocol, servo, homing, parking and drivers are
unmodified C sources; startup/system spelling, linker bound, version and lens
constants are the reviewed differences. The optical row scaling follows the
upstream recipe and does not measure this Contax lens's pupil geometry.

Both upstream builds pass eight host outcomes; 53 Swift tests pass, including
full-image journal validation, upload bounds, interruption/reconnect rules,
protected-region comparisons and fixed-baseline UI behavior. Signed app
0.14.0/build 17 and native preparation match this image exactly. Upstream's
Sony a9 II results do not qualify A7C II capture or shutdown.

See [all source changes](../../upstream-baseline/50mm-f1.4.patch),
[provenance](../../upstream-baseline/README.md),
[build record](../../../docs/evidence/upstream-baseline-build-2026-10-14.json),
[validation](../../../docs/evidence/upstream-baseline-validation-2026-10-14.json),
[image manifest](contax-zeiss-50-f1-4.manifest.json) and
[camera procedure](../../../docs/upstream-baseline-test.md).

```sh
python3 scripts/build-upstream-baseline.py
scripts/build-macos-app.sh
# New writable paths; preparation sends no USB reports:
dist/ea9ctl --state-directory /new/state prepare-upstream contax-zeiss-50-f1-4 /new/baseline.bin
cmp /new/baseline.bin firmware/candidates/3.1.0/contax-zeiss-50-f1-4.bin
```

The October 14 upload completed with a fresh two-pass backup and all 320 pages
acknowledged. See [the installation record](../../../docs/evidence/upstream-31-upload-2026-10-14.md).
Fresh two-pass readback and a separate offline audit passed full-image/metadata
and protected flash/factory-data checks. Initial MF capture/lifecycle testing is
requested; AF-S follows only after that cycle succeeds.
Use `apply-upstream`, not the historical `apply-af` command. Do not retry held
AF 3.0 or bypass reconnect/recovery guards to obtain a baseline.
