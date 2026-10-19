# AF 3.8 offline readiness composition

Build [3.8](../../candidates/3.8.0/README.md) from the exact frozen 3.7
materialization at `artifacts/private/targeted37-repeat`. If missing, follow the
[3.7 prerequisites](../next37/README.md) and reproduce it at that path first.
The pinned compiler, 23 translation units, flags, linker bounds and dependency
archives remain unchanged. Production applicators run in order: lane42 query
liveness, lane42 phase labels, then version `0x37` to `0x38`.

Use fresh private output directories under existing parents:

```sh
python3 scripts/build-upstream-readiness.py --output artifacts/private/recheck38
python3 scripts/test-upstream-readiness.py --build artifacts/private/recheck38 --output artifacts/private/recheck38-tests
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

The builder pins all 49 base source files, manifest, patch and host shim. It
hash-binds both applicators in `accepted-lanes.json`, enforces code plus
initialized data and the 256-byte minimum margin, checks vectors/RAM/stack and
requires an erased 1 KiB diagnostic tail. Existing published 3.8 bytes must
reproduce exactly. Later behavioral changes need a new version.

`replay.py` reuses the frozen 3.7 binder. `test-inputs.json` and
`contract-fixtures.json` separately pin templates and the four historical C
fixtures. `contract_adapters.py` creates private copies with explicit changes:

- Operand-only queries may answer under motor inhibition; shutdown, session,
  abort, checksum, queue and answer-value checks remain. Frozen baseline
  expectations and failing controls remain separately enforced.
- The coordinate-abort composition still requires abort, inhibition and exact
  endpoint/read counts. One explicit foreground query pump checks the new
  live-query behavior while readiness remains false.
- Homing deadline tests expect drive/settle failure codes rather than generic
  code 11. Existing deadline, shared-work and cutoff assertions remain.

These are intentional contract updates, not baseline bug counts. The first
unadapted replay exposed those changed expectations; production source was not
changed to satisfy old inhibit-based query rejection. Dedicated lane42 controls
reproduce starvation on frozen 3.7 and on both half-fixes.

All final source hashes and test-input hashes are checked before/after
acceptance. Production protocol modules, extracted exact foreground/homing
functions, compiled ARM reset/writer instructions, synthetic peripheral
boundaries, ASan/UBSan and negative controls cover complementary finite paths.
Private copies add 3.8 to the frozen writer/registry tests without editing their
original files. Another private copy suppresses only the historical compaction
runner's duplicate public receipt write, preserving its private output and
checks. Prior public evidence is not overwritten.

`compiled_audit.py` uses the unchanged reviewed 3.7 graph analyzer. It checks
49 source files, all callback targets, vectors, library stack operations,
terminal/wait instruction operations, NVM caller gates and the three-file
applicator composition. `compiled-policy.json` stays frozen. For builds at a
new path, `stack-reproduction.json` permits changing only ELF/map container
hashes after exact raw/image/manifest and normalized objdump instruction,
symbol and program-header hashes match. Normalization removes only the input
ELF path. The objdump executable is pinned. A supplied policy cannot change
any graph edge, frame estimate or other pin. Unknown edges and recursion fail.
The 1,516-byte envelope is conditional on the documented boot/IRQ assumptions;
physical stack usage and interrupt/peripheral timing remain unmeasured.

The app must stay closed during offline work because refresh enumerates USB.
Native prepare-only commands use isolated private state and exit before device
inventory. A CLI state-directory flag does not isolate the canonical USB safety
guard and is not permission to run transport commands. No script here launches
the updater, opens an adapter, flashes, clears a guard or drives a motor.

[Integrated evidence](../../../docs/evidence/upstream-38-readiness-2026-10-19.md) ·
[Astra42](../../../docs/audits/astra-42-home-readiness-2026-10-19.md) ·
[Astra43](../../../docs/audits/astra-43-capture-status-2026-10-19.md) ·
[Astra44](../../../docs/audits/astra-44-shutdown-liveness-2026-10-19.md)
