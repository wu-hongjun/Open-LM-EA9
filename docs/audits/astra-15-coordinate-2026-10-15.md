# Audit 15: bounded software coordinate arithmetic

2026-10-15. Independent offline source/math review of the proposed coordinate contract, against frozen `firmware/upstream-hardening/build/final-33a/src`. All 46 `manifest.json` source hashes verified. The frozen source does **not** yet contain this contract: its tracker rejects only `int32_t` overflow. This report assesses the proposed tracker replacement with unchanged servo and predictor. The original full-uint16-scale wide-target alternative is preserved below. A subsequent field-writer audit also proves that the existing 32-bit main target construction is sufficient for reachable production state, so the wide-target change is optional. Root owns integration/build verification.

**Finding:** the proposed inclusive tracker domain `[-65536,65536]` is sufficient to keep the reviewed production coordinate, servo, predictor, and report arithmetic within its integer ranges, including the existing main target expressions because the reachable defocus scale is 8. Computing main relative/defocus targets in `int64_t` before clamping is a sufficient broader alternative, but is unnecessary for this fixed configuration. No 64-bit servo division or further signed-overflow guard is required for these production configurations. The proof deliberately allows independent endpoint readings; it does not assume an encoder velocity, physical end stop, calibrated origin, mechanical gain, or successful guard response to every physical failure.

This is a conditional arithmetic result, not device qualification. Arbitrary external calls with invalid `servo_cfg`, memory corruption, altered focal-length/configuration constants, and bypasses of the tracker contract are outside its premises. Elapsed-time conversion and a real two-read target discrepancy are explained below; arithmetic correctness does not remove those behavioral distinctions.

## Scope and reproducibility

Only source reads and local audit artifacts were used. No network, Git, hardware discovery, USB/HID, updater, flashing, motor operation, or canonical-state changes were performed. Earlier audit-13 tests were not rerun.

Run:

```sh
python3 firmware/upstream-hardening/followup/15-coordinate/check_ranges.py
```

The certificate verifies the 46 source hashes and actual configuration assignments, enumerates all 16,384 modular raw differences, checks 98,301 points at/adjacent to the tracker decision thresholds, checks every scan/drive magnitude mapping, and computes conservative integer bounds. Results are recorded in `firmware/upstream-hardening/followup/15-coordinate/range-results.json`. This is a mathematical/source certificate, not exhaustive firmware execution; the interval/induction arguments below justify the unenumerated states.

## Preconditions verified from the actual sources

`main.c:363` defines STOCK with stop 30 ms, cruise 25,000 counts/s, feedforward divisor 40, offset 134, tau 26 ms, proportional divisor 50, boosts 12/8 capped at 800, duty floor 200 and maximum 1280, tolerance 12, settle 40, aim-ahead 0, noise 8, stall 300 ms, leg timeout 3000 ms, total timeout 5000 ms, at most 16 retargets, retarget minimum 12, reverse brake 20 ms above 15,000 counts/s. These are assignments, regardless of conflicting historical comments.

`focus_scan` and `focus_drive` copy STOCK and change only cruise and stop: cruise lies in `[4000,40000]`, stop is 8 ms (`main.c:1404–1444`). Their endpoints are clamped to `[0,5952]`. The old PARK definition/call is excluded by the frozen build's `EA9_NO_LOG` flag; it is not an extra production configuration. Its arithmetic would also fit these conservative bounds, but it is not needed for this result.

`focus_map.h` defines travel 5952, four counts/unit, and protocol origin 4144. `emount.h:322` fixes focal length to 500 (50 mm). `emount.c:256,1021` initializes frame period to 17 and assigns only measured periods 10 through 30. No production writer assigns an arbitrary period. `em_focus_cmd.delta` and `drive_vel` are signed 16-bit; scan extents/positions are unsigned 16-bit (`emount.h:506`). `em_defocus_scale()` returns unsigned 16-bit. The broad alternative allows its entire type domain; the production proof additionally establishes the actual stored scale of 8 from all field writers, below.

