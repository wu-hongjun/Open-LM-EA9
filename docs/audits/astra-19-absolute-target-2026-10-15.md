# Follow-up 19 — preserve resolved absolute motion targets

Offline review of exact 3.4 source in `artifacts/private/bounded34b` reproduces
an initial-target discrepancy: `focus_run()` computes `want - here`, then
`servo_move_rel()` takes another encoder reading and adds that delta. The
internal destination therefore becomes `want + second_sample - here`.
An already clamped destination can leave the advertised coordinate interval.
The proposal preserves the resolved absolute destination through a small
shared-sample entry point while retaining the existing relative API.

This is an isolated proposal, not an installed fix or a changed 3.4 release.
Root owns integration, full image margin checks, new versioning and commits.
No hardware, network, app launch, updater, flash or canonical Application
Support action was used. No gains, origin, timing constants or optical tables
were changed. There is no camera, physical stability or safety claim.

## Exact-source evidence

The [runner](../../firmware/upstream-hardening/followup/19-absolute-target/run.py)
verifies every manifest-listed input hash before and after execution, creates
fresh private scratch directories, and runs ASan/UBSan host builds of frozen
source and the staged proposal. The production bodies executed are:

- `focus_cmd_target`, `focus_invalid`, `focus_event`, `focus_abort`,
  `focus_retarget`, `focus_run`, and `focus_exec`, extracted from `main.c`.
- The complete `servo.c`, actual `STOCK` configuration, bounded tracker body,
  protocol dispatcher/command queues/events, ownership/shutdown modules,
  mapping/distance conversions, predictor and startup trace modules.

Only an observation call is inserted into extracted `focus_run` immediately
after the servo returns. Initial commands and retargets enter the actual
dispatcher as checksum-valid Move/Stop frames; session and shutdown cuts use
actual protocol frames. Raw encoder values, time, motor I/O and transport are
host substitutes. The pump samples the real predictor; current-position
reporting is a counted stub with an actual tracker read. This probe does not
execute the whole production pump/query path, board interrupt timing or main
foreground loop. Scan and Drive dispatch are unreachable asserting stubs in
these scenarios. They use the same production `focus_run` in source, but their
two-stage motion sequencing is not claimed as an executed test here.

All raw samples in the target-shift cases lie within `[0,5952]`, so reproducing
the discrepancy does not require a coordinate fault, an impossible integer,
an arbitrary defocus-scale injection or the exceptional tracker endpoints.
Synthetic sample changes establish software behavior, not a physical velocity
or the probability of a particular sensor history.

| Executed case | Resolved target | Frozen internal target | Proposal |
| --- | ---: | ---: | ---: |
| Interior absolute Move, samples 500 then 532 | 1000 | 1032 | 1000 |
| Upper endpoint, samples 5800 then 5832 | 5952 | 5984 | 5952 |
| Lower endpoint, samples 152 then 120 | 0 | -32 | 0 |
| Relative +100 units, resolve at 1000; run at 1020; next at 1052 | 1400 | 1432 | 1400 |
| Defocus +10 units, scale 8, same three samples | 1320 | 1352 | 1320 |
| Relative command clamped at upper endpoint | 5952 | 5984 | 5952 |
| Distance code 0x700 resolved to infinity, samples 500 then 468 | 0 | -32 | 0 |
| Arrival at commanded 1000 after start sample 800 | 1000 | 1200 | 1000 |

The arrival case leaves the frozen servo driving toward 1200 while the
feedback remains at requested 1000, eventually returning `SERVO_STALL`.
The proposal reaches the unchanged dwell/velocity arrival rule and returns
`SERVO_OK`. This does not change the existing event policy that acknowledges
some non-aborted failure outcomes; that separate policy is not reviewed here.

Two further failed controls concern retarget accounting. With the shifted
initial 1032 target, repeating requested 1000 consumes a retarget and resets
leg state. A new target 1008 also spends a retarget, because its difference
from 1032 exceeds the 12-count threshold. With the initial target correctly
1000, neither spends a retarget. The existing small-retarget policy remains:
the predictor can advance to 1008 while the controller keeps 1000, a documented
at-most-12-count difference. This proposal does not alter that deadband.

