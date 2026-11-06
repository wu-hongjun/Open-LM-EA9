# November upstream camera trial

This is a local build of [upstream `e054db9`](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/commit/e054db90cfae5d67fac67a7e0db4bb100f5893ae),
the November 6 snapshot of `main` after the upstream `v2.0.0` tag. It removes
the `0x2B` re-identification response and declaration. The intervening updates
also change optical-data handling, focus commands and motion reporting.

The camera version remains upstream's 2.0 and the optics remain the original
50 mm, nominal f/1.8, lens ID 50496. The macOS uploader labels the loader metadata
4.2.0 to distinguish this exact image from the project's existing 2.0.0 image.
The adapter cannot read the lens's physical aperture. No local AF changes or
lens profile patches are applied. This build has not been qualified on the A7C II.

| Artifact | Identity |
| --- | --- |
| [Upload image](upstream-november-trial.bin) | 20,480 bytes, SHA-256 `2a11822d47672355455dc4415db95f1487527e4f9865270ea368f24fc0ceaa7b` |
| [Manifest](manifest.json) | Exact source, build and layout pins |
| [Compatibility patch](compatibility.patch) | DFP startup spelling and ROM limit |

The normal `-O2` build exceeds the region reserved before the retained stock
data. The local release uses `-Os`, retaining `-O2` for the UART, EIC, encoder,
motor and servo units. The release logging code is compiled out. The linked
image is 19,716 bytes and ends at `0x9d04`; the padded transfer spans
`[0x5000,0xa000)`. No upstream protocol, optical or motion source was edited.
Two clean builds match; the upstream host suite and the native test suite pass.

Reproduce using the [pinned builder](../../../scripts/build-upstream-november-trial.py),
the pinned ARM toolchain/DFP/CMSIS and a Git checkout containing `e054db9`:

```sh
python3 scripts/build-upstream-november-trial.py --checkout CHECKOUT --output artifacts/private/upstream-november-rebuild
```

The signed native CLI has a dedicated `prepare-upstream-november` and
`apply-upstream-november --idle` path. The trial accepts only the bundled digest,
retains same-unit stock qualification, and checks that the fresh backup can
restore original stock before START. It has no ordinary install button. After
upload, physically reconnect the same adapter with the USB cap and run
`verify --idle` before camera use. [Original stock recovery](../../recovery/stock-1.8.0/README.md)
and [prior verified restoration](../../../docs/evidence/stock-18-af41-recovery-2026-10-21.md)
remain available.
