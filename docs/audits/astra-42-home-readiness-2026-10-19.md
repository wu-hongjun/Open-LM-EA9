# Astra42 — bounded homing workload and post-failure protocol liveness

The offline production-path replay reproduces and repairs one software defect:
**after homing fails, operand-only optical queries stop receiving answers**.
The repair leaves the failed motor inhibited and readiness false. It does not
repair or explain the physical homing failure, and does not establish the cause
or resolution of either reported camera freeze.

The owner reported two saved photos followed by a freeze requiring battery
removal, with AF selected; actual AF-S versus AF-C remains unknown. The two
retained cohorts both report `home-failed`; the later cohort lacks detailed
events because diagnostic storage had insufficient capacity.
[Evidence](../evidence/upstream-37-repeat-camera-failure-2026-10-19.md) ·
[prior discriminating experiment proposal](astra-40-41-af37-camera-trace-2026-10-17.md).

## Reproduced defect and exact repair

In pinned AF3.7 `main.c`, `home_service()` does not retry `HOME_FAILED`, and
`g_homed` remains clear. The foreground optical query worker is called only in
`step == 1`, entered after readiness. Its own admission and publication checks
also reject `motor_is_inhibited()`. Thus either gate independently prevents
these operand-only queries from completing after failed homing. Neither
conversion needs the current encoder coordinate or a committed home reference.

The pinned [liveness applicator](../../firmware/upstream-hardening/followup/42-home-readiness/apply.py)
changes only `main.c`:

1. Remove the worker's two `motor_is_inhibited()` checks. Retain handshake,
   abort, shutdown and session-generation checks, dequeue locking, publication
   locking and the existing finite queue budget.
2. Move the foreground worker call from the `step == 1` block to immediately
   before the outer loop's `em_poll()`. Keep the existing real servo/homing pump
   worker call.

The independent [phase applicator](../../firmware/upstream-hardening/followup/42-home-readiness/apply_phase.py)
requires that exact liveness result and the pinned AF3.7 trace header. It adds
`ST_HOME_DRIVE=17`, `ST_HOME_SETTLE=18` and `ST_HOME_BUDGET=19`, chooses the phase
in one local byte, and directs both existing iteration-limit branches through
one label that selects the budget reason. The existing failed label retains
its readiness state, first-fault recording, motor inhibition, deferred-command
clear and emergency release. No poll increment, comparison, deadline, duty,
polarity, stillness threshold, reference reset or retry policy changes.

These labels describe the software branch. Drive and settle labels mean the
phase could not establish qualifying stillness before its deadline; this can
include a pump that returned after the deadline. The existing first-fault latch
remains sticky. The labels add no occurrence timestamp, trajectory or physical
end-stop proof. Historical AF3.7 fault 11 remains valid; interpreting new labels
belongs to a version-scoped AF3.8 decoder change owned by integration.

## Source binding and experiments

The [runner](../../firmware/upstream-hardening/followup/42-home-readiness/run.py)
verifies all **49** AF3.7 source pins and its host shim before and after testing.
The original tree is never edited. In `--candidate` mode it additionally checks
every completed AF3.8 source pin, manifest, image digest and shim before and
after, clones the candidate without reapplying overlays, and uses the frozen
AF3.7 tree for all baseline controls.

The fixture extracts the actual `motor_home`, stillness, cancellation, command,
`home_service`, query worker and `pump` functions plus the actual foreground
service blocks from each tested source. It links production `emount`, packet
initialization, frame parsing, owner, shutdown, focus-map/distance/prediction,
motion trace and startup trace modules. RX queries and VD edges pass through
the existing host UART/EIC boundary and real dispatcher. Both 0x22 and 0x2E
answer operands, frame length, checksum and terminator are checked. The worker
has a host-only pre-conversion interrupt hook; test-only accessors expose queue
counts and the retained first fault. Motor, encoder, ADC, clock, UART/EIC and
flash boundaries are synthetic. No application startup or device I/O is used.