## Tracker invariant and fault path

Let `L=65536`. Static initialization and `abs_encoder_track_reset()` set `g_track=0`. Raw samples are 14-bit. The masked difference is 0 through 16383; subtracting 16384 exactly when it exceeds 8192 produces `d in [-8191,8192]` (`abs_encoder.c:96`). The asymmetric positive half-turn is intentional in the existing source.

The proposed pre-add test is:

```c
if (g_track > L - d || g_track < -L - d) {
    st_inhibit_fault(ST_ENCODER_OVERFLOW);
    motor_inhibit();
} else {
    g_track += d;
}
```

Both thresholds fit signed 32-bit (`L-d` in `[57344,73727]`; `-L-d` in `[-73728,-57345]`). Under the invariant, rejection is equivalent to the mathematical sum lying outside the inclusive domain. Accepted sums are in the domain; rejected samples retain the previous coordinate. Induction therefore establishes the invariant without ever evaluating an overflowing addition. Equality at either limit is accepted.

As in frozen code, `g_track_last` advances even on rejection. Later calls can accept a new bounded coordinate; “retain last coordinate” means the rejected call, not a permanently frozen sensor value. This does not weaken the invariant. `motor_inhibit()` is sticky until restart: there is no clearing assignment, pin attachment checks it, and drive/brake return when inhibited (`motor.c:7–23,39,135,143`). Resetting the tracker to zero does not clear motor inhibition.

Fault reason 16 is already `ST_ENCODER_OVERFLOW`. `st_inhibit_fault()` records only the first nonterminal fault in RAM (`startup_trace.c:132`), so it records 16 if no earlier reason exists, otherwise preserves the earlier reason. The proposed branch does not write NVM. Servo tests inhibition immediately before/after its loop sample; a fault inside the retarget callback is caught by the abort hook before the control step. The final sample can fault; bounded coordinates still reach the pump and an otherwise-OK result becomes aborted. `focus_invalid()` also includes inhibition. These paths preserve the arithmetic invariant even when they stop motion before a usual control step.

## Main targets, scan, and drive

For the broad alternative that accepts any unsigned-16-bit scale, relative command construction must cast **before** multiplying/adding, retain the wide value through the clamp, and narrow only after the result lies in `[0,5952]`. For the actual reachable scale of 8, the unchanged 32-bit construction is sufficient; see the field-writer proof below. Merely assigning an already-overflowed 32-bit expression into an `int64_t` is insufficient.

For the largest signed-16-bit magnitude and unsigned-16-bit scale,

`abs(here + delta*scale*4) <= 65536 + 32768*65535*4 = 8589869056`,

which comfortably fits `int64_t`. No division is needed. Plain relative commands also fit 32-bit under this contract, but the same wide construction is consistent and sufficient. Absolute position conversion has a preclamp multiplication no greater than `(65535-4144)*4=245564`; distance-code targets return `[0,5952]` for the fixed production focal length.

For centered scans, centre is `[0,5952]`, so preclamp high is `[0,268092]` and low is `[-262140,5952]`. The source clamps low below zero and high above travel; their other sides were already bounded. Endpoint scans start with both endpoints in `[0,5952]`. The later ordering check, near-end comparisons, run-up 300, run-out 240, and final endpoint clamps all fit signed 32-bit. `here-lo` and `hi-here` have magnitude at most 71488.

Scan speed uses `mag<=127`, with unsigned product at most 4,572,000. Drive negates a promoted signed-16-bit velocity: `-(-32768)=32768` fits the 32-bit `int`, then clamps magnitude to 32767. Its unsigned speed product is at most 1,179,612,000. Both expressions produce cruise values in `[4000,40000]`; their divisors 127 and 32767 are nonzero.

## Distinct sensor reads and the servo range proof

