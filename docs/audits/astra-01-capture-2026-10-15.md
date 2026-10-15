# Astra lane 01: capture, status and request ownership

Offline bounded proposal against upstream `d52ed06cc449918f938e0695fbf29a0c4141f2b2`
and immutable 3.2 image SHA-256
`e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
No device enumeration, report, updater, flash, motor action or Application Support
mutation occurred. Production, released images, recovery and 3.2 source inputs
were not edited. Root owns integration, release version/digest, commit and push.

## Findings and correction

Frozen `emount.c` snapshots every incoming frame into `g_req`, even when an older
control request owns `g_reply_id`. A normal frame can consequently replace
0x34's operand bytes before its reply. Two init requests replace the first
pending ID. Status 05, its hold/gap, and 06 have no CS interruption cancellation.
A disabled UART's void return still publishes transmit/readiness/tail state.
The foreground focus dequeue also clears its ready flag before copying a
mutable ISR-owned command, permitting a torn/replaced command or duplicate.

The small `em_owner.c/.h` module owns two fixed 256-byte request slots: one
immutable active request and one first-wins pending request. Accepted complete
frames retain their own length, ID, payload and raw sequence. Overflow saturates
an exposed counter (`em_control_overflow()`); it never silently replaces pending
control. Foreground claims the pending slot with a short `st_lock` index swap;
copying a full frame happens in the already serialized receive callback.

CS rise invalidates the remaining status pair and latches whether it interrupted
an active status phase. A validated INIT frame in that window becomes a raw
capture request independent of its ID, waits for a subsequent VD, and echoes
the exact validated frame. Window padding is excluded. Normal traffic retains
its parser and never becomes a blanket raw echo. The already-started 05 or 06
is allowed to complete; unsent 06/event/query tails survive cancellation. A raw
echo uses the recovered nominal 10 us lead and 100 us release hold, then disables
status transport. A later owned ordinary 0x0a re-enables status. Capture release
does **not** clear completed boot handshake/timestamp or command rehoming.

An accepted ordinary validated INIT 0x01 advances `em_session_generation()`,
clears handshake/timestamp and pending focus/query/event/answer state, and
invalidates an old failed-control retry. A phase-owned raw 0x01 does not advance
the session. An old 0x0a completion cannot publish readiness after the session
changes during its transmit. Focus/query dequeues and event/answer publication
use bounded interrupt masking; generation-aware motion cancellation belongs to
lane 03.

The applicator requires the new unconditional `uint8_t em_uart_send` result.
Counters, status tails, readiness and shutdown-OFF publication depend on
successful send. A failed ordinary/raw send retains its active slot for retry;
a failed shutdown echo returns the dedicated shutdown state to pending. The
lane-02 shutdown latch wins before ordinary/capture dispatch and transmission.

## Original instruction comparison and a rejected change

Re-ran the existing `investigate-af30-capture-interruptions.py` oracle: all 90
original-instruction cases pass, across phases 2/3/5/12/13, six IDs and three
sequences. The frozen AF 3.0 control reproduces five non-0x0a raw-echo divergences.
This confirms the supplied phase/interruption rule; it does not establish an
A7C II freeze cause, boot-to-connected reachability, or real interrupt timing.

Independent lane 04 additionally executed ordinary 0x34 handler `0x58a4` with
request sequences 0, 0x71 and 0xff: it preserves the stored reply's sequence
byte. An initially proposed universal ordinary sequence increment was therefore
**removed**. Ordinary replies preserve template bytes; only status uses a
single sampled incoming sequence plus one, and raw echo retains incoming
sequence exactly. The final fixtures include this unchanged behavior as a
positive frozen control.

Lane 04 also found factory raw sender `0x5260` reads **live** RX at callback time.
Our immutable snapshot is a deliberate ownership correction, not a claim of
byte-for-byte equivalence under later RX overwrite. Production's blocking status
intervals are a bounded approximation of the seeded factory phases, not a
transplant or reconstruction of its fourteen-state scheduler.

## Reproduction and results

From repository root, using fresh output directories:

```sh
python3 firmware/upstream-hardening/lanes/01-capture/run.py --shutdown --output artifacts/private/astra-01-final-composed
python3 firmware/upstream-hardening/lanes/01-capture/run.py --output artifacts/private/astra-01-final-isolated
tools/rea-analysis/venv/bin/python scripts/investigate-af30-capture-interruptions.py --output artifacts/private/astra-01-factory-v1
```

Actual outputs: composed **59/59 pass**, frozen 3.2 **53 intentional failures**
and six preservation controls; isolated **58/58 pass**, frozen **52 intentional
failures**. Both use Clang ASan/UBSan with warnings as errors. Matrix: six request
IDs at lead, 05 send, 05 hold, gap, 06 send and 06 hold; normal traffic controls;
9/17/64/255/256-byte echoes; pending and active ownership; successful/failing
init, raw, 06 and shutdown sends; session queue invalidation; atomic focus copy.
The checksum-valid 256-byte case validates buffer capacity, not its body grammar.

The focus-copy test inserts one explicit IRQ-attempt hook immediately before
the **actual** production command-copy loop in both sources. Frozen foreground
accepts it immediately and returns the replaced command. The patched `st_lock`
shim defers it until unlock, returning the old complete command and then the
new complete command exactly once. UART/delay callbacks are synthetic, and this
is not an MCU interrupt latency measurement. The raw factory replay emits one
existing Darwin linker alignment warning; all oracle assertions pass.

Committed machine-readable results:
[`result-composed.json`](../../firmware/upstream-hardening/lanes/01-capture/result-composed.json),
[`result-isolated.json`](../../firmware/upstream-hardening/lanes/01-capture/result-isolated.json).
All materialized 3.2 manifest source hashes and the released image hash are
verified before either host run. The only frozen emount test instrumentation is
the explicit focus IRQ cut; the test transport declaration returns success/failure
instead of void so frozen publication bugs are observable.

Cortex-M0+ `-Os` module object: **488 text bytes, 0 data/BSS** (the owning instance
is defined by the applicator). `sizeof(struct em_owner)` is **530 bytes**;
additional integration globals are a request pointer, retry pointer, generation,
and active flag. These are not whole-image linker/stack measurements. Root's
footprint lane must measure the complete composition before a new release.

## Root integration contract and remaining gates

1. Apply complete frame admission and unconditional TX result API to a **fresh**
   3.3 source tree; then lane 02, `01-capture/apply.py:apply(work)`, and lane 03.
   Compile `em_owner.c` alongside existing `em_frame.c` / `em_shutdown.c`.
2. Apply lane 05 after these. Lane 05 owns atomic TX admission with physical CS
   and pending EIC checks, immutable outgoing frame copy, and serialization of
   RX access. Lane 01's mailbox does not by itself protect shared `ea9_data`
   against an interrupt modifying capabilities/aperture while UART reads it.
3. Preserve lane 01's successful-send publication, pending first-wins policy,
   status-only sequence increment, raw exact echo, generation boundary and
   shutdown precedence when composing. Do not restore the removed ordinary
   sequence increment from earlier private v1-v6 probe outputs.
4. Re-run composed transport, homing and shutdown suites and full linked-size
   checks. There is no claim that all instruction-level IRQ boundaries, UART
   faults, optical behavior or camera acceptance have been established here.

3.2 still awaits the owner's physical reconnect and strict verification. These
offline results do not authorize uploading 3.3 or retrying failed AF 3.0.
