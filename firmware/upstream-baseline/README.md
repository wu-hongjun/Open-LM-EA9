# Direct upstream baseline

This lane builds [weiziqian/E-mount-impl-on-Techart-EA9](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9)
commit `d52ed06cc449918f938e0695fbf29a0c4141f2b2`, verified against the current remote HEAD on
October 14, 2026. It uses that repository's protocol, servo, main loop, homing,
shutdown and peripheral drivers together. Our factory-derived controller,
`em_arbitration`, reference policy and runtime lens-profile layer are absent.

**The 50mm f/1.4 image is uploaded and strictly byte-verified after physical
reconnect. It is not camera-qualified.** Fresh two-pass readback and a separate
offline audit passed. See [the installation record](../../docs/evidence/upstream-31-upload-2026-10-14.md).
Upstream documents a Sony a9 II test platform; the owner's A7C II remains an
independent compatibility check. Its latest header also labels lens ID 50496
as an experiment; this baseline preserves that value for a faithful comparison.

## Two reproducible builds

- `reference-release.bin`: as-configured upstream 50mm/f/1.8, camera tag 0x59,
  with only device-header/vector spelling and a capped linker region adapted.
  This is retained for comparison, **not admitted as an upload target**.
- [3.1.0 candidate](../candidates/3.1.0/README.md): documented lens constants set
  to 50mm/f/1.4, corresponding pupil-size row rescaled and camera tag set to 0x31.
  Its AF/protocol/driver/main C implementations are unchanged from upstream.
  Its image SHA-256 is `528225e6f6472da0d92479da2b3e475a32f82735347231b6dc7c3d0dc7e8b39f`.

`50mm-f1.4.patch` contains every source and test-fixture substitution. The
startup/system changes adapt DFP 2 header/vector member spellings. The linker
caps application ROM at `[0x5000,0xa000)`. Three aperture constants become
0x1100; slot B type 1 becomes `d2 5a c8 e1 e2 ea` by scaling the original
mantissas by the encoded f-number ratio `2^0.375`, rounding each point. This
follows the upstream recipe; the inherited optical curves are **not measured
Contax lens calibration**. Slot A, slot B type 0 and lens ID remain upstream.
One host-test row hardcodes upstream's f/1.8 descriptor twice; its configurable
copy is adjusted from 0x16 to 0x10 for the f/1.4 build. No test is removed.

Both builds use upstream's release `-O2 -DNDEBUG -DEA9_NO_LOG` configuration.
No diagnostic flash logger is compiled/linked. Upstream's recorded camera runs
used debug `-O1`; those results do not qualify this release build on the A7C II.
Their original unbounded peripheral/startup waits and homing/park behavior are
retained, along with their servo guards. This is an isolation baseline, not an
assertion that upstream has every safety/service improvement in our fork.

Run from the repository root:

```sh
python3 scripts/build-upstream-baseline.py
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

The checksum-pinned reference collection and toolchain/DFP/CMSIS versions from
`firmware/dependencies.json` must be materialized first. The builder checks the
reference catalog before compiling and leaves it immutable. Generated sources,
ELF/map files and host logs stay in ignored `build/`. All eight upstream host
suite outcomes pass for both builds. The source and tests are licensed under
[MIT](LICENSE); Microchip/CMSIS notices use [Apache-2.0](Apache-2.0.txt), with
notices included in the packaged firmware resources.

The native host treats 3.1 as a **full pinned fixed image**, including its FF
padding. It contains no `EA9LENS1` runtime profile row. Fixed 50mm/f/1.4 settings
are published only after exact image recognition; selecting/editing another
profile cannot silently alter the compiled lens. App 0.14/build 17 and
`prepare-upstream`/`apply-upstream` are explicit paths. Historical `prepare-af`/
`apply-af` still select held AF 3.0 and must not be used for this comparison.

See [implementation and validation](../../docs/evidence/upstream-baseline-2026-10-14.md)
and [the upload/camera procedure](../../docs/upstream-baseline-test.md). A fresh
same-unit backup, journal, post-upload physical reconnect and strict complete
readback remain required. Stock recovery and all older pinned images are kept.
