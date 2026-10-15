# Audit 23 — exact 3.5 target/time/readiness composition

Independent offline review found **no additional verified production defect** in
this focused composition. The exact proposed 3.5 source passes 40 new composition
cases, seven retained relative-API probes, and four counter-parity executions.
Four additional failing controls show that the composition tests detect removal
of the absolute handoff, either post-sample home deadline, and the positive-time
predictor correction. No production patch is proposed by this lane.

## Bound source and execution

Input is `artifacts/private/absolute35a`, including the release-only legacy
period-sample counter omission. Both runners require the exact manifest hash
`a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de`
and image hash
`04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632`.
They check the image file and all 46 manifest source hashes before execution,
then recheck the manifest and sources afterward. Scratch transformations happen
only in newly created directories under `artifacts/private`.

The [composition runner](../../firmware/upstream-hardening/followup/23-composition35/run.py)
extracts the final main functions for homing, readiness service, command
resolution, focus execution, Scan, Drive, reporting and the real query pump. It
links the full final servo, predictor, protocol/ownership/shutdown, conversion
and live-trace modules and executes the production encoder tracker/reset bodies.
Read-only observation hooks expose the servo result, event/query queue lengths,
scan state and fault reason. A query hook supplies a selected synthetic delay
or protocol input outside the worker's critical section. Sensor SPI, clock,
UART/CS, supply sampling and motor outputs are host substitutes. The host trace
memory pointer expression is parenthesized in this private fixture before
`st_init()` execution; no shared trace fixture or production file was edited.

The fixture starts from follow-ups 17, 19 and 20, but the new executions are
against the final combined source. The exceptional-time cut is the first
feedback read while the predictor is active. It does not reuse the old fixed
read ordinal, which changed when the absolute API removed one encoder read.
Both runners use ASan and UBSan with nonrecovering errors. All 51 positive
executions pass; the four correction-removed controls fail their intended
behavioral assertions. Their outputs and source/fixture hashes are retained in
[composition results](../../firmware/upstream-hardening/followup/23-composition35/results.json)
and [counter results](../../firmware/upstream-hardening/followup/23-composition35/counter-results.json).

## New interaction checks

- **Home into motion.** Commands retained through successful reference lead to
  targets 1000 (absolute), 1400 (relative) and 1320 (defocus), despite a different
  later starting/feedback sample. The relative and defocus instructions resolve
  after the home reference reset. A raw INIT captured during outgoing status 05
  preserves the epoch and readiness, and the queued query is delivered exactly
  once after capture completion. Removing the absolute handoff shifts the
  destination and fails the home-to-absolute case.
- **Deadline with other state changes.** A new Move or relative command during
  query service cannot turn an expired drive/settle phase into ready. Capture
  during the same home attempt does not bypass a later read-time deadline.
  Simultaneous session invalidation or shutdown produces cancellation; encoder
  rejection at the cap produces failed/inhibited state and retains the original
  encoder fault reason. The drive and settle one-tick-before cases still home
  and execute the retained relative target. Removing either final deadline check
  fails the corresponding readiness invariant.
- **Final home reference cuts.** An actual bounded-tracker rejection at the final
  home sample prevents reset/readiness. Session invalidation inside the raw read
  used by reference reset can occur after the reset has begun, but the locked
  final commit still rejects readiness and clears retained motion. This is a
  readiness guarantee; it is not a claim that cancellation rolls back a reset
  already performed. A failed home never retries or drives again through the
  tested `home_service()` calls, even with a fresh request. A fresh request may
  be retained by the existing command policy while the failed state prevents
  execution; this audit does not claim every later request is discarded.
- **Shared starting sample.** Session change, shutdown, Stop and actual encoder
  rejection during the initial sample produce no nonzero servo drive. The Stop
  gets its own event; invalidated motions do not get completion events. Query
  conversion can invalidate an already-running move after an earlier drive;
  the next abort check ends it, and no old query answer is published.
- **Final forecast and capture.** An unsigned `0xffffffff` gap on the first
  feedback sample times out absolute and relative-resolved moves without a
  drive. The final pump retains the commanded target and computes velocity
  -1024 Q8 and forecast 3892 from position 3960 at the default 17 ms frame period.
  The actual status bytes agree. Query-time session/shutdown cuts suppress old
  publication at this terminal pump. Raw capture retains ownership and delivers
  its query once after completion. Restoring the signed denominator fails the
  relative-resolved exceptional-gap case.
- **Wrap and final fault.** Ordinary unsigned wrap retains arrival and relative
  retarget behavior, including the new 1400 destination. A final encoder
  rejection after a stalled move makes the outer execution abort and suppresses
  completion even though the recorded inner servo result remains `SERVO_STALL`.
  The seven prior relative-API probes independently retain runaway, wrong-way,
  retarget, frozen-clock, stale-arrival, final-inhibition and ordinary-arrival
  behavior on the final servo body.

