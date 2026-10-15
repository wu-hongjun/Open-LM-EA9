# Lane 25 — diagnostic cohorts and semantic trust

This is an offline **host decoder proposal**, with no firmware changes. Root owns
integration. All fixtures are synthetic; none is a real-unit corruption report.

Run from the repository root, choosing a fresh output directory:

```sh
python3 firmware/upstream-hardening/followup/25-diagnostic-cohorts/run.py \
  --output artifacts/private/astra-25-cohorts-repeat \
  --build artifacts/private/absolute35a
```

The runner pins the exact published 3.2–3.5 images/manifests, source-binds and
compiles the production v1/v2 trace serializer under ASan/UBSan, generates
multiple-boot histories, and compares the frozen public decoder with the staged
proposal. It runs both existing decoder boundary suites against the staged
proposal, adding the new module to their copied dependencies. Changed-source
negative controls must fail before diagnostics are interpreted.

`apply.py` installs `cohorts.py` as `scripts/startup_diagnostic_cohorts.py` and
adds one call at the existing parser's return boundary. It also updates the
copied-module lists in the two existing decoder tests, when present. The
applicator requires frozen registry script SHA-256
`e01c4b210577a22eec7cacd535a29ef31a272214247780e4432f7c958895ede8`
and refuses the shared repository: apply to a staged copy, review, and let root
integrate the resulting files. `proposal.patch` is the same four-file host-only
change, ready for root review and `git apply`. `frozen_registry.py` is the byte-identical public
baseline for failing controls, not a second installed decoder.

CRC validity remains visible through existing page fields. New `recordTrust`
and `semanticIssues` distinguish writer-consistent, inconsistent and unassociated
records. Summary `eventSnapshotComplete` now requires the expected slot layout,
page counts and accounting; `eventSnapshotStatus` distinguishes complete,
partial and inconsistent. Intact event pages with a damaged summary remain
visible as unassociated. A missing/torn event page leaves the usable summary and
other surviving events visible as partial. V1's repeated flushes stay supported.

A CRC and source-consistency checks cannot authenticate data, establish event
chronology across counter wrap, prove physical execution, verify an installation
or qualify camera behavior. Immutable-prefix diagnostic matching remains a
separate read-only exception, never a replacement for strict installation checks.
See [the audit](../../../../docs/audits/astra-25-diagnostic-cohorts-2026-10-15.md).
