# Astra44 — capture and shutdown liveness

Offline source audit completed October 19, 2026. **No new runtime defect was
reproduced in this lane; no shutdown patch is proposed.** Four production
capture/dispatch cases and seven extracted production wait cases pass under
AddressSanitizer/UndefinedBehaviorSanitizer. Six existing extracted terminal
tail cases also pass. Two deliberately incorrect capture mutations fail.
[Runner and fixtures](../../firmware/upstream-hardening/followup/44-shutdown-liveness/run.py)
· [source-bound results](../../firmware/upstream-hardening/followup/44-shutdown-liveness/results.json).

All 49 reconstructed AF3.7 source digests match the published manifest. The
local upstream `main.c`, `emount.c`, `em_uart.c` and `delay.c` also match their
reference-collection checksums, at pinned upstream commit
`d52ed06cc449918f938e0695fbf29a0c4141f2b2`. No hardware enumeration/open,
USB/HID report, motor action, app/updater launch, canonical Application Support
access, external message or Git mutation was performed by this lane.

## Capture, cancellation and session handling

The compiled replay runs the complete production `emount.c`, packet initializer,
frame parser, ownership and shutdown helpers, with the actual trace writer and
motion collector. The synthetic EIC supplies complete checksummed frames; UART
calls are observed and return success. All ordinary initialization uses the
production `ea9_packets_init()` before `em_init()`.

Each scenario completes readiness, starts status on VD, and injects a CS
interruption carrying an init-class session-shaped frame during the first
status UART call. Production ownership classifies this as raw; it does not
advance the session. No raw transmission occurs before the following VD. The
raw echo then completes and clears its retry. Variants inject a session opener,
shutdown, or readiness during the raw UART call, plus a baseline with no such
injection. The checks establish:

- A completed raw echo disables status. Further VD pulses alone remain silent.
- An ordinary readiness request afterward, or queued during the echo, restores
  status in the same session and sends the status pair on the next VD.
- An ordinary session opener during the echo advances the generation, invalidates
  readiness, and prevents completion of the old raw owner from changing the new
  session's status state. Fresh readiness can establish that session.
- Shutdown during the raw echo latches immediately, invokes inhibit, cancels
  ownership and readiness, and allows only the immutable shutdown acknowledgement
  on subsequent foreground service. The callback runs once; later opener,
  readiness, shutdown and VD stimuli produce no additional sends.

Removing raw status-disable or retaining a successful raw retry causes an
assertion failure. These are sensitivity controls against broken policy, **not
baseline defects**. The test does not claim that silencing status after capture
matches an unobserved camera expectation. UART success is synthetic local
completion; it cannot demonstrate camera receipt or acceptance.

## Actual terminal dependencies and bounds

`em_shutdown_ack()` enters its callback only after a locally successful echo,
sets OFF and revokes readiness first. Admission has already inhibited motion.
The callback is foreground work. The production short masks restore their
incoming PRIMASK, and `em_uart_disable()` clears USART enable and sets the
software disabled latch; it does not disable SysTick or global interrupts.
The normal source path does not therefore turn UART disable into a stopped
millisecond clock. A new session cannot replace shutdown ownership: shutdown
admission precedes ordinary parsing and subsequent requests return early.

The exact terminal sequence is delay50 → UART disable/synchronize → trace flush
→ wait for two consecutive VD-low samples one delay1 apart, or 500 tick units
→ terminal record → PA23 write → terminal record → delay100 → terminal record.
The existing six tail fixtures exercise VD low, held high, and low at the final
sample, each with successful delay100 return or an explicit cut at that delay.
The delay and pin boundaries in these six cases are synthetic. The cut proves
what a missing footer permits; it does not identify where physical execution
stopped.

Additional tests extract the exact UART sync, disable and send implementations.
They verify normal disable, immediate send rejection after disable, normal
send, and bounded fail-stop invocation for stuck SYNCBUSY, DRE and TXC. The
actual macro uses 4,194,304 iterations. These are loop-work bounds, not measured
milliseconds. A sync fault enters `st_fail` before the callback can reach PA23.

The actual SysTick handler, `millis()` and `delay_ms()` control flow are compiled
separately. Only reads of `g_millis` inside `delay_ms()` are replaced by an
explicit synthetic read boundary; that boundary invokes the real handler in
advancing-clock cases and leaves it idle for the stalled-clock case. Zero, one,
50 and 100 tick waits and uint32 wrap pass. A stalled clock invokes
`st_fail(ST_TICK_WAIT)` after the exact 268,435,456 loop iterations (268,435,457
clock reads including initialization). This is a fail-stop outcome, not normal
terminal return. No timer interrupt delivery or elapsed hardware timing is
emulated.

`st_flush()` masks interrupts for its entire append sequence; `st_terminal()`
also masks around its append. Both restore the incoming mask on every returning
path. Their NVM-ready polls have 4,194,304-iteration budgets; a failure marks
the writer failed, and later appends return. The flush has a finite page plan
and does not erase. These flash intervals can delay SysTick service, so the
nominal 50/500/100 tick quantities are not a total wall-clock shutdown bound.
The flash/peripheral timing is not simulated by this lane. `st_fail()` releases
motor pins, records what fits and loops in WFI; its fail-stop is deliberately
non-returning. A continuously busy body may also defer successful acknowledgement
through repeated TX admission rejection; the test does not claim a total deadline
from arbitrary shutdown arrival to PA23.

