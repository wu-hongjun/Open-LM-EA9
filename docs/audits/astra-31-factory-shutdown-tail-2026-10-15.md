# Astra 31 — original factory shutdown tail

Completed offline October 15, 2026. **35 bounded original-Thumb cases pass;
nine incorrect interpretations are rejected by contrasting traces.** This
extends lane04's explicitly unexecuted terminal tail. It changes no production
firmware, released image, historical evidence, unit data, Git state or hardware.
No factory parity or physical sleep/wake claim follows.

The [runner](../../firmware/upstream-hardening/followup/31-factory-shutdown-tail/run.py)
uses the pinned original application, SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
[Results](../../firmware/upstream-hardening/followup/31-factory-shutdown-tail/final/results.json)
contain synthetic inputs, ordered boundary events, register writes, source/range
hashes, mask observations and explicit cuts, with no ROM payload or unit record.

## Correction: the old shutdown oracle observed before formatting

`scripts/test-stock-shutdown-order.py` calls its `0x51c8` cut the final sender.
Original `0x51c8` only sets the GPIO mask `0x400` at `0x60000018`. The caller
`0x51d4` invokes it **before** rewriting the request length, terminator and
checksum. The packet reaches UART boundary `0x9180` afterward.

The new deliberately malformed synthetic request has checksum `a5a5` and an
invalid terminator. At `0x51c8`, that malformed content is still present. At
`0x9180`, the original formatter has produced the valid checksum and `0x55`
terminator. Both supplied TX returns, 0 and -7, reach the sleep boundary.
This bypasses receive admission and does not show that factory RX accepts a
malformed frame. Nor does an observed UART-call buffer prove physical delivery.

The old `checksumFinding` in the October12/13 shutdown-oracle JSON files is
therefore too strong: it describes a pre-format buffer as an echo boundary.
The legal-frame results remain consistent because formatting leaves an already
valid packet unchanged. Lane04's ordinary formatter finding was correct; the
new case establishes that the terminal shutdown path also calls that formatter.

Root integration proposal, confined to the live replay and explanatory docs:

1. Keep `0x51c8` as an explicitly named pre-format GPIO observation, and record
   the actual formatted pointer/count buffer at `0x9180` as the UART boundary.
   Leave the formatter executing. Compare that buffer with an independently
   normalized expected frame in the malformed direct-state control.
2. Change the live replay's cut/field names and `checksumFinding` to state this
   distinction; reject the old pre-format-as-wire interpretation explicitly.
3. Add a correction adjacent to the “Original factory evidence” subsection of
   `docs/evidence/af-29-link-service-2026-10-12.md` and the oracle link in
   `docs/evidence/af-30-candidate-2026-10-13.md`. Link this report and new result.
   Preserve the old oracle JSON and released validation artifacts as historical
   records; do not silently rewrite their bytes or their pins.

## Original instruction contracts now exercised

| Boundary | Evidence and finite conclusion |
| --- | --- |
| Completion handoff | In state1, `0x5eec–0x5efa` reads completion at `0x200004b8` and only advances state to2. It does not send in that invocation. Clearing completion between that return and the next call does not prevent the state2 tail. |
| State2 entry | `0x5efe–0x5f0a` clears request `0x2000052c` and formats/sends retained RX. Across all completion/armed/park-option combinations, state2 reaches the same tail and preserves the completion and armed bytes. No motor target/stop/driver entry executes in this isolated tail. |
| Order | Formatted UART call → delay argument50 → UART disable → delay argument1 and first pin sample → delay argument1 and second sample → PA23 set → delay argument100 → sleep argument2 → WFI instruction boundary. Delay arguments are observed calls, not measured elapsed time. |
| UART disable | Original HAL `0x70d0`, valid-pointer assertion `0x7174`, and lower `0x7d56` execute. The lower routine clears bit1 in the descriptor-selected control word and loops while either low bit of the word at offset `0x1c` is set. Scripted values1 and2 block; value4 does not; sequence2,2,0 permits progress. |
| Pin wait | First sample at `0x5f28–0x5f34`, second at `0x5f50–0x5f5c`. A high first sample retries. A low first and high second also retries the pair. Both must be low. Original selection is `(DIR & (OUT xor IN)) xor IN`: input-configured PA3 uses IN, output-configured PA3 uses OUT. |
| Core mask | Both pin reads execute `0x66cc` MRS/save/CPSID/DMB and `0x66da` DMB/load/MSR restore. Reads occur with PRIMASK=1; restores preserve the caller's 0 or1. WFI inherits that value. The tail does not guarantee interrupts are enabled at WFI. |
| Sleep setup | Original `0x7a70` with argument2 clears SCR bit2 at `0xe000ed10` and writes byte2 at `0x40000401` (PM sleep configuration). Other supplied SCR bits survive. This is the non-deep branch, not the argument3 branch that sets SCR bit2. |
| WFI continuation | `0x5f7e` is reached and recorded before execution. In separately labeled supplied-wake fixtures it is explicitly skipped; branch `0x5f80` resumes housekeeping at `0x5e5a`. With no pending work the function returns. With pending sample flag `0x20000604`, it clears the flag and reaches original sensor-position entry `0x8cc0`, where this probe stops. |

