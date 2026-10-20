# Astra47 — factory origin and optional arithmetic measurement

No homing or sensor initialization remedy is established here. Tests run only
original instructions with synthetic input and extracted production arithmetic.
All 49 AF3.8 source pins and its published manifest are verified before tests.

From the repository root:

```sh
tools/rea-analysis/venv/bin/python firmware/upstream-hardening/followup/47-factory-origin/run_factory.py --output artifacts/private/astra47-factory-new
python3 firmware/upstream-hardening/followup/47-factory-origin/run_size.py --output artifacts/private/astra47-size-new
```

Use fresh output names. The first runner requires the pinned Unicorn2.1.4 REA
environment; the second uses local Clang sanitizers and the pinned build's ARM
compiler flags. Neither opens hardware. See the [audit](../../../../docs/audits/astra-47-factory-origin-2026-10-20.md).

`apply_size.py` is an **optional**, separate 48-byte arithmetic optimization,
not a homing fix. It computes an unsigned magnitude after signed ordering,
preserving the old int64 threshold predicate for every int32 coordinate pair.
The exact source fragment and tracker pin must match. The current release
composition is the root integrator's decision; the existence of this applicator
does not mean it is included. `size-results.json` measures it alone on AF3.8.
The earlier signed narrowing experiment was rejected because corrupted retained
tracker values lie outside its arithmetic guarantee.

`factory-results.json` records 24 bounded cases and six rejected incorrect
interpretations. These are supplied-state observations, not full boot/peripheral
or camera equivalence. `size-results.json` records 6,898,454 differential checks,
actual tracker guard controls, two failing arithmetic mutants and linked size.