| Unique scenario | Observed synthetic elapsed time / work | AF3.8 phase label |
| --- | --- | --- |
| Stationary-feedback home under continuing query/status traffic | 80 ms, successful reference | none |
| Same workload crossing uint32 clock wrap | 80 ms, successful reference | none |
| Continuing drive movement | 300 ms, failed closed | 17 |
| Continuing settle movement after successful drive | 540 ms total, failed closed | 18 |
| Real status UART send advances clock across drive deadline | 301 ms, failed closed | 17 |
| Real status UART send advances clock across settle deadline | 541 ms total, failed closed | 18 |
| Frozen clock, query/status traffic continues | 999,999 pump calls, 0 ms | 19 |
| Drive consumes 600,000 polls, clock then freezes during settle | 999,999 total pump calls, 40 ms | 19 |

Every failure scenario then presents a fresh query and runs 32 actual
foreground service passes. AF3.7 returns **zero** answers and leaves one query
pending. The repair returns **one** answer and drains both queues while
`g_homed` remains false, inhibition remains set, no reference reset occurs, no
new home attempt or drive occurs, and no focus position is reported. A session
reset injected during conversion discards its answer; a shutdown injected
during conversion discards its answer and produces exactly one 0x16 echo.

Each run has 31 scenario executions: eight baseline cases, eight liveness or
candidate cases, eight phase or candidate cases, and seven independent mutants.
There are eight unique workload scenarios; candidate mode intentionally uses
the same final candidate for both proposal and phase groups. All 18 expected
passes and all **13 intended failures** are required. The six failed baseline
cases and both half-fix controls fail specifically at the query-liveness
assertion. Removing either deadline recheck fails the readiness/cutoff
assertion, removing failure inhibition fails that safety assertion, resetting
the shared poll counter between phases fails the total-work assertion, and
mislabeling drive as settle fails the phase-identity assertion. The runner
requires the expected assertion text; an unrelated crash is not accepted as a
successful negative control. Host builds use ASan and UBSan.

## Full ARM reproduction and integration

All production units compile and link before any host-only instrumentation.
The frozen AF3.7 ARM build reproduces its full image SHA-256. Candidate mode
also requires the reconstructed complete image digest to equal the supplied
AF3.8 manifest, in addition to checking loaded code plus initialized data.

| Composition | Loaded code/data end | Margin before diagnostics | Static RAM |
| --- | ---: | ---: | ---: |
| Frozen AF3.7 | 39,608 | 328 bytes | 3,044 bytes |
| Liveness only | 39,592 | 344 bytes | 3,044 bytes |
| Liveness plus phase labels / final AF3.8 | 39,600 | 336 bytes | 3,044 bytes |

The behavioral repair saves 16 bytes; phase attribution adds eight, for a net
reduction of eight bytes. No helper production module is introduced. The
completed private candidate `readiness38a` reproduces image SHA-256
`8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`.
Its source delta against AF3.7 consists exactly of `main.c`, `startup_trace.h`
and the AF3.8 version in `emount.h`.

[Isolated source results](../../firmware/upstream-hardening/followup/42-home-readiness/isolated-results.json) ·
[Final candidate results](../../firmware/upstream-hardening/followup/42-home-readiness/final-results.json).
The two applicators are sequential: `apply(work)` followed by
`apply_phase_labels(work)`, before the integrator changes the version header.
Reproduce with fresh, private output directories:

```sh
python3 firmware/upstream-hardening/followup/42-home-readiness/run.py --output artifacts/private/astra42-new-isolated
python3 firmware/upstream-hardening/followup/42-home-readiness/run.py --candidate artifacts/private/readiness38a --output artifacts/private/astra42-new-candidate
```

All work was offline. No device inventory/open, HID/USB report, motor action,
updater/app launch, canonical Application Support access, external message or
Git mutation was performed by this lane. No frozen release, pin or recovery
artifact was modified. Root owns final integration, decoder compatibility,
release preservation review, commit/push and any separately authorized hardware
step.

Synthetic clock increments are workload controls, not measured protocol latency
or an electrical cutoff guarantee. The production loop checks the deadline
after the pump returns; the crossing tests prove rejection of late readiness,
not an independently timed motor cutoff inside a blocked call. Stationary or
frozen encoder feedback still qualifies under the existing software-reference
policy. The real camera's query sequence, AF mode, homing trajectory and failing
phase remain unknown. Camera acceptance and optical AF performance remain
unqualified; this is a verified protocol-liveness repair plus better fault
attribution, not a camera-freeze remedy claim.