Held-high PA3 and held UART synchronization exhaust a fixed 4,000-instruction
budget before sleep. Inspection of their respective back-edges at `0x5f3e` /
`0x5f66` and `0x7d64` shows no local deadline or counter. These are bounded
noncompletion traces plus a local-loop finding; they do not establish a physical
hang or an overall bound when external inputs eventually change.

No new recheck or cancellation is implied by state2. The armed=1/completion=0
state2 fixture is deliberately supplied; it does **not** prove ordinary factory
execution reaches that inconsistent combination. The state1→2 handoff probe
does execute the dependency, but its subsequent completion clear is a supplied
between-call change. Earlier lane04 already established optional state0 park
and timeout-derived completion. This lane does not repeat those cases, infer
mechanical arrival from completion, or infer motor cancellation from reaching
WFI. The PA23 write's electrical consequences remain unmodeled.

## Current upstream C comparison and disposition

A read-only check of exact 3.6 source against its published manifest pins
`main.c`, `emount.c` and `em_uart.c`; hashes are retained in
[guard/source review evidence](../../firmware/upstream-hardening/followup/31-factory-shutdown-tail/guards-and-source-review.json).
This is source review, not another upstream runtime suite.

The current `em_shutdown_ack()` commits OFF only after `em_transmit()` succeeds;
a failed transmit leaves shutdown pending. Its powerdown callback disables
UART, waits for two low samples with a 500-tick limit, raises PA23, delays100
and returns without WFI. Acceptance also invokes the separately tested sticky
motor inhibit. These are deliberate upstream policies, not exact copies of the
factory tail. The corrected factory formatter evidence supports recomputing
the valid echoed frame; it reveals no current 3.6 runtime defect. No production
patch or new candidate is justified by this lane. Existing caller cancellation,
UART bound and shutdown admission tests are not counted again here.

## Reproduction, controls and limits

From the repository root, choose a new output directory:

```sh
tools/rea-analysis/venv/bin/python \
  firmware/upstream-hardening/followup/31-factory-shutdown-tail/run.py \
  --output firmware/upstream-hardening/followup/31-factory-shutdown-tail/recheck
```

The 35 cases comprise 16 state2 motor-flag/option/mask combinations, three
state1/next-call dependency probes, five pin-input/selection probes, four UART
synchronization probes, two pre-format/UART controls, three sleep-register
seeds and two supplied-wake continuations. Nine explicitly evaluated wrong
rules fail: pre-format equals wire, state2 rechecks completion, tail clears
armed, tail always enables IRQs, one low sample suffices, PA3 wait has a local
timeout, UART disable ignores synchronization, WFI makes pending housekeeping
unreachable, and sleep argument2 sets deep sleep. Existing-output and optimized
Python invocations are rejected separately without modifying final results.

Original instructions execute through formatter, GPIO handoff, UART disable,
valid-descriptor assertion, interrupt-mask helpers and sleep setup. Cuts are
DMA stop `0x91ac`, UART sender `0x9180`, and delay `0x66fc`. The latter two
record boundary arguments/bytes and supply return values. No timer interrupt,
DMA engine or asynchronous exception is run. Dummy MMIO pages are inert RAM;
the UART descriptor's register pointer and its synchronization values are
synthetic. PA3 values are supplied at the register read. There is no GPIO alias,
electrical signal, oscillator or peripheral side effect model. The only observed
MMIO writes on a successful tail are GPIO mask0x400, UART enable-bit clear,
GPIO mask0x800000, SCR update and PM sleep byte. This does not prove that all
other physical peripherals are inactive; the TX/DMA cuts hide their effects.

All fixtures start in privileged Thread mode, CONTROL=0/IPSR=0, using the
existing Cortex-M0 Unicorn oracle (2.1.4), with supplied PRIMASK0 or1. This is
not arbitrary inherited-core-state or pending-interrupt coverage. WFI is never
represented as actual emulated sleep: the primary cases stop before it, and
continuation cases explicitly supply a wake by skipping it. Wake source,
interrupt eligibility, actual low-power entry and hardware return are unresolved.
Barrier execution is not a concurrency or timing model. Startup, homing and
persist flags are held inactive to isolate the terminal path.

No blocker prevented meaningful terminal-tail instruction execution. The
remaining blocker to sleep/wake and mechanical claims is the absence of a
peripheral/exception/physical model or owner-coordinated hardware evidence,
not missing byte inventory. This adds bounded contracts, not a new independent
C reconstruction model or an increase to the published 41-entry model union.
No device enumeration/open, USB/HID, updater, flash, motor, app launch or
canonical Application Support access occurred.

## Root integration check

Root independently repeated all 35 terminal-tail cases and nine contrasting
interpretations using a fresh private output. The corrected live historical
oracle passes all 25 cases. A separate mutation substitutes the pre-format
observation for UART bytes and fails at `Formatted UART frame mismatch`,
demonstrating that the corrected test detects the original boundary mistake.
[Root evidence](../evidence/release-guidance-and-factory-tail-2026-10-15.json)
binds these checks. All 60 prior release/recovery/pin artifacts, current 3.6
image/manifest/resource and both historical shutdown-oracle JSON files remain
exact. Only the live replay and explanatory documentation changed; no candidate
version or runtime code changed.