## Factory and upstream comparison

The [original-instruction factory tail audit](astra-31-factory-shutdown-tail-2026-10-15.md)
places formatted UART at `0x9180`, delay50 before UART disable, two delay1/pin
samples, PA23, delay100, sleep argument2, then the WFI boundary. Factory pin and
UART synchronization back-edges have no local deadline. The audit cuts delay
and UART hardware effects and supplies wake explicitly; it proves neither
physical timing nor actual sleep. Replaying its reported delay arguments as
elapsed hardware time would overstate that evidence.

Pinned upstream already has the bounded 500-tick VD loop and delay50/delay100,
UART disable, PA23 and a returning tail without WFI. Its original delay and
UART wait loops are unbounded. AF3.7 adds bounded fail-stop work budgets and
terminal logging, retains upstream's order, and commits shutdown only after TX
success. The factory and upstream differences are explicit policies, not a
basis for changing timing or re-enabling UART without discriminating evidence.
Several older source comments describe obsolete behavior (no UART disable or
revival by a fresh opener); executable code and this replay supersede those
comments for this audit. No source-comment-only patch is required for AF3.8.

## Camera evidence and disposition

The [October17 trace review](astra-40-41-af37-camera-trace-2026-10-17.md) establishes
local return of the raw echo and shutdown acknowledgement, VD timeout and a
PA23 marker; its missing tail-return footer does not prove a delay hang. The
[October19 repeat](../evidence/upstream-37-repeat-camera-failure-2026-10-19.md)
has owner-confirmed AF, two saved photos and battery removal, but only a new
home-failed summary and VD timeout fit. Storage was full after those two pages;
missing new PA23/tail records cannot locate a hang. The earlier cohort must not
be attributed to this later attempt.

No observed camera root cause is resolved by these tests. No polarity, gain,
drive limit, timing policy, raw-status policy or shutdown code is changed.
Production text/data/RAM delta for lane44 is **zero bytes**. This lane needs no
applicator and spends none of AF3.7's 328-byte code margin. Camera acceptance,
electrical PA23 effect, actual power removal, interrupt scheduling and optical
performance remain unqualified.

Reproduce in a fresh private directory:

```sh
python3 firmware/upstream-hardening/followup/44-shutdown-liveness/run.py \
  --output artifacts/private/astra44-recheck
```

## Independent integrated AF3.8 review

The same 17 cases and two failing controls pass against all 49 source pins in
integrated `readiness38a`, image SHA-256
`8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`.
[Candidate results](../../firmware/upstream-hardening/followup/44-shutdown-liveness/results38.json)
· [compiled review](../../firmware/upstream-hardening/followup/44-shutdown-liveness/compiled-review38.json).
The runner verifies AF3.7 first, then requires a separate candidate manifest,
checks the candidate image digest and every source digest, and ensures that
capture/owner/shutdown/UART/delay source contracts remain unchanged.

Only `main.c`, `startup_trace.h` and the firmware-version macro in `emount.h`
differ. The independent main review agrees that the query change computes from
request operands and static optical mappings; it performs no encoder read or
motor action. Handshake, abort and shutdown checks remain at dequeue and
publication, with generation equality at publication. The compiled worker at
`0x7cb8` has a four-query budget and restores the mask before conversion. Main
calls it at `0x855a`, then calls `em_poll` at `0x855e`, making service reachable
before the homing/step gate. The phase-label change distinguishes drive, settle
and shared iteration-budget failure without changing loop limits or drive
policy. These are the separate lane42 fix and instrumentation, not new lane44
changes or proof that the camera freeze is resolved.

Relative to AF3.7, compiled `main` grows 8 bytes and `focus_answer_queries`
shrinks 16 bytes. `powerdown_signal`, `motion_shutdown_inhibit`,
`em_shutdown_ack`, `on_cs_edge`, UART disable, delay, servo and STOCK symbol
sizes are unchanged. Every `main.c` compiler stack frame is unchanged. The
integrated code/data end is 39,600 (`0x9ab0`), margin 336 bytes, static RAM
3,044 bytes. These are static measurements, not stack high-water observations.

The inspected indirect-call map is: `0x56c6` → powerdown; `0x5754` → shutdown
inhibit; EIC `0x69b8`/`0x69cc` → CS/VD handlers; servo `0x7266` at cfg+52 →
retarget, `0x733c` at cfg+56 → abort, `0x74a8`/`0x7672` at cfg+48 → pump.
The preinit array is empty at `[0x9a94,0x9a94)`. The one init-array word at
`0x9a94` is `frame_dummy | 1`; the clone weak-callback literals at `0x50d0`
and `0x50f8` are zero. The overlay introduces no new indirect callback. Root's
separate complete stack analysis remains responsible for whole-call-chain and
interrupt-envelope accounting.
