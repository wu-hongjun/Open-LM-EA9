# Astra lane 06: motor ownership, servo completion and fault bounds

Offline proposal, October 15, 2026. No released image, device, HID path, updater,
physical motor, or canonical Application Support state was accessed or changed.
Frozen input is upstream diagnostic 3.2,
`e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
The runner verifies every manifest source and the released image before making
its own staging tree. Root owns integration, release decisions and Git.

## Integration contract

Run `lanes/06-motion/apply.py:apply(work)` after frame, explicit TX result,
02-shutdown, 01-capture, 03-homing and 05-transport. **It replaces, rather than
follows, root `apply_motor.py`.** It edits staged `motor.c/.h`, `servo.c`,
`abs_encoder.c`, `main.c` and `em_uart.c`. Exact source anchors fail closed if
prior overlays drift. The runner composes these dependencies in that order.

The independently reviewed foundational driver keeps `motor_inhibit()` sticky
until reset, with no clear API. `motor_init()` does not clear it.
`motor_emergency_release()` remains a transient release. The cutoff detaches
all four existing PWM pins, clears their GPIO directions, and writes PA19 high,
matching frozen `st_fail`'s established convention. It has no TCC, SPI, NVM or
clock wait. Clearing direction is the additional change from root's initial
proposal; no polarity or GPIO identity was invented.

`motor_attach_pins()` preserves prior interrupt masking, checks the latch and
commits all four mux writes under that short mask. All PWM synchronization waits
remain outside it. A shutdown accepted before attach blocks it; an IRQ pending
during attach executes after unmask and detaches the completed assignment. An
interrupted drive may subsequently write disconnected TCC registers, but cannot
reattach the pins. Nested calls preserve prior PRIMASK.

## Reproduced defects and bounded fixes

| Defect | Negative control and fix |
| --- | --- |
| Foreground remux after cutoff | Compile actual frozen `motor.c`, supplying the missing latch/cutoff API at the test boundary, and interrupt around every PORT/TCC store and wait. Frozen attach/drive/reverse/brake/init can restore mux after cutoff. The patched attach transaction closes these tested intervals. |
| Frozen millisecond clock | Actual servo loop and seek helper exceed the harness limit without returning. Both now have a 1,000,000-poll work budget independent of `millis`; exhaustion latches GPIO cutoff. This is not a calibrated electrical timeout. |
| Seek duty reverses during narrowing | `uint16_t` duty 65535 narrows to negative before the old driver clamp. Clamp to the existing `MOTOR_DUTY_MAX` before conversion; normal duty and direction definitions remain unchanged. |
| Stale arrival velocity | Fresh in-band position is accepted using previous control-step velocity and accumulated dwell. Arrival now checks the current step's velocity before accepting prior dwell; a new target resets dwell. Existing gains, tolerance, speed and time constants remain unchanged. |
| Unsafe feedback can rearm | Existing RUNAWAY and WRONG_WAY outcomes identify unsafe feedback but leave later commands able to drive. These outcomes now latch inhibition. Ordinary stall and ordinary timeouts retain their existing policy; only the independent poll-budget timeout latches a timebase-related cutoff. |
| Tracker signed overflow | Seed actual tracker at INT32 extrema and cross by one: frozen C triggers UBSan. The addition is checked, last representable coordinate retained, and motor inhibited. Normal forward/reverse 14-bit wrap controls remain unchanged. |
| Active motion survives session/off transition | Actual extracted `focus_abort` and `focus_exec` are exercised with session, shutdown, inhibit, handshake loss and abort state. The active motion checks the captured epoch and off states; final events use a short locked check+enqueue. `focus_run` checks ownership before work and after servo/final reporting. |
| Locally copied command acquires newer epoch | Main samples epoch and dequeues the command under an outer lock, then passes that exact epoch to `focus_exec`. Deferred work uses its recorded epoch; retarget admission checks and takes atomically, and records the active epoch rather than sampling a newer one afterward. A fully completed new handshake in the synthetic gap is an ownership robustness test, not a demonstrated IRQ-only hardware sequence. |
| Homing publishes readiness after last cancellation check | Execute the exact final commit with an interrupt request immediately before `g_homed` publication. Before06 accepts the Stop before publishing ready. The post03 commit serializes the final cancellation check and readiness assignment; a pending interrupt is accepted after the commit. All encoder I/O is outside this mask. |
| Fatal RX drain loses cancellation channel while motion stays enabled | Execute the actual extracted post05 `SERCOM1_Handler`. The persistent stuck-RXC branch disables receive IRQs but originally does not cut motion. It now calls GPIO-only `motor_inhibit()` at the sticky fatal latch. Transient error/overflow rejection does not inhibit. Receive communication remains unavailable after this fatal fault until reset. |

## Reproduction and result

From the repository root, with a new output path:

```sh
python3 firmware/upstream-hardening/lanes/06-motion/run.py \
  --output artifacts/private/astra-06-new-review
