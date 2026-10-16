# Astra 33 — bounded first motion fault evidence proposal

October 15, 2026. **The staged observation code captures the coordinate and
controller state that selected the first wrong-way/runaway guard. Synthetic
control/protocol parity passes; this is not a shutter remedy or hardware
qualification. Whole-image fit remains a root/lane35 integration gate.**

This is newly authorized offline work following the
[3.6 failure analysis](astra-32-af36-capture-failure-2026-10-15.md) and
[closed campaign](../evidence/firmware-hardening-final-2026-10-15.md). The earlier
campaign is not restarted. The exact source is
`artifacts/private/handoff36-repeat`, matched against all 46 source entries in
the [3.6 manifest](../../firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json)
before and after testing. The frozen image SHA-256 is
`d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`.

## Staged implementation

The [applicator](../../firmware/upstream-hardening/followup/33-motion-tracing/apply.py)
requires the exact frozen `main.c` and `servo.c` hashes and writes only a private
source copy. It adds
[motion_trace.c](../../firmware/upstream-hardening/followup/33-motion-tracing/motion_trace.c)
and its [fixed-layout header](../../firmware/upstream-hardening/followup/33-motion-tracing/motion_trace.h).
Root owns the production composition; lane35 owns the persistence writer and
lane34 owns capture/queue/TX observations. This lane changes no shared
production file, release image, manifest or app resource.

The collector is a fixed 144-byte main-context RAM record, plus three bytes of
pending command metadata (147 object BSS bytes, subject to link alignment).
Its four 12-byte samples form a latest-sample ring. There is no allocation,
sensor call, NVM call, IRQ hook or fault-clear operation in the collector. Its
only undefined ARM symbols are `memset` and `millis`. The begin clear is bounded
to 144 bytes; per-sample and per-state updates have no data-dependent loop.

The record contains:

- The accepted operation, normalized raw operand, original resolved target and
  starting coordinate. Relative/defocus operands come from the signed delta
  field, not the unrelated target field. Initial time is servo/deadband entry,
  not wire reception or an observed shutter time.
- The current resolved target and leg start, requested leg direction, accepted
  retarget count, reversal-rebase and brake-hold state. Consuming a small
  retarget does not relabel it as a servo-accepted target. The accepted command
  metadata advances only when the actual servo retarget count advances.
- Four recent existing loop reads, each with its wrapping millisecond timestamp,
  unwrapped encoder coordinate, preceding `motor_drive` argument, retarget count
  and state interpreted by the guard after retarget/rebase processing. Duty is
  a software request, not an independently measured bridge output or polarity.
- The exact guard coordinate and timestamp, guard reason/outcome, target, start,
  sign, state and duty. `st_motion_finish` freezes these **before the existing
  inhibition and final encoder read**. The later final read cannot replace the
  coordinate that actually crossed the guard. Guard thresholds and comparisons
  are unchanged: strictly beyond 120 behind the leg start, or strictly beyond
  600 past the target, with the existing rebase condition.
- A separate completion disposition. Main records publication attempt or
  suppression; an aborted move is recorded without manufacturing success.
  Lane34 can advance ordinary observations to queue acceptance/drop and TX
  return using the agreed API. After a frozen fault, the first subsequent
  disposition sticks; later unrelated commands or shutdown cannot replace it.
  A TX function return still does not establish camera receipt.

No encoder read was added. The loop sample hook uses the existing `pos` and
`now`; the leg hook uses the existing controller locals. The existing motor
calls occur exactly once at their original sites, followed by RAM-only argument
observations. Gains, polarity, origin, arithmetic, guard predicates, cancellation,
waits and motor-inhibit behavior are unchanged.

## Source-bound tests and rejected controls

[The runner](../../firmware/upstream-hardening/followup/33-motion-tracing/run.py)
compiles the pinned production servo and extracted exact production focus
functions with ASan/UBSan. The parser, owner, shutdown, mapping, distance and
predictor modules are linked from the same source copy. Hardware boundaries
supply synthetic coordinates/frames. Test sources and
[results](../../firmware/upstream-hardening/followup/33-motion-tracing/results.json)
are public synthetic material only.

