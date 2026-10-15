# Post-3.4 target and time composition

The [3.5 candidate](../../candidates/3.5.0/README.md) integrates the shared-start
absolute target entry, post-stillness home deadlines, exact unsigned long-gap
predictor quotient, and omission of a release-invisible legacy counter update.
The frozen `accepted-lanes.json` pins the applicators and supporting inputs.
Root owns integration; no script here accesses hardware.

The base is the exact 3.4 materialization at `artifacts/private/bounded34b`.
If absent, first reproduce the [3.4 prerequisites](../next/README.md), then:

```sh
python3 scripts/build-upstream-bounded.py --output artifacts/private/bounded34b
```

Use fresh private output paths with existing parents:

```sh
python3 scripts/build-upstream-absolute.py --output artifacts/private/recheck35
python3 scripts/test-upstream-absolute.py --build artifacts/private/recheck35 --output artifacts/private/recheck35-tests
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

The builder requires the pinned 3.4 image/manifest/sources and exact applicator
plan. It keeps the established per-unit flags, checks code plus initialized-data
load extent, at least 256 bytes before logs, RAM/vector bounds and a blank 1 KiB
diagnostic tail. It refuses any changed image under published version 3.5.
The test entrypoint covers exact source/image/resource identity, retained capture/
shutdown/query/numeric/home regressions, target/time changes with failing controls,
release/debug counter parity, compiled stack evidence/guards, compiled ARM writer,
and version/pin/page/native-manifest decoder boundaries. Native Swift tests and
signed packaging are separate. Do not launch the app during offline work because
its normal refresh enumerates hardware. Isolated prepare-only commands return
before inventory; apply/backup/verify are future coordinated hardware actions.

Fresh build directories change ELF DWARF/map path strings. The stack reproduction
record requires the exact image, raw bytes, manifest and source hashes, plus
reviewed normalized disassembly, symbol-table and program-header hashes before
rebinding only ELF/map container pins in scratch. All reviewed callbacks, library
bodies/frames, inventories, layout checks and physical caveats remain enforced.

`measure.py` is an exploratory analysis link, producing no binary image. The
home+target overlay has 256 bytes before logs; adding the predictor alone leaves
248 and fails the required margin. Omitting the legacy-only accepted-period
counter update recovers 16 bytes, yielding the final 264-byte margin and 3,072
static RAM bytes. This does not alter the real frame period or remove I/O.

The final-source time fixture injects at the first controller feedback read:
ordinal 3 for frozen 3.4, ordinal 2 after removing the redundant entry read. Its
expected outcome and wire checks are unchanged. This avoids treating an old
fixture's absolute read ordinal as a production contract. All private source
instrumentation is separate from the compiled firmware and retained originals.