```

The final retained run is `artifacts/private/astra-06-verified/result.json`.
[Public result](../../firmware/upstream-hardening/lanes/06-motion/result.json)
records **392 executions**: **206 patched passes**, **57 frozen failing
controls plus 115 frozen passes**, and **9 before06 failing controls plus 5
before06 passes**. Before06 already composes lanes 01/02/03/05; its failures are
cross-lane ownership, final readiness, and fatal-RX cutoff omissions. Encoder
negative controls must produce UBSan's signed-overflow diagnostic. ASan/UBSan
are enabled for the C fixtures; compiled patched tests have no sanitizer errors.

Whole actual `motor.c`, `servo.c`, `abs_encoder.c`, `em_uart.c` and `main.c`
compile for Cortex-M0+ with ARM GCC 14.2, `-Os -Wall -Wextra -Werror`, the SAMD21
CMSIS headers and `EA9_NO_LOG`. This is compilation, not whole-image link or
size approval. Root's footprint lane must establish the linked flash/RAM gate.

Motor tests compile the actual whole C source against register shims; inserted
hooks observe before/after PORT/TCC store statements and peripheral wait
boundaries. Pending interrupts are deferred by modeled PRIMASK. Tests include
all generated injection sites for attach, drive, reverse, brake, release and
init, sticky follow-on entries, transient-release reentry and seek bounds. The
host wait shim does not simulate peripheral timing; it asserts waits are outside
the interrupt mask. The final readiness test likewise observes a callable C
boundary, not every ARM instruction. ARM object compilation is separate.

## Evidence limits and deferred work

Factory AF `0x8d94` target crossing and `0x8e28` completion flag/register writes
are software semantics; neither proves physical rest or optical focus. The
sensor extension confirms byte order and discarded low bits, without proving
physical status/error meanings. This lane does not import stock persisted origin,
change gains, choose a new polarity, interpret sensor low bits, or claim parity
with the factory control loop. See the [factory baseline](../reverse-engineering/factory-af-baseline.md)
and [sensor/origin record](../reverse-engineering/stock-re-progress-2026-10-12.md).

The position/prediction telemetry can still describe a software-completed move
while the mechanism coasts. Responsive SPI delivering stale but plausible samples
cannot be identified from this interface alone. No new sensor validity flag or
physical settle window is invented. End-to-end sensor freshness, stopping
distance, predictor truth during coast, optical accuracy and A7C II timing need
coordinated hardware evidence.

The encoder overflow fix is specifically a checked accumulator addition. It is
not a proof that all servo, predictor and main arithmetic tolerates arbitrary
INT32-limit synthetic coordinates or untrusted control configurations. Those
interfaces normally operate on the constrained focus coordinate/profile, and a
full arithmetic-domain audit remains separate. No camera failure is attributed
to any synthetic extremal state in these tests.