| Evidence | Result |
| --- | --- |
| Seven servo cases | Positive/negative wrong-way; positive/negative runaway; reversal/rebase turn; rebase expiry; ordinary abort. Exact equality boundaries remain allowed, the next count trips. Guard endpoint differs deliberately from the later final read. |
| 22 focus cases | Absolute, relative, defocus, distance, travel clamps, arrival/deadband, session/shutdown/Stop/inhibit/stale cancellation, accepted/repeated/small retargets, wrong-way and runaway. |
| Seven existing relative-path cases | Finite work under frozen clock, stale arrival, post-read inhibition, ordinary completion and guard/retarget behavior remain equal. |
| Control parity | All seven servo and 22 focus cases compare serialized motor calls, synthetic sensor returns and pump coordinates byte-for-byte with frozen source. Focus comparisons also include every captured UART buffer under the supplied schedule. All seven existing relative outputs match. |
| Ring/clock/freeze checks | 65,540 samples saturate the counter at 65,535 while the ring continues; wrapping timestamps retained; ignored retarget not mislabeled; 64 subsequent mutation attempts cannot overwrite a first guard; first suppression disposition persists. |
| Frozen missing-context control | All seven servo context checks reject the uninstrumented frozen source. |
| Six bad observers | Missing samples fails six cases; incorrect guard coordinate six; incorrect direction four; overwritten first fault six; incorrect accepted operand six; missing completion seven. Control bytes remain equal even when the observer is wrong. |

Sample duty fields are checked against the actual preceding motor-call arguments
in each synthetic control log, independently of the collector's own stored
state. No diagnostics test is treated as evidence that the software control law
is physically correct. The focus harness substitutes the outer pump/report
hardware surroundings; the captured byte parity covers its supplied schedule,
not every IRQ ordering or the complete runtime status-pump workload. Lane34/root
own broader protocol composition and interleaving gates.

## Compiled footprint and trace-expression reduction

[The measurement script](../../firmware/upstream-hardening/followup/33-motion-tracing/measure.py)
uses the frozen compiler and every existing unit flag unchanged. Only the new
collector unit receives `-Os`. [Measured object results](../../firmware/upstream-hardening/followup/33-motion-tracing/measurement.json):

| Object text bytes | Frozen | Initial observation | Final observation |
| --- | ---: | ---: | ---: |
| `servo` | 1,716 | 2,392 | 1,628 |
| `main` | 3,230 | 3,332 | 3,332 |
| New `motion_trace` | 0 | 492 | 492 |
| Sum | 4,946 | 6,216 | 5,452 |

The final trace-only bit packing uses `rebase | (holding << 1) |
((leg_sign < 0) << 2)` with unsigned casts. An exact source assignment inventory
proves both state variables are always zero or one, and all 2,048 combinations
of those values, requested direction and byte retarget count compare equal to
the initial ternary expression. This changes compiler allocation substantially:
764 fewer servo object bytes, without changing a controller expression or flag.
The original observation call ordering and API remain; experimental merged
hooks and motor wrappers were not adopted.

The final servo static frame is 128 bytes; collector helpers report at most
32 bytes. These are compiler frame reports, not a composed IRQ/callgraph bound
or physical stack high-water measurement. Net lane33 object text addition is
506 bytes before linker effects. The frozen 268-byte code margin and required
256-byte floor cannot accommodate that by themselves. This lane makes **no
whole-image fit claim**; root/lane35 must reclaim diagnostic-only code and check
the final linked `0x9c00` boundary, full 1,024-byte log reservation, upperflash,
RAM and stack. No reserved log or protected region is shrunk here.

## Remaining limits and reproduction

Four samples are a deliberately short recent trajectory, with no guaranteed
millisecond coverage. Ring count saturates; its next-slot index remains
independent. Initial and latest accepted targets are retained, not a complete
history of intermediate retarget operands. The sticky detailed snapshot covers
the first wrong-way/runaway outcome only; other inhibit reasons remain the
shared core's summary responsibility. Before any observed motion the record is
all-zero, including version/valid; active records use version 1. Once frozen,
subsequent guard fields remain unchanged even if the shared summary later records
another fault. RAM still requires the separately reviewed safe flush to survive
power loss; a shutter freeze before that boundary need not yield persisted data.

Reproduce with fresh private output directories:

```sh
python3 firmware/upstream-hardening/followup/33-motion-tracing/run.py \
  --source artifacts/private/handoff36-repeat \
  --output artifacts/private/astra33-audit-tests
python3 firmware/upstream-hardening/followup/33-motion-tracing/measure.py \
  --source artifacts/private/handoff36-repeat \
  --output artifacts/private/astra33-audit-size
```

Final test output was `artifacts/private/astra33-motion-tracing-final`; final
measurement output was `artifacts/private/astra33-final-size-2`. Actual execution
time, ISR interference and physical motor behavior are unmeasured. No claim of
factory parity, corrected AF/capture/shutdown, or readiness for a camera trial
follows. There was no device enumeration/open, USB report, flash operation,
motor command to hardware, updater/app launch or canonical Application Support
access. Instruction searches stayed on explicit ancestor paths and repository
paths. No real frames, unit dumps or keys were read or published by this lane.
