# Prospective readiness replay preserving the production home gate

The historical lane50 runner hardcodes `HOME_GATE_OPEN()` to 1 while extracting
production functions. This wrapper preserves the complete source conditional
instead. It hash-binds the historical runner, fixture and 4.1 compatibility inputs,
and executes a modified copy in memory. It changes no frozen runner, release pin,
master, image or candidate source.

```sh
python3 firmware/upstream-hardening/followup/57-validation-gap/test.py \
  --output artifacts/private/astra57-fresh-validation \
  --receipt artifacts/private/astra57-fresh-validation/sanitized.json
```

The exact frozen 4.1 source must pass. The historical runner must reproduce its
false green for a private source mutant closing the gate; the corrected runner
must reject that mutant at the existing readiness assertion. Compiled and preprocessed checks
exercise the production macro at delays 0 and 25, including wraparound. The source
mutant uses a private altered manifest only for the host component runner; its
binary is not rebuilt, and it cannot pass the frozen image acceptance master.

`results.json` is the sanitized recorded result, including source/script hashes.
The wrapper remains prospective until a future master explicitly adopts it.
This repair does not remove the other lane50 peripheral/clock substitutes and
does not qualify hardware, capture, shutdown, or watchdog/NVM timing.

See [Astra57 audit](../../../../docs/audits/astra-57-validation-gap-2026-10-23.md).
