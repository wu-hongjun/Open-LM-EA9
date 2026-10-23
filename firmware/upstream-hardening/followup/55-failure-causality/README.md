# Offline diagnostic/startup causality probes

This lane demonstrates a concrete AF4.1 availability limit without changing any
firmware policy: successful cold-start baseline appends eventually fill the
diagnostic tail, after which `st_crash_boot()` cannot return. Its explicit
availability probe intentionally exits23. The runner succeeds only when the
documented behavior and this failed availability requirement are reproduced.

```sh
python3 firmware/upstream-hardening/followup/55-failure-causality/run.py \
  --output artifacts/private/astra55-causality-new
```

The output must be a new private directory. Frozen4.1 and base4.0 manifest/image
hashes, all49 source pins per image, and the host shim are checked before/after.
No device, USB/HID, app, motor, firmware compiler, or canonical host-state access
occurs. No real camera frames, operands, raw dumps, identifiers, or keys are used.

The test compiles the actual `startup_trace.c`, `emount.c`, protocol companions
and motion collector with ASan/UBSan. Production `st_fail` and watchdog C bodies
are extracted byte-for-byte; hardware NVM/IRQ, CPU wait instructions and registers
are inert boundaries. Exact production main startup ordering is asserted; the
whole main loop is not executed. Pin reads advance synthetic ticks through the
existing host shim. This is not a physical timing/electrical model.

Cases cover16 successful POR-only baselines followed by a refused17th start,
initially full valid storage, preserved WDT crash latch, the observed camera
record's page-count shape using wholly synthetic data, actual `em_init()`'s
CS-rise timeout, and a terminal workload followed by clean starts. A deliberate
boot-gate removal fails both full-storage and crash-latch assertions; it is a
negative control, not a proposed fix. Base4.0's actual scanner returns without
writing for32 empty and32 full-tail starts; its main has no boot-record gate.

`offline-results.json` is the sanitized receipt. The actual camera's first
shutter-delay/freeze cause remains unresolved. See the
[causal review](../../../../docs/audits/astra-55-failure-causality-2026-10-23.md).