In `focus_run`, `here in [-L,L]` and commanded `want in [0,5952]`, so `delta=want-here in [-65536,71488]`. `servo_move_rel` reads a **new** `start in [-L,L]`, then computes `target=start+delta`. Do not incorrectly assert that this internal target remains `[0,5952]`.

Treating the two reads as independent gives the conservative target interval `[-131072,137024]`. Every retarget from `focus_retarget()` is clamped back into `[0,5952]`. Thus this target interval is invariant over the move. Aim equals target because aim-ahead is zero. Position, stored position, leg start, and last movement reference remain in `[-L,L]`.

| Expression/state | Conservative absolute bound |
| --- | ---: |
| Initial/retargeted servo target | 137,024 |
| `aim-pos`, `target-pos`, overshoot | 202,560 |
| `(aim-pos)*1000` | 202,560,000 |
| `pos-pos_ctl`, `pos-leg_start` | 131,072 |
| `(pos-pos_ctl)*1000` | 131,072,000 |
| `v_meas`, allowing any nonzero signed divisor | 131,072,000 |
| `abs(v_meas)*2` | 262,144,000 |
| `v_target`, `v_prev` | 40,000 |
| `v_target-v_meas` | 131,112,000 |
| `tau_ms*(v_target-v_prev)` | 2,080,000 |
| `v_ff`, allowing any nonzero signed divisor | 2,120,000 |
| Duty before clamp, including offset and boost | 2,676,174 |

All are below `INT32_MAX`; all relevant negative values are above `INT32_MIN`, so absolute-value negations are defined. Positive stop/divisor constants exclude zero division. Under normal positive elapsed time, servo dt is at least 5 and bounds are tighter; the table intentionally does not require that tightening.

`nt-target` and its absolute value are at most 137024. `target +/- 600`, `leg_start +/- 120`, and `last +/- 8` remain far inside signed 32-bit. Boost starts at zero, increases by at most 12 before clamping to 800, and decreases by 8 before clamping to zero; even transient values are `[-8,812]`. The duty clamp produces `[-1280,1280]`, so negation and cast to motor `int16_t` are exact. Arrival-count and retarget counters have explicit saturation/limits. All branches preceding the control step, including runaway, wrong-way, stall error, abort, holding, and rebase, use the same bounded states.

The actual consecutive-read target discrepancy is tighter than the independent-read proof: with no intervening tracker call/reset, `start-here in [-8191,8192]`, hence initial target is `[-8191,14144]`. A valid bounded example is `want=5952`, `here=0`, then `start=8192`: servo aims at 14144 while the predictor retains commanded target 5952. This is an existing behavioral consequence of the relative API, **not** an overflow counterexample. The contract does not enforce that every internal servo target lies within advertised travel. If that were a separate requirement, pass an absolute target to the servo or otherwise construct its target from the same position sample; do not claim that coordinate capacity provides that property. No velocity/physical plausibility assumption is used to discard this example.

## Predictor and reporting

`focus_pred_begin()` initializes last position from a bounded read, target from `[0,5952]`, and velocity to +/-2048. Retarget changes only the bounded target. Samples update position only from bounded readings. For any nonzero signed elapsed divisor,

`abs(fresh)=abs((pos-last_pos)*256/dt) <= 131072*256 = 33554432`.

If the old estimate is in that same interval, `fresh-old` has magnitude at most 67108864 and its rounding adjustment at most 67108865. `blend` moves to a rounded midpoint lying between old and fresh, so induction keeps the estimate within +/-33554432. This also proves the final `old+...` addition is defined. Multiplication by the accepted frame period is at most `33554432*30=1006632960`, before division by 256. `left=target-pos` fits; the sign/distance clamp confines `pos+d` to the interval between position and target, hence within `[-65536,65536]`. End clears active and velocity; the idle predictor returns the bounded position unchanged.

