# AF 2.6 independent correctness audit

October 12, 2026. Audited source commit
`d023745022e9375c54282221be8d6fee4df2ad61`, before the parent’s polish changes.
The review found two reproducible command-boundary faults and one telemetry
issue under injected moving feedback. These are software counterexamples; they
do not establish which path caused the owner’s AF 2.4 failure or quantify
performance on the A7C II.

No USB, HID, updater, flash, camera or device commands were run. No firmware,
test source, frozen candidate, recovery image or application resource was edited
by this audit. The only tracked audit output is this document. Local probes,
binaries, build logs and source hashes are in the ignored directory
`artifacts/af26-night-correctness/`.

## P2: A full completion queue loses a Stop acknowledgement

At the audited commit, `firmware/ea9/src/emount.c:1073` gives the event FIFO
two slots; `em_post_event` at line 1078 silently discards the next event when
both are occupied. `firmware/ea9/src/main.c:1181` releases an idle Stop and
increments its counter without learning that its acknowledgement was discarded.

The production-main probe executes two four-count no-drive Move completions
before the next frame-sync edge, then calls the ordinary idle Stop dispatch.
After three status pairs, both Move events have appeared and no Stop event
has appeared:

```text
stop-fifo idle_stops=1 transmitted_events=2 transmitted_stop_ack=0
```

Equivalent call sequence after a successful reference in the host harness:

```c
struct em_focus_cmd tiny = {
    .op = EM_OP_MOVE, .target = focus_counts_to_em06(4)
};
focus_exec(&tiny);
focus_exec(&tiny);
struct em_focus_cmd stop = { .op = EM_OP_STOP };
focus_exec(&stop);
/* Deliver three VD edges and inspect each subsequent 0x06 tail. */
```

The motor does stop. The fault is a missing protocol acknowledgement, which
can leave the camera’s command progression waiting or retrying. This is a
producer/consumer capacity failure, not a checksum or ISR race. Increasing
the queue alone postpones the failure.

Recommended correction: guarantee admission of Stop, with an explicit policy
for replacing obsolete Move completions and coalescing duplicate Stop events.
Keep at most one event per status frame. Test a full FIFO, repeated Stops,
Move arrivals while Stop is pending, and FIFO draining. Do not let a later
Move completion evict the last pending Stop acknowledgement.

## P2: Repeated identical targets exhaust the retarget budget

`firmware/ea9/src/factory_servo.c:95` treats every successful retarget callback
as a new redirection. Lines 98–107 consume the sixteen-retarget limit and
reset the leg deadline, even when the quantized target is unchanged.
`firmware/ea9/src/main.c:902` returns such repeated absolute targets as
successful retargets. A seventeenth identical request becomes a hard
`SERVO_TIMEOUT`; `firmware/ea9/src/af_control.c:13` then permanently inhibits
later motion for that boot.

The production-main probe commands full travel and injects the same valid
absolute Move every sixteen simulated milliseconds. The control sends the
same initial Move once. Neither case contacts a simulated end stop:

```text
repeat fault=2 elapsed_ms=332 position=4232.627 retargets=16 outcome=2 stop_contacts=0 duty=0
single fault=0 elapsed_ms=437 position=5800.808 retargets=0 outcome=8 stop_contacts=0 duty=0
```

Elapsed time in this inherited simulator advances when code asks for time;
these values are not hardware timing measurements. The important comparison
is permanent fault versus an eligible bounded deadline, solely from repeating
the same target. No live capture establishes that the A7C II produces this
precise repeated-target sequence.

Recommended correction: compare the admitted, quantized next target with the
current target before consuming a redirection budget or resetting the leg
deadline. Preserve Stop/replacement polling, the total deadline, distinct-target
limit, fresh feedback guards and latest command ownership. Do not deduplicate
relative operands without resolving them first: the same relative operand can
represent different absolute destinations. Keep the pure instruction-tested
factory PID unchanged.

## P2: Predictor lifetime is used as measured motion state

`firmware/ea9/src/main.c:777` defines motion as `ahead != counts`. At motion
termination, `focus_run` calls `focus_pred_end` at line 962, which zeros velocity
and disables the forecast (`firmware/ea9/src/focus_pred.c:47`). Subsequent
valid position samples then report at rest even when feedback is still changing.
The same coupling can hide real motion during a reversal, because the predictor
clips motion pointing away from the new target to zero at lines 86–96.

The inherited mechanics retain momentum after brake application. The
production-main probe finishes a full-travel command, then samples/report its
idle feedback. It returns with positive residual velocity, immediately reports
at-rest `0x82`, and subsequently moves another 89 counts:

