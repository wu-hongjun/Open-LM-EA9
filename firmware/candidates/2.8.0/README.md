# AF 2.8.0 — Contax Zeiss 50mm f/1.4

**Prepared and tested offline; not uploaded or camera-qualified.** This candidate
separates observed movement from command completion, target prediction and Stop.
It restores the REA factory frame-sync writer's equal current/ahead positions.

| Property | Value |
| --- | --- |
| Loader / camera | 2.8.0 / BCD 0x28 |
| Application / profile | `0x5000..<0xa000`, 20,480 bytes; row at `0x9f00` |
| Lens / declared aperture | Contax Zeiss 50mm f/1.4 / fixed nominal f/1.4 |
| Actual iris | Unknown; use the physical ring |
| Template SHA-256 | `ac9302fd329ab59b0e47efa5bbcf3e3b0b72de4e3e2033febf006c518ba6a0cc` |
| Personalized SHA-256 | `81f959c0b19fb222ee39b49eb7505882c30b25cb765c643e3f33daadf8e92834` |
| Profile SHA-256 | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340` |
| Flash headroom / static RAM / stack | 400 bytes / 2,200 bytes / reserved 8,192 bytes |

A pure measured observer retains motion through coast and reversal. Rest needs
a fresh quiet interval at four-count resolution, while stale sampling/VD is
internally unknown and uses the existing moving/just-stopped wire fallback.
History is discarded after a gap/reference reset and seeded on the first resumed
VD before a later full interval can append a delta. Slow cumulative displacement
survives quiet frames; sub-resolution boundary jitter does not hold motion forever.

[Implementation, REA evidence and limits](../../../docs/evidence/af-28-motion-telemetry-2026-10-12.md),
[independent audit](../../../docs/audits/af28-motion-telemetry-review-2026-10-12.md),
[finite regressions](../../../docs/evidence/af-28-regressions-2026-10-12.json),
[build inputs/layout](../../../docs/evidence/af-observed-build-manifest-2026-10-12.json),
[image manifest](contax-zeiss-50-f1-4.manifest.json), and
[separate camera runbook](../../../docs/af-s-test.md).

The pure factory controller, wrapper, drivers, aperture and completion law are
unchanged from 2.7. A completion/Stop acknowledgement still does not prove
physical rest or optical lock. Noise of four or more counts, sub-resolution
motion, physical settling and camera consumption are unqualified. This is not
factory parity or production firmware.

App 0.11.0/build 14 and explicit AF preparation/install select 2.8. Normal Device
profile changes preserve the verified installed variant. All older resources
and stock recovery remain unchanged. No hardware operation occurred; flashing,
physical reconnect and byte verification will be coordinated separately.

```sh
python3 scripts/build-firmware.py --variant observed-af
scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
tools/rea-analysis/venv/bin/python scripts/test-observed-candidate.py --output /new/af28-results
tools/rea-analysis/venv/bin/python scripts/test-stock-motion-reporting.py --output /new/stock-motion-results
scripts/build-macos-app.sh
# New output paths, existing parent directory, isolated local state:
dist/ea9ctl --state-directory /new/state prepare contax-zeiss-50-f1-4 /new/metadata.bin
dist/ea9ctl --state-directory /new/state prepare-af contax-zeiss-50-f1-4 /new/native50.bin
python3 scripts/prepare-af.py /new/metadata.bin /new/python50.bin
cmp /new/native50.bin /new/python50.bin
```

Unicorn must use the repository's pinned dependency. Full Git history containing
`7efac6b`, `d023745` and `6d84407` is required for frozen controls. Outputs must
be new directories/files; no retained source/evidence is overwritten.
