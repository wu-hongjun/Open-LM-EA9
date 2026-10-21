# Factory/upstream qualification audit

See [audit](../../../../docs/audits/astra-51-factory-qualification-2026-10-20.md).
This lane contains no production overlay. The small probe extracts the exact
AF3.9 stillness helper and checks a synthetic late-arrival counterexample,
postdrive fixed-anchor drift rejection, clock wrap and signed extremes.

```sh
python3 firmware/upstream-hardening/followup/51-factory-qualification/probe.py --output artifacts/private/astra51-policy-new
```

Use a new output directory. All49 baseline sources, image, manifest and upstream
main reference are verified. Clang ASan/UBSan are required. The test does not
execute the complete homing routine or emulate hardware. Existing original-stock
instruction evidence is reused from pinned lane47, not silently regenerated.