Query replies already sent before a later failure are not retroactively removed.
Inhibition alone is not a universal protocol-history purge; session reset and
shutdown retain their distinct existing policies. The assertions distinguish
these boundaries rather than requiring all earlier history to disappear.

## Deadband internal return versus caller-visible completion

Root requested an additional check of `focus_run()`'s initial read: it checks
`focus_invalid()` before reading, then its deadband branch can return
`SERVO_OK` without another validity check. Nine cases execute actual Move,
Scan and Drive callers, each with injected inhibition, session change or
shutdown at that exact read. All reach the deadband branch, execute no servo
body or motor drive, and publish no completion event. Move and Drive reach the
locked `focus_event()` validity gate; Scan checks validity after the leg before
entering its sweep or finish. An inhibited Scan may retain its existing
`ACCEPTED` state, but does not advance to `SWEEPING` or `DONE`. No false external
completion was reproduced, so this internal return alone is not treated as a
new defect.

The injected inhibition cases are deliberately **not** labeled encoder-overflow
reproductions or returning SPI-fault reproductions. The hardware encoder SPI
wait timeout calls `st_fail()` and does not return; the injected inhibition is a
cancellation-cut model. With the admitted tracker in ±65536 and a modular increment of
magnitude at most 8192, capacity rejection can only retain an old position above
57344 or below -57344. Every production `focus_run()` target is in `[0,5952]`,
including the clamped Scan run-up/run-out and Drive endpoints. Such a rejected
position cannot satisfy the 12-count deadband. A corrupted tracker outside its
admitted domain or a non-production out-of-contract caller is not used to claim
a reachable near-target rejection.

## Release counter: period, I/O and live trace

Source review finds `em_frame_period_n` consumed only by the legacy logged focus
page, under `#ifndef EA9_NO_LOG`. The actual accepted-period assignment and VD
ownership/status scheduling remain outside that guard. The live trace recorder
has no dependency on this legacy counter.

The independent [counter runner](../../firmware/upstream-hardening/followup/23-composition35/run_counter.py)
compares exact final source against a scratch variant restoring **only** the
counter increment. It compiles release and debug variants of each. Seventeen
VD samples include invalid intervals, ordinary wrap and the zero-timestamp
sentinel; a seeded near-overflow counter exercises its uint16 wrap. The real
predictor and extracted production reporter turn each accepted period into the
expected forecast and actual 0x06 bytes.

All four executions produce identical period/forecast, complete wire, CS
assert/release and serialized live-trace output, SHA-256
`8f3b648cc37898348e07e6a2d78803c49678f402eb9920336f4a43aa209fb24b`.
Each sends 34 simulated status frames. No trace memory writes occur during the
VD/report loop or a disallowed flush. A later allowed flush serializes 12 pages
into private in-memory storage, with valid CRCs and identical bytes. These are
host memory writes, not board flash operations. This strengthens root's period
and wire parity evidence with real forecast consumption and live-trace parity.

## Reproduction and qualification limits

```sh
python3 firmware/upstream-hardening/followup/23-composition35/run.py \
  --source artifacts/private/absolute35a \
  --output artifacts/private/astra23-composition-rerun
python3 firmware/upstream-hardening/followup/23-composition35/run_counter.py \
  --source artifacts/private/absolute35a \
  --output artifacts/private/astra23-counter-rerun
```

Use fresh output paths. Final scratch results are
`artifacts/private/astra23-composition-verified/result.json` and
`artifacts/private/astra23-counter-verified/result.json`. This is a focused
finite simulation plus source review, not a repeat or replacement of the
original eleven-lane campaign and not exhaustive interrupt-interleaving proof.
The fixtures inject selected callbacks at observed boundaries; they do not model
arbitrary IRQ scheduling, physical SPI/PWM, optical calibration or camera
behavior. The extraordinary gap is a synthetic arithmetic schedule, not evidence
of a plausible multi-day motor move. Whole-cycle timestamp alias, interrupted
cutoff latency and stopped-clock physical exposure remain unqualified.

The shared-start API intentionally removes one sensor transaction and changes
the initial velocity/guard sample baseline. These results establish target and
software-state behavior, not identical physical timing or transient response.
Compiled stack/image review belongs to root and lane 22; this lane does not
infer margin or stack guarantees from host sanitizers. No adapter enumeration,
USB/HID open/report, motor operation, flashing, app/updater launch, network,
canonical app-state write, published-source/pin mutation or commit occurred.