The servo's last pump occurs before `focus_pred_end`, even on failure. Its final position remains bounded, so the same induction applies. Reports outside moves use an inactive predictor. Separate reads taken by retargeting do not invalidate the proof: measured predictor differences use independent bounded endpoints, not an assumed one-step delta.

`focus_report_at` subtracts two bounded current/previous coordinates, at most 131072 in magnitude, then divides by four before `em_push_velocity`. That function accepts `int32_t` and clamps to `[-128,127]` before narrowing (`emount.c:1074`), including the possible +32768 input. Position-to-protocol conversion clamps before dividing. `(uint8_t)(counts/256)` is defined modulo 256; it is not a signed-overflow hazard or evidence of physical calibration.

Distance reports clamp counts before extension conversion. With the actual fixed 50 mm focal length, the largest `f_mm*(f_um+x_um)` is 2,725,000 and the largest rounded extension numerator is 26,786,976. Distance division checks zero extension first. Inverse distance uses at most `50*50000=2500000`, checks `d_mm>50` before division, and bounds extension below 4500 before converting to counts. Log normalization uses Q14 multiplication below `2^30`; exp Q14 products remain below `2^32`, with exponent guards before shifts. None depends on the preclamp raw coordinate being near physical travel. Arbitrary caller-selected focal lengths are not the production call graph reviewed here.

## Clock wrap, narrowing, and limits of the conclusion

`millis()` is an unsigned 32-bit tick incremented by SysTick. Every elapsed subtraction is unsigned, so ordinary wrap works: `3 - 0xfffffffe` is 5 modulo `2^32`. Servo tests unsigned dt >=5 before converting to signed; predictor returns on unsigned dt zero. On the target's usual two's-complement unsigned-to-signed conversion, neither path can divide by zero after narrowing, and neither numerator can be `INT32_MIN`; even a narrowed divisor of -1 fits the conservative bounds above. `out->ms` narrows unsigned elapsed time to `uint16_t`, which is defined modulo 65536.

A duration exceeding `INT32_MAX` before signed conversion is implementation-defined in C and, with the usual wrap conversion, becomes negative. Normal uninterrupted servo execution is additionally limited by 3000/5000 ms guards before each control step; stopped SysTick leads to finite poll-budget exit. These facts are not a measured interrupt-latency guarantee. The coordinate contract does not establish correct velocity direction after an extraordinary >24.8-day sampling gap or a whole-counter-wrap alias. The arithmetic proof remains valid for every nonzero wrapped signed divisor, but it is not a proof of those timing semantics.

If a separate requirement demands portable and explicitly handled long-gap semantics, an exact additional guard is to retain the unsigned delta, check `dt > INT32_MAX` before any cast, and rebase/clear predictor velocity (or abort/inhibit a servo control gap) before returning. Such a guard needs a defined behavior policy, not a guessed physical timing limit. It is not needed to close the reviewed signed-overflow domain on the current production configuration.

No signed-overflow counterexample was found under the proposed contract. The two-read target discrepancy and long-gap timing conversion are explicitly preserved limitations. Integration must still verify that the tracker guard runs before addition, the defocus high-byte/configuration invariant remains true (or wide targets clamp before narrowing), no other writer can violate the tracker/period/config invariants, and the built source matches the reviewed proposal. No claim of device safety, calibration, or camera qualification is made.


## Additional production proof: unchanged main expressions and scale writers

Root requested this refinement after the wide-target variant reduced available image margin. Source-only review supports retaining the frozen main target expressions when adding the tracker bound. Run `python3 firmware/upstream-hardening/followup/15-coordinate/check_scale.py`; the writer inventory is in `scale-results.json`. It rechecks the 46 source hashes, parses the actual template and fixup table, enumerates direct stores and `put16` destinations, and checks the setter call/ladder. It complements manual alias/call review, rather than pretending to be a general C analyzer.

