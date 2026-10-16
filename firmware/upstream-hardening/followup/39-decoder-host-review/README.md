# Astra 39 decoder / host review

This directory owns source-bound synthetic negative controls and the proposed decoder patch. The parent integrated `proposed_startup_diagnostic_v3.py` into `scripts/startup_diagnostic_v3.py` at SHA-256 `7662e1472dfd4db179368d46d8cff64cdb5462a587d11b66ee3dda1ee9c2cb83`.

Run from the repository root:

```sh
python3 firmware/upstream-hardening/followup/39-decoder-host-review/test_adversarial.py --output firmware/upstream-hardening/followup/39-decoder-host-review/integrated-results.json
python3 firmware/upstream-hardening/followup/39-decoder-host-review/test_registry.py --output firmware/upstream-hardening/followup/39-decoder-host-review/registry-results.json
```

The first command requires the source-produced synthetic fixture at `artifacts/private/trace35-suite8/synthetic.bin` (or pass `--fixture`), never a camera backup. Its default expected fixture hash is recorded in the audit. The second creates and deletes a disposable repository under this directory, reads only published candidate files and scripts, and generates its own blank synthetic flash image. Neither command accesses a device or canonical app state.

Baseline: 11/60 passed before fixes. Proposed and integrated: 60/60. CLI trust-boundary controls: 27/27. Complete findings and host source review are in `docs/audits/astra-39-decoder-host-review-2026-10-15.md`.
