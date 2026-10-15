# Audit 20: elapsed-time contracts in bounded C 3.4

2026-10-15. Offline review of exact `artifacts/private/bounded34b`, manifest
SHA-256 `8e358720a959a79a4636e1a9310fc23c08af9fa50539396d6946be6194c25a9a`.
All 46 manifest source hashes are verified before and after the probes. The
published image remains `fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9`.
Root owns integration, footprint measurements and any future candidate version.
This lane changes no published image or shared production file.

**Findings:** both homing phases can accept stationary feedback after the phase
deadline has expired during work inside the loop. A final unsigned elapsed check
after the stillness sample closes that acceptance gap. The predictor also has an
implementation-defined signed elapsed conversion that can affect the status sent
by a timed-out servo's final pump under an extraordinary sampling gap. An
independent proposal corrects its arithmetic without choosing a new physical
latency threshold. The servo's normal timeout guards exclude negative signed
control intervals unless the move lifetime aliases across a whole 32-bit wrap;
no servo, gain or period change is proposed.

## Production-path tests and limitations

Run:

```sh
python3 firmware/upstream-hardening/followup/20-time-contract/run.py \
  --output artifacts/private/astra-20-time-contract-new
```

The output directory must be fresh. The saved [results](../../firmware/upstream-hardening/followup/20-time-contract/results.json)
contain **62 executions: 25 frozen observations, 25 proposal checks and 12
frozen failing controls**, plus eight protected-path rejection checks. ASan and
UBSan run with nonrecovering failures; all expected positive executions pass
without sanitizer diagnostics. The failing controls are explicit behavioral
assertions; unsigned-to-signed conversion is implementation-defined in C, so
the absence of a UBSan diagnostic is expected and does not validate its meaning.

The runner compiles actual `servo.c`, `focus_pred.c`, optical conversion modules,
protocol dispatcher/queues/ownership/shutdown, and diagnostic code. It extracts
unchanged production bodies for `focus_run`, target resolution, retarget/abort,
the exact STOCK initializer, reporting, pump, query worker, home cancellation,
stillness and `motor_home`. It also executes the actual admitted-coordinate
tracker and reset bodies. Sensor SPI, GPIO/motor outputs, VDD and UART/IRQ timing
are host boundaries. The query conversion hook advances the synthetic tick
outside the query critical sections; the conversion itself still executes.
The encoder hook advances time inside the raw read consumed by the real tracker
and stillness check. No fixture directly assigns the stillness result, home
success flag, predictor result, servo outcome or reported bytes.

Both proposals in [apply.py](../../firmware/upstream-hardening/followup/20-time-contract/apply.py)
require private scratch and reject the frozen `bounded34a/b` input directories.
They are independently callable as `home(build)` and `predictor(build)`.
The root's separate integration must recheck the linked size; the published
3.4 margin is only 276 bytes with a 256-byte required floor. This lane does not
claim that either or both proposals fit or have been published.

## Homing: sample after work, then decide against the deadline

`main.c:655–680` tests the drive's 300 ms cap at loop entry. Inside the loop it
calls `pump(0)`, cancellation checks, and finally `home_still_for`. If the latter
returns true, `drive_ok` is set without checking that time is still below the
cap. The settle loop at `main.c:697–708` has the same ordering with a 500 ms cap.
The 40/20 ms minimums are lower-bound gates and cannot exclude an expired cap.

The bounded query worker is now reachable through this pump even before home.
Four queries per pass bound foreground work, not elapsed wall-clock duration.
The logical timeout gap does not require assuming a conversion normally takes
300 ms: any interruption or other delay at the tested boundary can cross a
deadline, including near its end. These are adversarial tick schedules, not
measurements of real conversion, SPI, IRQ or camera latency.

The frozen production body reaches `HOME_READY`, resets the tracker reference
and leaves inhibition clear in every following expired-phase case:

| Boundary | Drive elapsed tick | Settle elapsed tick |
| --- | ---: | ---: |
| During query service, exactly at cap | 300 | 500 |
| During query service, just beyond cap | 301 | 501 |
| During encoder stillness read, exactly at cap | 300 | 500 |
| During encoder stillness read, just beyond cap | 301 | 501 |
| During query service at cap, with ordinary counter wrap | 300 | 500 |

All ten cases fail the corrected assertions against frozen source. The proposal
adds a final conjunct to each existing success test, after `home_still_for`:

```c
&& (uint32_t)(millis() - t0) < HOME_MS
```

The settle condition uses `HOME_SETTLE_MS`. A rejected success falls through to
the existing loop deadline and failure path: `HOME_FAILED`, sticky motor
inhibition, pending motion cleared, no reference reset. No new state, timer,
gain, delay, origin or fault code is introduced. Normal no-wrap and ordinary-wrap
homes retain their eight pumps/nine reads and succeed. Both pump and read
completion one tick below either cap still succeed. The original minimums and
stillness thresholds remain intact.

The acceptance contract is specifically **elapsed ticks sampled after the
stillness operation are below the phase cap**. It is not a guarantee of cutoff
at that physical instant. Interruption after the final tick read, time inside
the eventual cutoff, a stopped tick or one complete counter-wrap alias remain
outside such a guarantee. The proposal cannot undo time already spent driving
inside a delayed operation.

## Servo: ordinary wrap works, normal guards precede signed dt

`millis()` returns the volatile unsigned 32-bit counter incremented by SysTick.
Unsigned subtraction correctly handles ordinary boundary crossing, e.g.
`3 - 0xfffffffe == 5` modulo `2^32`. No calendar/host time is used in production.