`EA9_OFF_06=0` and `EM06_DEFOCUS=0x13`. The generated `ea9_data` template has bytes `[0x13,0x14]=[0x20,0]`. `em_init()` calls `em_set_focal_length(EM_FOCAL_MM10)` with 500; `focal_step(50)` returns 8. The setter writes only byte 0x13, so the pair becomes `[8,0]`. It executes before initial request capture/dispatch and before main focus processing. Searching every production C source finds exactly one call to `em_set_focal_length`, this initialization call. A new protocol session does not introduce a new setter or rewrite the high byte.

The exhaustive source writer categories are:

| Writer category | Destination relevant to exclusion of 0x13/0x14 |
| --- | --- |
| `em_set_focal_length` | The sole store to 0x13; writes 8 in production |
| Direct message-06 state/position/sequence stores | 4, 6, 7, 8, 9, 0x1A, 0x1B, 0x1F, 0x20..0x23 |
| Velocity-history pointer alias `h` | 0x26..0x2C, seven bytes |
| Event/query tail stores | Start at 0x2D; lengths only increase from 48 |
| `put16` and other packet/optical-row stores | Other packet regions, all above 0x14 |
| Generic `frame[f->off]` fixup alias | All eight fixed rows resolve to 0x96, 0x356..0x359, or 0x30E..0x310 |
| `em_transmit(frame,len)` | Copies to private `snapshot`; checksum, length, and footer edits affect that snapshot only |

The packet table is const. The generic reply dispatcher chooses its packet from that table, and its only template mutation uses the eight const fixups. No fixup targets message 06. Even the aperture RX fixups, which production skips, are outside the scale bytes. Other source files contain no writer or escaping mutable alias to `ea9_data`. The event/query tail begins at 0x2D and uses idle/max lengths 48/56; its offsets cannot move backward into 0x13/0x14. The scope here is the low-address scale invariant, not revalidation of audit-12 behavior.

Thus high byte 0x14 stays zero, and the reachable post-init scale stays 8. The unchanged left-associative defocus multiplication has the following bounds at every intermediate step:

- `delta*8` lies in `[-262144,262136]`.
- Multiplying by four lies in `[-1048576,1048544]`.
- Adding bounded `here` lies in `[-1114112,1114080]`.
- Main then clamps to `[0,5952]` before any caller uses the target.

Plain relative construction lies in `[-196608,196604]`. No signed intermediate overflows. Even a conservative invariant of merely zero high byte, allowing any low byte 0..255, gives absolute preclamp bound `65536+32768*255*4=33488896`, still below `INT32_MAX`. The pre-init template value 32 also fits; execution order is needed to prove the exact value 8, but not to rescue arithmetic.

Consequently, a test that injects arbitrary scale 65535 into the getter storage is outside the reachable production invariant, rather than a valid counterexample to keeping main unchanged. A future writer to the high byte, a packet layout change, or a new API that accepts arbitrary 16-bit scale must reopen this proof or use the preserved wide-target alternative. No physical focal calibration is inferred from the software constant.

## Composed-source review: coordinate + query-12 + flow-16

Reviewed exact source directory `artifacts/private/astra-root-domain-flow-measure/src` after root requested validation of the prospective separate 3.4 composition. This is source validation of that private composition, not validation of a final packaged image. `check_composed.py` and `composed-results.json` in this audit's folder pin the exact four changed file hashes and verify all other manifest files against frozen 3.3. No unchanged range enumeration was repeated.

The checker passes: 42 of 46 manifest-listed source files are byte-identical, including servo, predictor, mapping, distance conversions, packet templates, motor inhibition, clock, and relevant configuration headers. The changes are exactly the bounded tracker guard/header, the replacement query worker plus one pump call in main, and the answer-capacity gate in `em_take_query`. Removing the two reviewed main edits reproduces frozen main byte-for-byte; removing the new queue gate reproduces frozen emount byte-for-byte. Thus the target construction, STOCK/scan/drive configuration, retarget path, final servo handling, scale-writer inventory, and report arithmetic previously proved remain applicable without a new assumption.

