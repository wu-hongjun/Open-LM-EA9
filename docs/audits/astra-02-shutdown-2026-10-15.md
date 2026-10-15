# Astra lane 02: shutdown ownership, October 15, 2026

**Offline proposal; not a released or installed fix.** The pinned 3.2 image remains
`e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
Owner reconnect confirmation and strict verification remain pending. This lane
performed no device discovery/open, HID/USB operation, upload, motor operation,
or Application Support mutation. Root owns 3.3 integration and commits.

## Findings in actual 3.2 C

The dispatcher snapshots every frame into one 16-byte `g_req`. A shutdown
followed by normal traffic retains shutdown as the reply ID but echoes the
normal frame. A later init request replaces the pending shutdown ID entirely.
A repeated shutdown replaces the original sequence/request. These are actual
production-dispatcher reproductions, not scheduler-model predictions.

The shutdown acknowledgement does not latch ownership until after calling the
park callback. A nested poll can service status while parking; late session
traffic can clear acknowledged off state despite physical UART disable. Pending
focus commands remain available after shutdown. Requests longer than 16 bytes
can invoke park and then return without echo or powerdown. Malformed requests
also reach that callback before frame admission is added.

`motor_home()` pumps `em_poll()` during drive and settle, then continues to brake,
reset the encoder and set `g_homed` after nested shutdown. The original park
callback can enter a full servo timeout before echo. These main/driver defects
require the lane03/lane06 integration below; the dispatcher fixture does not
pretend to execute them.

The `em_set_shutdown_enabled()` API has no call site in materialized 3.2 main.
Its old behavior discards a pending shutdown when disabled. The proposal latches
and inhibits even while servicing is disabled, preserving the request until
service is re-enabled. Disabled service is not a claim of bounded echo latency.

## Minimal proposal and integration contract

Files reside in `firmware/upstream-hardening/lanes/02-shutdown/`:

- `em_shutdown.c/.h`: independent validated first-request snapshot, 9–64 bytes,
  and IDLE → PENDING → ACTIVE → OFF latch. The snapshot length excludes padding;
  sequence and checksum are retained. Invalid or oversized shutdown does not
  inhibit, park, echo or power down. The capacity is a candidate limit, not a
  recovered maximum factory request size.
- `apply.py`: `apply(work: pathlib.Path)` edits a **fresh staged** build root or
  `src` directory and copies the module there. `apply_source()` is provided for
  finite host probes. Link `em_shutdown.c` plus existing `em_frame.c`.
- `em_shutdown_requested()` returns true for pending/active/off. RX invokes
  `em_set_shutdown_inhibit_handler()`'s callback immediately after publishing the
  complete snapshot. The callback must perform only bounded GPIO motor inhibit;
  no UART, peripheral synchronization, flash or park work is allowed in ISR.
- Shutdown intercept precedes ordinary reply publication. It clears pending
  ordinary reply/status/focus work, suppresses later ordinary RX, and prevents
  focus/query dequeue. Status checks before 05 and after 05/gap suppress unsent
  status and preserve event/query tails when shutdown interrupts the pair.
- The core **does not invoke the legacy park callback**. This explicitly prevents
  new shutdown motion and removes an unbounded callback from acknowledgement's
  critical path. The callback setter remains API compatible. A currently
  transmitting frame may finish; the shutdown request then echoes before the
  existing powerdown callback. OFF has no session-opener revival; reset is needed.
  Repeats while pending/active keep the first request, and repeats after OFF are
  silent because UART is disabled. These are explicit priority/lifecycle choices,
  not proof of every factory repeated-request behavior.

Apply after frame admission and before lane01 ownership. The `em_frame_view`
addition does not collide: shutdown independently validates its input and copies
only the declared validated length. Lane01 must accommodate the inserted guards
at status entry, after lead, before gap and after gap; it owns ordinary immutable
request/sequence handoff and capture-phase arbitration. There are no guessed
capture IDs here.

**Required integration gates:** lane03 registers GPIO-only `motor_inhibit()` and
uses `em_shutdown_requested()` to cancel home without brake/remux/reference
publication after cutoff. Lane06/root must keep motor inhibition sticky through
all later motor calls. Lane01/root must atomically admit TX against shutdown so
an interrupt after an ordinary reply's entry check cannot start a new ordinary
frame. The existing void `em_transmit`/UART contract cannot distinguish failed
send from success: this proposal still commits OFF after its call returns.
Successful-send publication and bounded UART failure behavior are mandatory
lane05/root integration work, not passed by these immediate-UART fixtures.

## Exact evidence

Run from repository root with a new output directory:

```sh
python3 firmware/upstream-hardening/lanes/02-shutdown/run.py \
  --output artifacts/private/astra-02-shutdown-new

tools/rea-analysis/venv/bin/python scripts/test-stock-shutdown-order.py \
  --output artifacts/private/astra-02-stock-shutdown-new
```

The runner verifies all frozen 3.2 manifest source hashes. It compiles the actual
production dispatcher with ASan/UBSan, production packet data/startup trace and
the original host shim, changing only explicit delay/UART hooks in a private shim.
Each case starts a fresh process. Private queue counters establish whether tails
were consumed. All fixture executions have finite harness timeouts.

**53 proposed cases pass; frozen 3.2 fails exactly 37 and passes 16 controls.**
The 21 named cases cover ordinary control, plain shutdown, normal/init overwrite,
first repeated request, 9/64/65-byte boundaries, checksum/terminator/truncation,
disabled service, park/powerdown reentry, pending command, lead/gap/in-flight-05
interruption, session after off, repeat after off, nonzero padded window, and an
unresponsive park callback. The last fixture gives the old park callback a
nonreturning body: frozen execution hits the finite one-second harness ceiling;
proposed execution makes zero park calls and completes. This proves callback
exclusion, not physical motor latency.

The other 32 cases cover lengths **9, 11, 16, 19, 27, 32, 48, 64** crossed with
sequences **0, 1, 0x71, 0xff**. Every proposed echo equals the complete request,
and every admitted shutdown invokes inhibit once, powerdown once, and park zero
times. Frozen 3.2 retains the <=16-byte controls and fails the longer cases.

The original-instruction oracle rerun passes **25 cases: 24 legal echoes plus
one direct-state invalid-checksum boundary**. It executes original `0x5e00`, with
ready phase 2 seeded, PA3 low, lower UART/timing/GPIO operations cut, dummy
register memory and WFI wake supplied. Observed order is raw echo, delay 50,
UART disable, delays 1/1, PA23 high, delay 100, sleep setup and simulated wake.
The invalid-checksum fixture bypasses RX validation; it is not a legal request.
This finite oracle does not establish a reachable active park, ordinary boot
reachability, actual elapsed time or A7C II acceptance.

Machine-readable local results:
`artifacts/private/astra-02-shutdown-verified/result.json` and
`artifacts/private/astra-02-stock-shutdown/validation.json`. The dispatcher report
pins lane inputs, exact frozen dispatcher/main and shim hashes. Results are
scripted CS/VD interleavings with immediate UART completion and callback cuts;
real IRQ/peripheral timing, transport failures, electrical behavior and optics
remain outside this lane. No surviving trace proves these defects caused the
reported A7C II freeze. AF 3.0 remains failed and 3.2 remains reconnect-unverified.
