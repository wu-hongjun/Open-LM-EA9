# Exact 3.5 composition review

Offline tests bound to `artifacts/private/absolute35a` and its exact manifest/image.
See [audit 23](../../../../docs/audits/astra-23-composition35-2026-10-15.md) for
scope, assertions, source instrumentation, observed caller behavior and limits.

```sh
python3 firmware/upstream-hardening/followup/23-composition35/run.py \
  --source artifacts/private/absolute35a --output artifacts/private/astra23-rerun
python3 firmware/upstream-hardening/followup/23-composition35/run_counter.py \
  --source artifacts/private/absolute35a --output artifacts/private/astra23-counter-rerun
```

Output directories must be fresh. `results.json` records 40 composition checks,
seven retained relative-API probes and four expected assertion failures after
private removal of individual corrections. `counter-results.json` records four
release/debug exact-final/restored-counter comparisons, each with 17 VD samples,
34 simulated status frames and 12 in-memory live-trace pages. All source edits
and compilations occur in private scratch; no device access is used.
