# Stock application model reproduction — October 11, 2026

The existing stock 1.8.0 C11 host reconstruction now has a self-contained source
bundle under [`research/stock-1.8/`](../../research/stock-1.8/README.md). A fresh
offline run reproduced **24,991 original-instruction cases/steps across 38
routine entries**, including both existing negative controls. Ten input/output
guard regression tests passed. This verifies the declared finite host semantics;
it does **not** establish a complete factory reconstruction, flashable replacement,
physical timing or autofocus qualification.

## Input and source identity

The oracle is the already committed Techart
[`application.bin`](../../firmware/recovery/stock-1.8.0/application.bin), 20,172
bytes at original load address `0x5000`, SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
No private backup, unit serial, per-unit settings, recovery key or local updater
is needed. Its file digest remained unchanged after validation.

The promoted authored C and header are byte-identical to the earlier local REA
model: C digest `73857edba47e37670214b269770697cf5b0108ac9bf55638a24489394703f815`,
header digest `ed572052599a89e1c0c3e1597d4548fc25f8f9b3d2a635f632f6a88026f146b2`.
The application suite is also byte-identical. Core/protocol fixture differences
are limited to public pinned input selection, fresh output directories and
portable host-library builds; their scenario logic is preserved. The retained
instruction helper excludes the old private input path and unrelated standalone
experiment. Earlier ignored sources and evidence remain untouched.

[`provenance.json`](../../research/stock-1.8/provenance.json) records earlier
source identities. The [machine-readable record](stock-model-reproduction-2026-10-11.json)
pins every new bundle source, test script and result file; no generated host
library or mutated test C source is promoted as firmware.

## Fresh comparison results

The run used Python 3.14.6, Unicorn **2.1.4**, Apple Clang 21.0.0 and macOS arm64.
Compilation uses C11, `-Wall -Wextra -Werror -pedantic -O2`; macOS shared libraries
use `-dynamiclib`. Linux `-shared -fPIC` support is present but was not exercised
in this macOS run.

| Suite | Cases/steps | Observed result |
|---|---:|---|
| Core AF arithmetic, commands and composed fixtures | 8,882 | Pass |
| Protocol frames, reply dispatch and metadata/menu | 5,900 | Pass |
| Application orchestration and bounded main scenarios | 10,209 | Pass |
| **Total** | **24,991** | **Pass across 38 unique entries** |

Every comparison checks all 2,048 synthetic modeled RAM bytes. Relevant pure
routine return values and ordered driver/service events are also compared.
Synthetic random settings and stale/invalid state fields characterize instruction
behavior; they are not observations of the owner's adapter.

The intentionally wrong sensor wrap (`16383` → `16384`) produced the required
mismatch. Separately, mutating only the descriptor immediate at `0x8aa6` from
`0x18` to `0x10` in emulator memory made the ordinary model disagree; a model
retaining its data/address dependency reproduced the changed writes. The vendor
file was never patched. Full fresh outputs are retained publicly:

- [Core report](../../research/stock-1.8/evidence/2026-10-11/validation.json)
- [Protocol report](../../research/stock-1.8/evidence/2026-10-11/protocol-validation.json)
- [Application report](../../research/stock-1.8/evidence/2026-10-11/application-validation.json)
- [Reproduction summary and digests](../../research/stock-1.8/evidence/2026-10-11/reproduction.json)

The ten guard tests check pinned oracle identity, rejection of altered/truncated
images before output creation, preservation of existing evidence, missing
parent/compiler rejection, one-time output configuration, rejection of Python
optimization that would disable assertions, and unchanged C/header identities.

## Reproduce from the repository

Use an existing Python 3.9+ and C11 compiler; dependency installation is the only
step requiring package access. From repository root:

```sh
python3 -m venv /tmp/ea9-stock-model-venv
/tmp/ea9-stock-model-venv/bin/python -m pip install -r research/stock-1.8/requirements.txt
/tmp/ea9-stock-model-venv/bin/python tools/test-stock-model.py
/tmp/ea9-stock-model-venv/bin/python research/stock-1.8/run.py
```

The recorded run used the already installed local `tools/rea-analysis/venv/bin/python`
and the same `run.py` entry point. That ignored environment is a convenience,
not a source or firmware dependency. Results default to a unique temporary
directory. `--output /path/to/new-results` selects a new directory under an
existing parent; even an existing empty directory is rejected. An optional
`--firmware` still requires the exact pinned stock size/digest. `--compiler` or
`CC` selects a compiler executable. Python `-O` is rejected. No previous output
or evidence is overwritten.

## Declared emulation boundaries

Original Thumb instructions execute offline against mapped memory. Stop register
instructions use dummy RAM pages; four final motor drivers and selected
timer/DMA/NVM/delay/UART calls emit recorded events. Critical-section helpers are
stubbed, so atomicity and interrupt races are outside the result. NVM stubs return
`-7`, which the application callers ignore; no flash is programmed.

Main-loop cases hold one sensor sample fixed per invocation, PA3 low at both
shutdown reads, and explicitly supply wake by skipping WFI after recording it.
Held-high polling, changing sensor input during delays, real sleep/wake, arbitrary
interrupt schedules, reset/startup, bootloader and physical mechanics remain
unmodeled. Frame lengths 4–255 and valid SRAM pointers are host-contract bounds,
not factory validation. PID uses denominator 200; original division-by-zero
behavior is excluded. The earlier Unicorn Cortex-M0 selection accepted MOVW,
so these comparisons do not establish ARMv6-M instruction legality.

No device enumeration, HID/USB reports, updater execution, firmware upload,
motor operation or canonical app-state mutation was performed. The next
reconstruction work remains integration with explicit scheduler, peripheral and
flash interfaces, followed by reset-to-handshake and varying-input sequences.
The [whole firmware ledger](../reverse-engineering/whole-firmware-reconstruction.md)
retains that wider scope and its unresolved claims.
