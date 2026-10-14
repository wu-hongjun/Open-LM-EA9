# AF 3.0.0 — Contax Zeiss 50mm f/1.4

**Upload finished; physical reconnect/strict verification pending; camera unqualified.**
The October 14 [installation record](../../../docs/evidence/af-30-upload-2026-10-14.md)
retains the fresh backup and successful offline upload audit. This image was
prepared and tested offline on October 13. This candidate
adds factory-derived capture interlocks and raw opener echo, prioritizes shutdown
without starting new motion, and services bounded homing in foreground steps.
Cancelled acquisition can resume only on a fresh motion request, within a
per-boot two-attempt budget; faults remain sticky. AF 2.9 remains held after its
capture/shutdown failure. Keep this image off the camera until reconnect
verification succeeds; camera testing is coordinated separately.

| Property | Value |
| --- | --- |
| Loader / camera | 3.0.0 / BCD 0x30 |
| Application / profile | `[0x5000,0xa000)`, 20,480 bytes; profile at `0x9f00` |
| Declared / actual aperture | Fixed nominal f/1.4 / Unknown, physical ring only |
| Image SHA-256 | `a2ec81cd87be9142da1d4caec3968afff810bfc51e25ebc214f5532b51783b03` |
| Template SHA-256 | `2cc7b512d9d78c3d39eee8d67589a99e8d8ffa97a302819399833f8c5a1da038` |
| Profile SHA-256 | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340` |
| Flash margin / static RAM / stack | 392 / 2,380 / reserved 8,192 bytes |

See [implementation and remaining limits](../../../docs/evidence/af-30-candidate-2026-10-13.md),
[validation](../../../docs/evidence/af-30-validation-2026-10-13.json),
[build inputs](../../../docs/evidence/af-arbitrated-build-manifest-2026-10-13.json),
[image manifest](contax-zeiss-50-f1-4.manifest.json) and
[camera runbook](../../../docs/af-s-test.md).

25 new arbitration/readiness cases pass with 8 detected frozen-2.9 defects;
40 retained link cases and 51 Swift tests pass. Full firmware, original-instruction
and retained controller/queue/query/telemetry checks pass. Native and Python
preparation produce this exact image. This does not establish a resolved camera
freeze, optical AF or factory parity. Real IRQ timing and stack high-water remain
unmeasured. The full factory phase machine and saved-origin policy are not ported.

App 0.13.0/build 16 and explicit `prepare-af`/`apply-af` select 3.0. Normal lens
changes preserve the verified installed variant. Older template/image and stock
recovery bytes are preserved. Reproduce from the repository root:

```sh
python3 scripts/build-firmware.py --variant arbitrated-af
scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
python3 scripts/test-capture-arbitration.py --output /new/arbitration
python3 scripts/test-home-readiness.py --output /new/readiness
python3 scripts/test-camera-link.py --output /new/link
# Use the pinned Unicorn environment:
tools/rea-analysis/venv/bin/python scripts/investigate-capture-boundary.py --output /new/capture
scripts/build-macos-app.sh
# Isolated local state and new output paths; no USB reports:
dist/ea9ctl --state-directory /new/state prepare contax-zeiss-50-f1-4 /new/profile.bin
dist/ea9ctl --state-directory /new/state prepare-af contax-zeiss-50-f1-4 /new/native.bin
python3 scripts/prepare-af.py /new/profile.bin /new/python.bin
cmp /new/native.bin /new/python.bin
```

Choose writable new paths; output parents must exist for native preparation.
Full Git history containing `1043bad` and `8996e3c` is required for exact frozen
controls. No USB operation is needed to build or prepare. Upload requires a
fresh same-unit backup, journal, physical reconnect and strict verification.
