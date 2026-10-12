# AF 2.7.0 — Contax Zeiss 50mm f/1.4

**Historical frozen candidate; superseded by AF 2.8 for new testing.**
The [2.8 change](../../../docs/evidence/af-28-motion-telemetry-2026-10-12.md)
corrects the retained post-completion motion-reporting gap. This original
candidate was prepared/tested offline and was never uploaded or camera-qualified. This polish
candidate fixes reproduced queue/retarget faults while preserving the audited
fixed-aperture policy and stock-derived pure controller. A known simulated
post-completion motion-telemetry gap remains open. It is not production firmware.

| Property | Value |
| --- | --- |
| Loader / camera version | 2.7.0 / BCD 0x27 |
| Application / profile | `0x5000..<0xa000`, 20,480 bytes; profile at `0x9f00` |
| Declared lens / aperture | Contax Zeiss 50mm f/1.4 / fixed nominal f/1.4 |
| Actual physical iris | Unknown; controlled by the lens ring |
| Template SHA-256 | `da4eaa0f41fe9ff5b2c896ee7d5d2526cfc8fa423f581b5f55f9a1ff3c2059bf` |
| Personalized SHA-256 | `e124d09ad3eb272fab699035ee1ff941417afa3c6dd900484e11ae44c9c890b4` |
| Profile SHA-256 | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340` |
| Initialized flash margin / static RAM | 524 bytes / 2,192 bytes |
| Reserved stack | 8,192 bytes; high-water not measured |

A Stop acknowledgement survives a full two-entry completion queue. A newer
Stop supersedes an older pending Stop and follows intervening completions.
Only changed, admitted four-count targets spend the retarget budget or restart
a leg. Repeated identical, quantized or clamped absolute destinations retain
the existing deadline and cancellation checks. Release builds omit disconnected
raw diagnostic capture/log bookkeeping; request snapshots and fault guards remain.

The camera report stays fixed in known aperture fields; opaque `0x34` preserves
the stock operand echo. No undocumented F-- sentinel, exposure bias, new optical
calibration, braking gain or factory reference transplant is introduced.

See [the overnight integration record](../../../docs/evidence/overnight-audit-polish-2026-10-12.md),
[independent review](../../../docs/audits/af27-integration-review-2026-10-12.md),
[image manifest](contax-zeiss-50-f1-4.manifest.json),
[build inputs/layout](../../../docs/evidence/af-polished-build-manifest-2026-10-12.json),
[finite regressions](../../../docs/evidence/af-27-regressions-2026-10-12.json)
and [separate installation/camera procedure](../../../docs/af-s-test.md).

At that milestone, app 0.10.0/build 13 and explicit AF actions selected 2.7.
The current app selects 2.8. Historical 2.7 personalization uses explicit Python
`--variant polished-af`; its binary and original evidence remain unchanged. The normal
Device dropdown preserves the verified installed variant. Versions 2.0–2.6,
including 2.6's original binary/pin, and stock recovery remain byte-identical.
No hardware operation occurred. Upload/reconnect verification and camera testing
must be coordinated separately; a 2.7-to-stock hardware round trip is untested.

Reproduce with the documented compiler caches and pinned Unicorn environment:

```sh
python3 scripts/build-firmware.py --variant polished-af  # Verify frozen resource.
tools/rea-analysis/venv/bin/python scripts/test-polished-candidate.py --output /new/frozen27-results
# Outputs must be new paths; parent directories must exist.
dist/ea9ctl --state-directory /new/local-state prepare contax-zeiss-50-f1-4 /new/metadata50.bin
python3 scripts/prepare-af.py /new/metadata50.bin /new/50mm27.bin --variant polished-af
```

The regressions require full Git history containing `d023745` and `7efac6b`;
frozen negative controls are materialized with per-file digest checks. Host
mechanics and original-instruction models do not establish optical focus,
exposure, electrical timing or whole-firmware equivalence.
