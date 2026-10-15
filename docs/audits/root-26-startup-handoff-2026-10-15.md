# Follow-up 26 — startup receive ownership and scoped EIC delivery

The Astra turn identified the startup lead, then was interrupted by content
filtering. Root completed the benign source reproduction, proposals and fitting
work. **This is not counted as a completed Astra audit.** Independent
[Astra review 28](astra-28-startup-handoff-review-2026-10-15.md) found a flaw in
the initial proposal and verified the narrower replacement against real UART/
EIC source. All tests are offline with synthetic peripheral inputs.

## Reproduced defect

Frozen 3.5 `em_init` enables EIC delivery, then calls `on_cs_edge(0)` directly
to rescue the already closed first window. That direct call runs in foreground;
the real EIC callback can interrupt it. Thus the request mailbox's intended
single-producer assumption does not hold during this handoff.

The [root fixture](../../firmware/upstream-hardening/followup/26-compiled-irq/run_handoff.py)
uses the actual `em_init`, dispatcher and owner source. A valid 11-byte opener
is interrupted during its copy by another valid 17-byte request. Frozen 3.5
produces a mixed, checksum-invalid 11-byte owned request and advances the session
generation twice. Earlier enable/validation cuts replace the first request.
The shared source is never edited by the runner: hooks and hardware shims live
only in private copies, with ASan/UBSan enabled and all 46 source hashes checked.

This root fixture deliberately queues a complete synthetic frame. It proves a
software ownership failure under that cut, not the electrical timing of two
physical CS edges. Review 28 supplies a stronger independent control: **one
rising EIC interrupt** executes the actual UART reset and poisons the buffer
during the foreground copy. No nested EIC invocation or complete second frame
is required for that corruption.

## Rejected and accepted proposals

The first proposal saved PRIMASK, disabled all interrupts across EIC setup and
rescue, then restored it. It passes the root producer-serialization fixture.
Review 28 demonstrates why that alone is insufficient: a final UART byte that
would complete the frame during setup is delayed until after rescue rejects
the incomplete frame. A supplied short receive FIFO can also accumulate bytes
while all interrupts are masked. **The global-mask proposal is rejected** and
retained only as a counterexample in `apply()` and review fixtures.

The accepted `scoped()` applicator instead splits EIC setup from delivery:

1. `em_eic_init` disables only NVIC EIC delivery before publishing callbacks,
   then configures the peripheral and its existing priority. UART and SysTick
   interrupts retain their existing state.
2. Foreground performs the first-window rescue or empty/invalid reset with no
   competing EIC producer.
3. New `em_eic_start` enables EIC delivery afterward, without clearing pending
   edge state. It does not change PRIMASK.

The hardware boundary remains in `em_eic.c/.h`; frame parsing remains in
`emount.c`. No scheduler, gains, target mapping, aperture policy, time budget or
storage range changes. Host shims gain the new hardware API stub separately;
the firmware never links that stub. Review 28's exact-final cases cover the new
compiled-source composition rather than reapplying the proposal to frozen code.

## Fitting evidence and parity

The scoped change alone, with the open snapshot omitted, still leaves only
252 bytes before diagnostics and fails the existing 256-byte release floor.
The accepted fitting composition omits **both** legacy RAM assignments
`em_rx_bytes_at_open = em_rx_bytes` and `em_rx_bytes_at_close = em_rx_bytes`
under `EA9_NO_LOG`. Each snapshot's sole source read is the excluded legacy
page's subtraction. The live RX byte counter stays active, as do all wire, RX
and startup-trace operations. No MMIO or sensor read is removed.

[ARM preprocessing](../../firmware/upstream-hardening/followup/26-compiled-irq/review_snapshots.py)
checks all 22 release units: the only nondeclaration uses are those two
assignments. Logging-enabled tokens are identical after gating; release tokens
differ solely by removing the assignments. Lane 24 independently confirms the
open snapshot consumer. The root fixture compares complete in-memory diagnostic
storage and emitted frames byte-for-byte before/after both omissions over four
cuts for each proposal. The scoped composition ends at `0x9af4`, leaving **268
bytes**, with **3,064 static RAM bytes**. These are linked analysis measurements,
not physical timing or camera acceptance.

The initial trace harness reuse exposed a preexisting host pointer expression
that formed an out-of-bounds intermediate pointer during `st_init`. The private
fixture parenthesizes the offset, as earlier lane 23 does. No production source
or expected firmware outcome is changed to hide that sanitizer failure.

## Reproduce and limits

```sh
python3 firmware/upstream-hardening/followup/26-compiled-irq/run_handoff.py --source artifacts/private/absolute35a --output artifacts/private/handoff-recheck
python3 firmware/upstream-hardening/followup/26-compiled-irq/review_snapshots.py --source artifacts/private/absolute35a --output artifacts/private/snapshot-recheck
python3 firmware/upstream-hardening/followup/26-compiled-irq/measure.py --design scoped --snapshots both --output artifacts/private/handoff-size-recheck
```

The measurement runner links analysis-only ELF/map files, never a binary image.
Use `--snapshots open` for the 252-byte failing measurement, or `--design
global-mask --snapshots none` for the separately rejected initial design.

Root fixtures verify 20 variant/cut outcomes, including three frozen failing
controls; full global-mask passing cases are explicitly not acceptance of that
rejected design. Review 28's 287 assertions include 41 exact-final 3.6 cases,
the global-mask counterexample and early-start/unlock negative controls.

EIC flags can coalesce physical edges. UART bytes arriving before a rising-edge
reset may still be discarded; a delayed boundary can also produce duplicate
parsing. Those peripheral scheduling limits are documented by review 28 and
not solved by this source handoff gate. The tests do not prove a camera places
events at any particular cut or that this defect caused prior A7C II freezes.
Physical response time, exposure, capture, shutdown and optical AF remain
unqualified. Factory boot assumptions are conditional as described by
[audit 24](astra-24-boot-entry-2026-10-15.md).

No adapter access, USB report, updater, flash, motor operation, app launch or
canonical state mutation occurred. Uploaded 3.2 remains pending owner-confirmed
physical reconnect and strict verification. Published images and recovery stay
unchanged; the accepted executable is prepared only as separately versioned 3.6.
