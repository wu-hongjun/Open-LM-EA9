# Stock 1.8.0 application semantics, reproduced offline

This is an independently authored C11 host reconstruction of **38 factory
application routines**. It compares declared arithmetic, RAM updates, return
values and ordered external-action events against the retained official Thumb
instructions. It is neither a complete factory reconstruction nor a replacement
or flashable firmware. It has no USB, HID, device enumeration, updater, MMIO or
flash-writing interface.

The model sources and finite scenarios are preserved from the earlier local REA
study. `stock_model.c` and `stock_model.h` are byte-identical to that study's
authored versions. The Python harness is promoted with only input/output,
dependency and host-library build changes; original scenario logic is retained.
`provenance.json` records the earlier source digests. The full run emits digests
for every current source and result report.

## Reproduce

Use Python 3.9+ and an existing C11 compiler (`clang` by default, or an executable
selected by `CC` / `--compiler`). The harness builds a shared library using
`-dynamiclib` on macOS or `-shared -fPIC` on Linux. macOS execution is recorded in
the dated evidence; Linux command handling is implemented but not validated in
that run. Windows is unsupported.

From the repository root, create a virtual environment in a location of your
choice, then use its Python:

```sh
python3 -m venv /tmp/ea9-stock-model-venv
/tmp/ea9-stock-model-venv/bin/python -m pip install -r research/stock-1.8/requirements.txt
/tmp/ea9-stock-model-venv/bin/python tools/test-stock-model.py
/tmp/ea9-stock-model-venv/bin/python research/stock-1.8/run.py
```

The default oracle is the already committed
[`application.bin`](../../firmware/recovery/stock-1.8.0/application.bin), exactly
20,172 bytes at original address `0x5000`, SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
An explicit `--firmware /path/to/application.bin` must match the same size and
digest; it cannot change the supported oracle. No private backup, keys,
calibration, serial number or per-unit settings are needed.

Without `--output`, the runner creates a unique temporary directory and prints
its location. To retain results, select a **new** directory under an existing
parent. Existing directories, including empty ones, are rejected:

```sh
/tmp/ea9-stock-model-venv/bin/python research/stock-1.8/run.py \
  --output /tmp/ea9-stock-model-new-results
```

The complete run must pass 8,882 core cases/steps, 5,900 protocol/metadata cases
and 10,209 application cases/steps: **24,991 total**. It writes
`validation.json`, `protocol-validation.json`, `application-validation.json`
and `reproduction.json`, plus host libraries and negative-control sources. The
input file is read only and checked again after validation. Python optimization
(`-O` / `PYTHONOPTIMIZE`) is rejected so fixture assertions cannot disappear.
The runner requires the pinned Unicorn 2.1.4 dependency. This suite includes
the intentionally wrong 16,384 sensor wrap and the in-memory metadata-immediate
mutation; both must expose the expected mismatch/dependency behavior. These
mutations never alter the retained vendor file or the authored model sources.

## Evidence contract

The model preserves all 2,048 synthetic RAM bytes, including unrelated fields.
Pure-result entries also compare return values; selected driver and service
calls compare ordered events. Core/protocol/application suites compose through
imports, so run `run.py` to configure all three once. The model API accepts
original routine addresses and explicitly bounded RAM offsets; the header's
44-byte settings structure is documentary and checked at compile time.

The zeroed `stock_init` state is synthetic, not factory startup. All settings
restore records are generated synthetic bytes, never original unit settings.
The event sink must only record events and must not mutate model RAM during a
call. Host frame guards require lengths 4–255 and valid SRAM pointers; they are
not checks performed by factory firmware. PID uses factory denominator 200 and
normal positive floor/clamp parameters; original divide-by-zero semantics are
outside the contract.

Original Thumb instructions execute with Unicorn's Cortex-M0 selection. Stop
register instructions use dummy RAM-backed pages. Four final motor driver calls
are recorded stubs; timer/DMA/NVM/delay/UART and critical-section boundaries are
also explicit stubs where required. NVM stubs return `-7`, which the application
callers ignore. Main scenarios hold a sensor sample fixed during each call,
hold PA3 low at both shutdown reads, and explicitly supply wake by skipping WFI
after recording an event. Arbitrary interrupt ordering, held-high polling,
sleep/wake hardware, transport, flash failure behavior, actual movement and
physical timing are not reproduced.

Unicorn accepted a Thumb-2 MOVW control despite the selected Cortex-M0 model in
the earlier study. Passing instruction comparisons therefore does not prove
ARMv6-M instruction legality, electrical behavior, whole-program equivalence or
complete firmware reconstruction. See the [semantic coverage dossier](../../docs/reverse-engineering/stock-host-model.md)
and [whole firmware ledger](../../docs/reverse-engineering/whole-firmware-reconstruction.md)
for routine provenance and the wider remaining work.

## Attribution and licenses

The host C model and harness are independently authored analysis implementations
derived from observed official 1.8.0 instruction behavior, not recovered vendor
source or a copy of the upstream experimental AF controller. The repository
currently states no separate license grant for these research sources; the MIT
license under `firmware/ea9/` applies to that firmware source and is not a vendor
binary license. The oracle is Techart's official application, retained under the
[recovery bundle's attribution](../../firmware/recovery/stock-1.8.0/README.md).
No vendor source license or redistribution rights are inferred from analysis.
Unicorn is a separately installed dependency under its own license.

## October 12 extension

The independent [sensor/origin extension](extensions/2026-10-12/README.md) adds
three new bounded entries without changing this 38-entry model. Its 68,648
cases/steps and four guards use synthetic inputs, original Thumb instructions
and explicit lower peripheral cuts. The union is 41 application routine models;
these overlapping finite counts provide no whole-firmware coverage percentage.