Reachable STOCK has leg timeout 3000 ms and total timeout 5000 ms; scan/drive
copies change only cruise speed and stop time. Both timeout comparisons execute
at `servo.c:325–331`, before the control step converts `now - t_ctl` at line 355.
Retargeting can restart the leg clock but does not restart the total clock.
Assuming elapsed time since move start has not completed a full 32-bit cycle,
a control step that passes total timeout has elapsed below 5000; its previous
control timestamp was within that same move. Its unsigned delta therefore lies
between 5 and 4999. The signed conversion is representable. A single
`0x80000000` or `0xffffffff` gap on the first loop sample times out before any
nonzero motor drive under the actual STOCK initializer.

The whole-wrap caveat is real and explicitly reproduced: start at tick 0,
control at 5, then tick 4 after a synthetic `0xffffffff` interval. The move's
total elapsed aliases to 4 and the control elapsed becomes `0xffffffff`, cast
to -1 on the host/target conversion convention. A second drive is executed.
The fixture then inhibits at the next sample to bound the demonstration. A
proper coordinate history from 4000 to 3960 remains within the tracker contract;
no invalid configuration is used. This represents a move surviving at least one
49.7-day tick cycle, not normal wrap during a short move. The present proposals
do not claim to solve it. A general whole-cycle alias cannot be recovered from
two 32-bit timestamps alone. A wider clock or a separately justified watchdog
policy would require its own design/evidence, so this is deferred.

## Predictor: exceptional final-pump arithmetic is reachable

The servo brakes, samples its final position and calls `cfg->pump(out->end)`
even when it timed out. `focus_run` ends the predictor only after the servo
returns (`main.c:1272–1274`). Thus the normal servo timeout does not prevent the
predictor from seeing an exceptional interval in that final pump. The actual
report can reach the protocol before `focus_pred_end` clears activity.

The production-path fixture starts at position 4000, requests target 0, and
obtains position 3960 after unsigned elapsed `0xffffffff`. The servo times out
without a drive. The predictor seed is -2048 Q8, but the old signed divisor -1
turns measured velocity into +10240; blending gives +4096. The direction clamp
then leaves predicted position equal to 3960 and reports at rest. The exact
unsigned-positive denominator instead gives fresh velocity zero, blended -1024
and predicted position 3892 at the stored 17 ms period. The captured production
0x06 bytes contain those respective predictions and corresponding motion flags;
lengths/checksums/terminators and current position are checked. This is a
demonstrated software arithmetic distinction under an exceptional synthetic
schedule, **not a camera observation or evidence of a plausible 49-day live
move**.

Audit 15 already established `abs((pos-last_pos)*256) <= 33554432` under the
admitted coordinate contract. Consequently, for every `dt > INT32_MAX`, the
exact quotient of this signed numerator by the positive unsigned interval is
zero. The optional predictor proposal uses:

```c
dt > INT32_MAX ? 0 : ((pos - p->last_pos) * 256) / (int32_t)dt
```

It retains the zero-dt early return, existing blend, target clamp and normal
behavior. This is an exact arithmetic identity on the admitted domain, not a
chosen physical timing threshold. Twelve direct boundary checks cover both
coordinate directions at dt 1, 5, `0x7fffffff`, `0x80000000`, `0xffffff00` and
`0xffffffff`; their oracle uses wider signed division by the positive interval.
The boundary oracle and the real final-pump case form the two additional frozen
failing controls.

This correction intentionally preserves the existing half-weight old estimate,
even after a long gap. It does not establish that a half-decayed seed is a good
physical prediction after days, nor does it establish a desired terminal-frame
motion policy. Clearing/rebasing stale velocity or suppressing the final active
forecast would be separate behavior changes needing an explicit policy.

## Measurement ordering, finite work and remaining physical gates

The servo reads position, then captures `now`, performs control/retarget work,
and pumps last. Inside pump, predictor sampling and reporting happen **before**
the newly reachable query worker, then `em_poll`, then VDD sampling. Therefore
the current query worker's time is not incorrectly attached to the predictor
sample preceding that worker. The next servo iteration samples a new position
and tick after the previous pump. Its velocity delta includes the elapsed pump
work, as intended. Pump obtains its own timestamp for the passed position after
the servo's intervening work; the resulting measurement/timestamp skew already
exists. No physical upper bound on it is proven here. Retarget/abort callbacks
likewise execute after the servo captures `now`; the timeout decision is based
on that captured sample, not a claim of an instantaneous hardware deadline.

At stopped SysTick, home fails after 999999 pump passes. Servo stops at its
million-poll budget and inhibits; the outer `focus_run` returns aborted because
of inhibition. The tests cover both zero drive before the clock stops and a
clock stopping after one nonzero control drive. All million pump calls, including
the servo's final one, return in the fixture. The counters never reset when ticks
resume, so they bound cumulative iterations, not a calibrated stall duration.
Nested peripheral waits have their own finite instruction budgets. None bounds
elapsed wall time if interrupts starve foreground execution, or establishes that
an energized motor is harmless while those budgets are consumed.

PRIMASK critical sections can defer SysTick service. The counter counts serviced
interrupts; it is not a proven lossless wall clock through arbitrary masking or
interrupt overload. Stack/IRQ capacity was separately reviewed in audit 18;
that static envelope supplies no measured latency guarantee. No physical IRQ
duration, SPI/ADC latency, watchdog response, motor rest, optical timing or camera
behavior was measured. No USB enumeration/open/reports, firmware flashing,
updater/app launch, network access or canonical application-state mutation was
performed. Published sources/images/pins remain unchanged.