All 20 proposal cases pass; frozen source fails precisely those ten desired
target/arrival/retarget invariants. The other controls cover no inter-read
movement, ordinary deadband acknowledgement, absolute/relative/defocus
retargets, Stop acknowledgement, session invalidation, shutdown, injected
sticky motor inhibition, and an already-stale session. The cancellation
cases issue no nonzero drive. Session/shutdown/inhibition suppress the final
event; Stop produces its own event. Inhibition is injected through the motor
latch in this test, not reproduced by an additional coordinate-overflow trace.

Seven existing relative-API probes additionally pass against both versions
with exactly identical observed output: runaway, wrong-way, retarget, frozen
clock budget, stale final arrival, final inhibition and ordinary arrival.
These execute the existing lane-06 servo fixture with the exact frozen and
proposed servo bodies. They specifically exercise the retained relative API;
they are not a rerun of the earlier full campaign.

## Why the relative resolution is preserved

Mode 4 and mode 6 intentionally read the encoder in `focus_cmd_target()` to
resolve their relative operand into one clamped absolute destination. The
later `focus_run()` sample is used for the deadband, predictor start and
remaining displacement. Movement between resolution and that later sample
should change the remaining displacement without rebasing the destination.
The proposal preserves this existing choice of resolution instant. It does
not claim that protocol receipt time or another sample would be the correct
external definition for every camera.

In-place retargets already hand `want` to the servo as an absolute value.
Relative/defocus retargets use their resolver sample, and the servo accepts
that destination without adding another sampled-origin correction. The
proposal makes new-leg handoff consistent with this existing behavior.

The locally archived pinned upstream `main.c` and `servo.c` contain the same
two-read construction. A source comment acknowledges the discrepancy and
keeps the predictor bounded by the commanded target; it supplies no contract
requiring the controller destination itself to shift. That distinction is
explicit here: this is a correction to an acknowledged upstream behavior,
not discovery of a typo or a claim that upstream already has this patch.

Local REA evidence independently supports target identity. The recovered
`0x8dd4` operation, represented in `firmware/ea9/src/factory_af.c`, derives the
target from the protocol operand; the sampled position selects direction,
without translating that target by an inter-read displacement. The separate
factory wrapper's `factory_servo_move_to()` accepts an absolute target for the
same reason. These references support preserving an absolute destination;
their controller, coordinate reference and timing remain different. No
factory PID or saved-origin behavior is imported. Comparison file hashes are
recorded with the test evidence; no online lookup was used.

## Staged implementation and remaining integration gates

The [applicator](../../firmware/upstream-hardening/followup/19-absolute-target/apply.py)
accepts only source directories under this workspace's `artifacts/private`:

1. The existing control body becomes
   `servo_move_from(start, target, cfg, out)`. Direction uses `target >= start`.
2. `servo_move_rel(delta, cfg, out)` remains available, samples once and calls
   that common body with `start, start + delta`, preserving relative semantics.
3. `focus_run()` hands over its existing `here, want` pair, shared with the
   predictor. The diagnostic-only park path similarly passes `here, 0`.

The first control-loop iteration still samples feedback and checks inhibition
and abort before any nonzero drive. There is no second control implementation
and no change to gains, deadbands, retarget budget, timers or conversion rules.
The API requires admitted coordinates in the supported arithmetic domain; it
does not make arbitrary out-of-contract C callers safe. The prior arithmetic
certificate's bounds cover the new main handoff (`start` within ±65536 and
target within `[0,5952]`), while the relative wrapper keeps its existing
addition and caller preconditions.

Sharing the start removes one initial encoder transaction and uses the main
sample for the initial velocity/guard baseline. This is a deliberate
consequence of the API, not a claim of identical physical timing or transient
response. The diagnostic park change is source-reviewed; this no-log harness
does not execute its logging path. Root must measure the linked composition,
review affected compiled stack paths and retain the required image/log margin
before publishing a separately versioned executable. Frozen 3.4 remains
unchanged, including its image and pins.

## Reproduction

```sh
python3 firmware/upstream-hardening/followup/19-absolute-target/run.py \
  --source artifacts/private/bounded34b \
  --output artifacts/private/astra19-target-rerun
```

Use a previously unused output directory. Final scratch evidence is
`artifacts/private/astra19-target-3/result.json`; the
[tracked results](../../firmware/upstream-hardening/followup/19-absolute-target/results.json)
also retain runner and local comparison hashes. All manifest source hashes
remain unchanged after execution. These finite software tests do not establish
physical execution latency, optical calibration or camera qualification.
