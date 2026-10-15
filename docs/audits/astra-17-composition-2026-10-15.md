# Follow-up 17 — bounded coordinate and query-pump composition

Independent offline review of frozen 3.3 plus the coordinate, follow-up 12, and
follow-up 16 overlays found one additional software-state defect: **homing could
publish `HOME_READY` after the bounded encoder tracker had rejected a reading
and latched motor inhibition.** The driver remained inhibited; this is a false
readiness/reference transition, not evidence of motor rearming or physical harm.
The minimal correction has been integrated by root into private `bounded34b` and
passes this lane's fault-path controls. No additional defect was found in the
reviewed query-worker composition.

## Source and scope

Initial review used `artifacts/private/astra-root-domain-flow-measure/src` and
the reports for follow-ups 12, 15 and 16. Final execution used the exact sources
in `artifacts/private/bounded34b`, whose manifest records image SHA-256:

`fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9`.

Both final runners verify every manifest source hash before and after execution.
All source instrumentation and compilation occurs in newly created
`artifacts/private` directories. This lane did not edit published firmware,
perform a full previous-lane campaign, enumerate/open USB, send hardware reports,
launch an app, run an updater, flash, access a network, write canonical
Application Support state, or commit. Root owns final build/release verification.

## Confirmed defect and correction

Before this lane's guard, `home_cancel_requested()` checked abort, shutdown,
handshake and epoch, but omitted `motor_is_inhibited()`. In `motor_home()`, an
encoder rejection can occur in the initial sample, drive stillness samples,
settle samples, or final sample. The coordinate remains bounded, but the
unchanged value can satisfy the stillness timer. The later cancellation checks
then permit `abs_encoder_track_reset()` and the `g_homed=1; HOME_READY` commit.
This contradicts the software reference/readiness meaning after a feedback
fault. It also lets the main loop advance to its homed reporting path.

The reproduction executes the complete production `motor_home`,
`home_cancel_requested`, `home_still_init` and `home_still_for` function bodies,
with the actual production tracker/reset bodies and actual homing constants.
Clock, raw encoder input, supply sampling, motor I/O and the pump are host
substitutes. No claim is made about the physical plausibility of the synthetic
encoder sequence or its timing.

Four cut cases establish `+65536` using eight accepted `+8192` modular tracker
increments, then inject `+1` on the initial, drive, settle-initialization or final
feedback sample. A fifth case starts the tracker at zero and generates all eight
accepted increments and the rejection **within `motor_home()` itself**. This
avoids depending on a preexisting near-limit coordinate. All five guard-removed
controls finish with fault 16, inhibition set, `HOME_READY`, `g_homed=1`, and a
reset coordinate of zero. Independently running the desired invariant against
each control fails its assertion. The no-fault control succeeds normally.

The [applicator](../../firmware/upstream-hardening/followup/17-composition/apply.py)
adds an early inhibited branch in `home_cancel_requested()`: clear pending
motion, mark `HOME_FAILED`, return cancellation. The existing callers route to
cutoff. The final check before reference reset and the locked readiness commit
also use this function. Existing `home_service()` excludes `HOME_FAILED`, so a
fresh command cannot retry this terminal attempt. The original encoder fault
reason is preserved; this branch introduces no NVM operation or new fault code.

On final `bounded34b`, all five fault cases end with `g_homed=0`, `HOME_FAILED`,
pending motion clear, zero resets, and the last accepted coordinate retained at
65536. The ordinary case still reaches ready with its one reference reset. The
runner makes its negative controls by removing **only** this guard in private
scratch, then verifies the reapplied proposal exactly equals final `main.c`.
The original input source remains hash-identical.

## Query, capture and servo composition

The bounded worker is still the sole answer producer. Its only calls are in
the foreground main loop and foreground pump; optical conversion functions have
no pump, protocol-dispatch, encoder or answer-publication edge. Thus the answer
capacity check at dequeue is sufficient for this call graph: an IRQ may enqueue
requests or invalidate the session, but cannot steal the available answer slot.
Both ownership capture/dequeue and publication checking use the existing nested
saved-mask locks. Conversion remains outside those locks, and each worker call
is bounded to four conversions. This is a bound on software work, not a measured
camera response deadline or interrupt-latency guarantee.

The new composition probe uses exact final worker, pump, tracker and abort-hook
bodies; the full production servo, protocol, ownership, shutdown, packet,
conversion, predictor and trace modules; and synthetic transport/encoder/clock
I/O. Current-position reporting is an observed stub checking coordinate bounds.
The nine passing ASan/UBSan cases cover:

- Ordinary session INIT during conversion through both homed and unhomed pumps:
  epoch advances, the old answer is not published, and the new handshake/status
  has no old answer. Unhomed pumping performs no position report.
- Shutdown at the same two pump cuts: no answer is published and no status 0x06
  is emitted after the cut.
- Raw INIT capture at the outgoing status-05 boundary: epoch/readiness remain
  owned by the existing session, and exactly one correct query answer is later
  delivered. Encoded length, checksum, terminator, tag and value are checked.
- Session INIT and shutdown during a query conversion inside the actual servo
  pump: the production abort hook returns `SERVO_ABORTED`, with no stale answer.
- Actual coordinate rejection at a servo loop sample and at the final feedback
  read: last position remains 65536, outcome is `SERVO_ABORTED`, and a query
  queued at that read remains pending without conversion or answer publication.
  The final-feedback case specifically covers conversion of an otherwise-OK
  servo result into aborted before its final pump.

The epoch/shutdown injections occur at an explicitly unmasked conversion cut;
this probe does not claim to explore all interrupt interleavings. The earlier
follow-up 12 lock/deferred-IRQ tests remain relevant. It also does not rerun the
full capacity/FIFO campaign from follow-up 16, whose sole-producer premise was
checked against this composition. Already buffered answers are not universally
purged by motor inhibition alone: the worker prevents new publication, while
status may still drain earlier answers. Session reset clears the queues;
shutdown suppresses status. These are distinct existing policies, not a new
claim that inhibition clears all protocol history.

## Evidence and limits

Final results:

- [Homing result](../../artifacts/private/astra17-home-final2/result.json): six
  final-source cases pass; five guard-removed invariant checks fail as intended,
  with five independent observation runs documenting their state transitions.
- [Composition result](../../artifacts/private/astra17-composition-2/result.json):
  all nine focused cases pass.
- [Homing runner](../../firmware/upstream-hardening/followup/17-composition/run_home.py)
  and [composition runner](../../firmware/upstream-hardening/followup/17-composition/run_composition.py)
  preserve input sources and use fresh scratch directories.

```sh
python3 firmware/upstream-hardening/followup/17-composition/run_home.py \
  --source artifacts/private/bounded34b --output artifacts/private/astra17-home-rerun
python3 firmware/upstream-hardening/followup/17-composition/run_composition.py \
  --source artifacts/private/bounded34b --output artifacts/private/astra17-composition-rerun
```

Use unused output paths. These are finite software-path tests, supplemented by
source review; they are not exhaustive firmware execution. Hardware SPI/PWM,
real clocks, camera behavior, optical calibration and physical safety were not
tested. The full homing test stubs the pump, while the separate composition test
executes the real pump with real query/protocol modules. No claim combines them
into an executed full-board homing experiment. The prior coordinate arithmetic
proof's distinct-read target discrepancy and exceptional long-gap time
conversion limitations remain unchanged. No further change to gain, mapping,
protocol grammar or coordinate capacity is proposed by this lane.