```text
coast first_pos=5800.808 first_velocity=5.135 first_contacts=0 idle_pos=5889.888 idle_velocity=0.000 contacts=0 first_stop_ms=0 fault=0 first_motion_flag=0x82 motion_flag=0x8a
coast first_pos=50.471 first_velocity=1.466 first_contacts=0 idle_pos=63.348 idle_velocity=0.000 contacts=0 first_stop_ms=0 fault=0 first_motion_flag=0x92 motion_flag=0x92
```

The second case is a forty-count target. Neither case contacts a simulated
stop. This does not prove an unsafe physical coast or justify guessed braking
gains. It does show that the software’s “at rest” estimate is derived from a
command predictor rather than measured displacement. The interpretation of
every status bit by the camera remains a protocol inference.

A conservative modular correction is a separate, frame-paced measured-position
observer. Feed it only validated encoder samples, publish observed displacement
and direction independently of the active predictor, and retain observed motion
across predictor termination and command reversal. A complete unchanged
observation interval can clear its motion estimate; missing/stale observations
must not fabricate rest. Reset the observer when the reference is committed.
Reuse the negotiated frame cadence and protocol position resolution, without
altering PID, brake duty, timeout or optical completion policy.

Regressions should cover changing idle feedback with an inactive predictor,
feedback moving opposite a new target, unchanged frames, skipped frame edges,
reference reset and rejected feedback. Sensor jitter on the owner’s unit has
not been measured. An observer noise threshold or physical settling criterion
must remain explicitly unqualified; do not invent a calibration during polish.

## Validation, scope and reproduction

The audit reran, under AddressSanitizer and UndefinedBehaviorSanitizer, all
27 scripted factory-wrapper cases, 21 production-main hardening scenarios,
11 factory lifecycle scenarios, and the opaque stock-query test (56
operand/length/sequence cases plus two missing-operand cases). All passed.
The five new probe cases passed their assertions that the counterexamples and
the single-request control occurred. Passing existing tests therefore did not
cover the newly found behaviours.

Local reproduction at the audited commit:

```sh
artifacts/af26-night-correctness/boundary stop-fifo
artifacts/af26-night-correctness/boundary repeat
artifacts/af26-night-correctness/boundary single
artifacts/af26-night-correctness/boundary coast
artifacts/af26-night-correctness/boundary coast40
```

The probe source is `artifacts/af26-night-correctness/boundary.c`, SHA-256
`29cef1b233b5cb473b9e108362ad5c947b157671eb1620c2998fa4965643a43b`.
`results.json` records results and source hashes; its recorded main, emount
and factory-wrapper source hashes were separately checked against the audited
Git commit. Rebuild the probe with the production modules and inherited
`hosttest/sim_motor.c` and `hosttest/shim.c`, defining `EA9_FACTORY_AF`,
`EA9_SIM_MOTOR` and `EA9_NO_LOG`, with dead stripping and
`-fsanitize=address,undefined -fno-sanitize-recover=all`. It includes production
`main.c` with its entry point renamed, as the existing lifecycle/hardening
harnesses do. These local binaries intentionally remain diagnostic artifacts;
the parent’s successor regression tests are the versioned reproduction path.

The reviewed positive protections include complete declared-frame checksum
admission before motor-command parsing, declared payload bounds, opaque `0x34`
operand bounds, IRQ-preserving command/query/request snapshots, sticky I/O and
mechanical faults, widened relative/defocus target arithmetic, feedback bounds
before prediction arithmetic, finite peripheral waits and clock-independent
poll ceilings, and shutdown inhibition against recursive motion ownership.
No new sensor/PWM fault-restart regression was found in the exercised cases.

The factory reconstruction remains partial. The pure PID/target/timer functions
have strong finite original-instruction evidence, but production uses a
foreground scheduler, an experimental reference/homing policy, braking and
packet/event orchestration that differ from factory. Scan/Drive speed handling,
optical rows and distance models, real interrupt ordering and loaded bus timing,
physical position calibration, metering and camera acceptance remain separate
qualification obligations. The factory Stop state machine also emits the prior
operation event before its Stop event (`research/stock-1.8/stock_model.c:194`);
the candidate’s one-Stop policy is a known orchestration difference, not a new
proof that a particular camera requires both.

The parent will integrate the two command-boundary fixes into a separate AF 2.7
candidate and preserve frozen 2.6. The moving-telemetry finding requires the
measurement limits above to be retained in any follow-up. This audit does not
authorize or perform a hardware installation.