Run the bounded composition check:

```sh
python3 firmware/upstream-hardening/followup/15-coordinate/check_composed.py
```

**Tracker and target result:** the implemented guard is precisely `g_track > ENC_TRACK_LIMIT-d || g_track < -ENC_TRACK_LIMIT-d` before addition, with `ENC_TRACK_LIMIT=65536`, unchanged fault/inhibit branch, unchanged zero/reset, and unchanged last-raw update. The existing main expressions remain 32-bit. The scale is still exactly 8 after initialization, because neither new worker nor capacity gate writes packet scale storage; the entire emount writer set is otherwise unchanged. All coordinate/target/servo bounds above therefore hold for this exact composed source.

**Worker conversion result:** every iteration declares `operand` and `value` as `uint16_t`. The position-to-distance path first maps any operand to counts `[0,5952]`, then computes a bounded distance code at fixed focal value 500. The other path first maps any distance operand to counts `[0,5952]`, then returns protocol position `[4144,5632]`. Both return values fit `uint16_t`; there is no new signed narrowing. Before the infinity-code branch, the inverse conversion uses `code<1792`, so its signed Q6 expression is `[254,2045]`, well within `int32_t`; the existing exponential exponent guard handles its upper end. These are the same pure functions and operand domains already covered above, now reached while a servo/home pump is active.

The new worker contains no encoder read/reset, predictor operation, motion call, target write, focal setter, or `millis()` call. Its conversions do not call the worker or `pump`, and its enqueue/dequeue functions do not invoke motion. The new call is nested on the existing foreground control stack, not recursive query processing. Its `uint8_t` budget runs 0 through 3, increments at most to 4, and stops. Answer/query indices remain bounded by `EM_QUERY_Q=4`; the new capacity check can only refuse a dequeue. It introduces no additional unbounded numeric producer.

**Pump timing result:** queries execute after predictor/report updates and before `em_poll()`. They can lengthen the interval before the next servo sample. The arithmetic proof allows independent endpoint coordinates and any nonzero signed dt, so it does not require a previous pump cadence, maximum physical velocity, or a measured conversion duration. A stopped tick still avoids predictor division at dt=0 and servo division before unsigned dt>=5. Normal clock wrap and the separately documented extraordinary-long-gap semantics remain unchanged. This review does not establish a maximum electrical response time or sampling adequacy for unwrapping physical motion.

**Sensor-fault and return paths:** a tracker rejection before a servo control step leaves the previous admitted coordinate, latches inhibition, and the loop aborts before arithmetic that could drive. If a rejection occurs on the servo's final read, the final pump still samples/reports only the retained bounded coordinate; the predictor may still be active until `focus_pred_end`, but its independent-endpoint induction applies. The added worker then observes inhibition under its entry lock and returns without dequeue/publication. Frozen motor drive/brake/remux gates continue to honor sticky inhibition.

A fault detected by `focus_report()` immediately before the idle worker similarly prevents that worker's query action. A homing pump can publish an operand-only query before a later encoder sample discovers a fault; the earlier answer depends on its operand, not the unread sensor state. Once inhibition has been latched, subsequent worker entry rejects it. If a shutdown/session change interrupts an unlocked conversion, the publication lock checks session, handshake, abort, shutdown, and motor inhibition again before posting. The worker cannot itself discover an encoder-capacity fault during a conversion because it performs no encoder read, and no other query context is introduced by this overlay.

No new arithmetic counterexample or required numeric guard was found in this composition. The previously documented two-read target discrepancy and extraordinary timer-gap limitation remain. The result applies to the exact four changed hashes in `composed-results.json`; any subsequent candidate-source change must be compared against them or reviewed before reusing this conclusion. Build/link, image packaging, stack-budget validation, and device qualification remain separate from this source/math result.
