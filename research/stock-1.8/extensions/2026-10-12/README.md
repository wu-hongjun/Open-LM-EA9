# Stock sensor reader and position-origin extension

This isolated C11 host model adds **three** bounded factory routine entries:
`0x89a4` (sensor reader), `0x8c64` (initializer for an inventoried filter-like
state block), and `0x8c80` (encoder/motion initialization). It uses the unchanged
public `stock_model.c` for already modeled restore, position and boot-metadata
semantics. It is research code, not a firmware image or a device tool.

The original-instruction oracle executes the sensor reader's valid-descriptor
paths through the original SPI HAL wrappers `0x6be4` and `0x6c0c`; lower enable,
transfer, assertion and delay boundaries are recorded stubs. Supplied response
bytes are synthetic. Dummy GPIO memory has no electrical behavior.

The retained evidence contains **68,648 passing cases/steps**, a detected host
byte-order mutation, eight composed origin sequences, and eight bounded traces
of original main entry `0x8b70` through its first foreground poll. Matching these
finite cases establishes neither whole-program equivalence nor physical
sensing, camera exposure or AF quality.

## Reproduce

From the repository root, use Python 3.9+ with the existing pinned dependency
[`unicorn==2.1.4`](../../requirements.txt) and a C11 compiler:

```sh
python3 -m venv /tmp/ea9-stock-model-venv
/tmp/ea9-stock-model-venv/bin/python -m pip install -r research/stock-1.8/requirements.txt
/tmp/ea9-stock-model-venv/bin/python research/stock-1.8/extensions/2026-10-12/validate_sensor_boundary.py
/tmp/ea9-stock-model-venv/bin/python research/stock-1.8/extensions/2026-10-12/test_input_guards.py
```

The runner creates a fresh temporary output directory by default. To retain a
chosen destination, `--output` must name a new directory under an existing
parent; existing directories are rejected. `--firmware` can only select the
exact 20,172-byte retained stock 1.8.0 application, SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
Python optimization is rejected so assertions cannot silently disappear.

The build links the authored extension with the shared, unchanged host model.
Generated libraries and a deliberately incorrect byte-order model stay in the
fresh output directory. No source, recovery image or original firmware file is
rewritten. No private settings, calibration, key, unit identity, USB, HID or
hardware interface is used.

[`sensor-boundary-validation.json`](sensor-boundary-validation.json) records the
exact source hashes, original instruction-range hashes and prior REA evidence
IDs, environment, finite scenarios, negative control and declared stubs.
The [dated research note](../../../../docs/reverse-engineering/stock-re-progress-2026-10-12.md)
explains the findings and remaining reconstruction limits.

[`input-guard-validation.json`](input-guard-validation.json) retains four guard
checks: existing output, optimized Python, wrong-size input and wrong-digest
input are rejected before creating output files. The original file stays read
only; modified negative inputs are temporary synthetic copies.
