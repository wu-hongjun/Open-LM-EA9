# AF 3.9 offline regression acceptance

Run the final acceptance against a complete private build, using a fresh output
path whose parent exists:

```sh
python3 scripts/test-upstream-homing.py --build artifacts/private/homing39a --output artifacts/private/recheck39-tests
```

`test-inputs.json` binds the exact 3.9 image and manifest, fourteen unchanged
historical Python templates, the compatibility helpers and the private fixture
adapter. `contract-fixtures.json` pins six historical C fixtures independently.
`replay.py` retains the reviewed 3.7 binder, replacing only candidate version,
immediate-base identity and the explicit local adapter call. Frozen source
controls and designated failing mutants remain in their historical runners.
Historical sources and published receipts are never rewritten.

The private fixture adapters retain the accepted 3.8 operand-query and phase-ID
contracts. For 3.9 they additionally separate test scheduling from ADC telemetry:

- Query-flow still enters and exits pump depth exactly once and injects the same
  homing queries. Its former ADC mock body runs from an explicit pump-exit hook;
  the depth decrement sits outside the release logging preprocessor guard.
- Time-contract and target-time-composition retain their synthetic clock,
  VD/RX, predictor-observation and deadline injection bodies, called once from
  pump exit for both frozen controls and the candidate. ADC mocks become inert.
- Query-composition retains its pump count independently of ADC. Unused ADC
  reset/result mocks in time and home fixtures are annotated locally, preserving
  compiler warnings for all other functions.
- The weak motion-data fixture returns aligned writable storage for the new
  failure-only home snapshot. Dedicated lanes45/46 exercise the real collector;
  these weak hooks cannot override linked production implementations.

No deadline, readiness, cutoff, read-count, wire-value or negative-control
assertion is removed for the ADC change. Scheduling hooks exist only in private
extracted test bodies. They model supplied hardware schedules and do not measure
real peripheral or interrupt timing.

The master runs all fourteen historical suites; exact-candidate home45,
shutter-readiness46 and release-ADC48 checks; retained capture43 and shutdown44;
trace and compaction; ARM reset and writer instructions; legacy/v3/phase/home
snapshots and adversarial decoding; registry checks for 3.7, 3.8 and 3.9; the
compiled composition audit; and the preservation ledger. Private writer/shutdown
copies admit version 3.9 without changing assertions. Hash-bound private factory
and compaction copies omit only their historical runners' duplicate public
receipt writes; all controls and private outputs remain. Image, all 49
production source hashes and test inputs are checked before and after acceptance.

`--skip-compiled` is available for intermediate integration only. It emits
`partial39-offline-compiled-audit-skipped`, never final acceptance. Full acceptance
requires the compiled audit and preservation checks to pass. Passing offline
checks does not establish a physical homing, shutter-block or camera-freeze fix.
No device inventory, transport, updater, application or motor is accessed.

## Build reproduction

The prerequisite is the exact frozen 3.8 materialization at
`artifacts/private/readiness38-repeat`. If it is missing, use the
[3.8 reproduction recipe](../next38/README.md) to create it at that path, including
its documented 3.7 prerequisites. Then build and test in fresh private directories:

```sh
python3 scripts/build-upstream-homing.py --output artifacts/private/recheck39
python3 scripts/build-upstream-homing.py --output artifacts/private/recheck39-repeat
cmp artifacts/private/recheck39/contax-zeiss-50-f1-4.bin artifacts/private/recheck39-repeat/contax-zeiss-50-f1-4.bin
cmp artifacts/private/recheck39/manifest.json artifacts/private/recheck39-repeat/manifest.json
python3 scripts/test-upstream-homing.py --build artifacts/private/recheck39-repeat --output artifacts/private/recheck39-repeat-tests
```

The builder verifies all 49 frozen source pins and applies the accepted
lanes45→46→48 composition. It retains the 256-byte minimum code/data margin and
the blank 1 KiB diagnostic tail. The published candidate image and manifest must
reproduce exactly. Compiled acceptance separately checks normalized instruction,
symbol and program-header output when build-path-dependent ELF/map container
hashes differ. No size floor, source pin or diagnostic reservation is relaxed.
