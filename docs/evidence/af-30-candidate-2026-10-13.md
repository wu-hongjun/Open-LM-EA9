# AF 3.0: capture/shutdown ownership and reference readiness

October 13, 2026, America/New_York. **Contax Zeiss 50mm f/1.4 AF 3.0.0 is
prepared offline; it has not been flashed or camera-qualified.** App
0.13.0/build 16 includes the new pinned template. This work sent no USB reports,
performed no device discovery or camera test, and changed none of the checked
canonical owner state files. The last verified hardware image remains AF 2.9,
which is held after failed camera acceptance.

The owner reported focus followed by capture freeze requiring battery removal,
then reset movement with no later focus movement; shutdown worked on the latter
reboot. [The original failure record](af-29-camera-failure-2026-10-12.md) preserves
both outcomes and unknown settings. These fixes address reproduced software
defects; no surviving hardware trace proves which defect caused those outcomes.

## Factory basis and the capture exchange

REA is the navigation/decompilation aid. The pinned original 1.8 application
instructions, upstream protocol notes and finite comparisons are the evidence.
The [capture oracle](af-30-capture-oracle-2026-10-13.json) executes:

- The original CS-rise callback `0x53a4` and status-06 sender `0x54d8`, with
  receive-window state supplied: two cases demonstrate the receive interlock.
- Original `0x5260` with generated complete `0x0a` requests: twelve combinations
  of length 9/11/25/64 and sequence 0/0x71/0xff produce exact raw echoes.
- One connected transition seeded in mode 4, phase 6, gate open, callbacks
  enabled: actual CS edges latch the interlock; VD selects mode 5 and schedules
  the opener after 10 units; raw echo schedules TX release after 100 units;
  release returns to init mode 1. These are nominal microsecond timer contracts.

The original lower RX/UART/timer operations are explicit cuts; callbacks are
invoked by the harness and registers are dummy memory. This does not establish
physical elapsed time, ordinary boot reachability or complete A7C II traffic.

The custom responder distinguishes the boot-final `0x0a` from a later capture
opener. Boot-final still sends the stored descriptor reply. A later opener waits
for VD, then echoes the complete received frame, preserving its sequence and
checksum. During the ensuing control exchange it holds status publication.
The closing `0x0a` sends the stored reply and resumes status on the next VD;
it does not rehome or refresh the boot handshake timestamp. This is a bounded
composition of recovered behavior, not a port of all fourteen factory phases.
The nine-request order used in the integration fixture comes from upstream's
Sony a9 II notes; synthetic payloads are not a recovered A7C II capture trace.

## Module ownership and shutdown

`em_arbitration.c/.h` owns receive/transmit epochs, session generation, status
pair admission, capture hold and shutdown/off state. `emount.c` owns validation,
immutable request snapshots, replies and event/query tails. Hardware CS-level
and pending-EIC checks gate TX admission under a short interrupt mask.

Opening a receive window invalidates an unsent status pair. A receive edge
between status 05 and 06 suppresses the old 06; queued events/answers remain
until a later successful 06. Failed UART transmission neither consumes tails
nor arms readiness. A deferred control reply keeps its request snapshot.
A new session cannot be armed by an older final reply, and foreground session
cleanup clears stale commands and tails atomically after any previous TX ends.

A validated shutdown has a dedicated complete-request snapshot and priority over
ordinary pending work. Its ISR only inhibits drive through GPIO; it transmits
nothing and starts no park. An already transmitting frame finishes boundedly,
then foreground sends the shutdown echo. Successful echo commits off state and
runs the existing factory-derived tail: 50 ms delay, UART disable, two VD-low
samples 1 ms apart with a 500 ms ceiling, PA23 high, then 100 ms delay. Late
session openers cannot restart AF or the disabled link; physical power reset
is required. No new shutdown motion, automatic fault clearing or flash logging
is introduced. The historical park wrapper is compiled only in finite host
fixtures, not linked in the hardware release.

Capture-opener and shutdown snapshots support validated **9–64-byte** requests.
An oversized request is rejected before shutdown inhibition; this is a bounded
candidate grammar, not support for every possible 255-byte factory request.
The new shutdown tests cover 9/11/16/19/27/32/48/64 bytes and rejection at 65.

## Nonblocking reference readiness

`af_reference` retains the pure drive/settle/origin policy. New `af_readiness.h`
owns attempt admission; `main` adapts it to sensors and the foreground scheduler.
A service turn performs one bounded reference step and returns to protocol
service. The old 20 ms voltage burst used only for logging is replaced by one
guarded initial reading. The existing 300 ms drive and 500 ms settle ceilings
remain, with bounded I/O guards; these are not measured wall-clock limits under
real IRQ and sensor latency.

Reference states are UNKNOWN → DRIVING → SETTLING → READY, with CANCELLED and
FAILED exits. Stop releases the motor and acknowledges, including Stop before
initial homing. CANCELLED does not silently retry: only a newly parsed motion
request can admit another acquisition, with **at most two attempts per physical
boot**. A new session during homing cancels it and drops stale work; another
completed handshake and fresh motion are required. Faults remain sticky and
FAILED cannot rearm from a motion request. Shutdown inhibits acquisition.

The reference becomes READY only after the final fault-free encoder reset;
no origin is fabricated to make a Move executable. Until then, normal targets
wait and established moving/unsettled bits describe an active acquisition.
The factory saved raw origin and seam arithmetic remain research findings.
Ordinary factory homing's enabling writer remains unresolved. Candidate homing,
its stop direction/offset and its explicit retry policy are not factory parity.

## Retained behavior, product and layout

The stock-derived PID/speed law, completion policy, motion observer, pure
reference, optical tables and audited aperture implementation are byte-identical
source to the preceding milestone. Motor drive gains and duty are unchanged.
The known aperture fields declare fixed nominal f/1.4; opaque `0x34` retains
stock operand echo. The app shows **Actual aperture: Unknown**; only the lens
ring operates the iris. Exposure and physical stop-down still need camera tests.

The [candidate](../../firmware/candidates/3.0.0/README.md) occupies 20,480 bytes at
`[0x5000,0xa000)`, profile at `0x9f00`. Loader version is 3.0.0; camera BCD is
0x30, keeping the single-byte BCD scheme consistent after 2.9. Linked initialized
flash ends at `0x9d78`, leaving **392 bytes** before the profile; static RAM is
2,380 bytes, with 8,192 bytes reserved for stack. Stack high-water is unmeasured.
Only protocol/arbitration units use `-Os`; controller/drivers retain `-O2`.
No heap, diagnostic flash writer or legacy park controller is linked.
[The build manifest](af-arbitrated-build-manifest-2026-10-13.json) pins inputs,
dependencies, layout and digest. Optimization and polling timing need hardware
qualification; fitting the image does not establish ISR or stack margins.

Explicit app AF installation and CLI `prepare-af`/`apply-af` select 3.0.
The ordinary Device dropdown preserves the verified installed variant.
AF 2.9 now has an explicit held message. All older variants and original 1.8
recovery remain available for verification/restoration; their pinned bytes
were checked unchanged. Local preparation uses an isolated state directory.

## Validation and remaining gate

[Validation](af-30-validation-2026-10-13.json) records the final image and evidence
digests, successful signed app/CLI packaging and native/Python image equality.
Checks completed after the final interrupt-boundary review:

| Check | Result |
| --- | --- |
| [Capture/shutdown arbitration](af-30-arbitration-2026-10-13.json) | 18 current cases pass; 7 exact frozen-2.9 failures detected |
| [Reference readiness](af-30-readiness-2026-10-13.json) | 7 current cases pass; frozen 2.9 cancellation defect detected |
| [Retained driver/link/lifecycle checks](af-30-link-regressions-2026-10-13.json) | 40 current cases pass; 15 frozen-2.8 failures detected |
| Full C/profile/driver suite | Pass, including all eight requested lens profiles |
| Swift tests | 51 pass: 7 LensCore, 34 DeviceKit, 10 AppWorkflow |
| [Retained queue, telemetry and opaque query checks](af-30-retained-regressions-2026-10-13.json) | Pass; 32 original complete `0x34` replies and frozen controls retained |
| [Pure factory controller oracle](af-30-factory-oracle-2026-10-13.json) | 7,323 original-instruction comparisons; gain mutation detected |
| [Original frame sync/completion](af-30-stock-motion-oracle-2026-10-13.json) | 12 / 18 cases pass |
| [Original shutdown ordering](af-30-stock-shutdown-oracle-2026-10-13.json) | 24 legal echoes plus direct-state bad-checksum boundary recorded |
| [Prior releases/recovery](af-30-preserved-releases-2026-10-13.json) | 21 artifacts byte-identical; checked owner state unchanged |

The fixtures supply CS/VD edges, sensor/voltage data and UART completion, and
instrument selected delay/TX boundaries. They do not simulate concurrent real
IRQs, full MCU reset, camera negotiation, exposure or optics. Homing fixtures
use the inherited mechanical model, not measurements of this adapter.
Original-instruction agreement is finite; the semantic-model union remains
partial, and this milestone does not establish complete reverse engineering.

Flashing is a separately requested step. Preserve the same-unit fresh backup,
durable journal, physical reconnect guard and strict complete-image/protected-
data verification. Then use the [camera runbook](../af-s-test.md): MF live
preview, saved exposure, quiet idle and shutdown first; a single bounded AF-S
attempt only after those pass. Stop on preview freeze, shutdown nonresponse or
abnormal drive. AF 2.9's earlier failure remains failed until a new candidate
has separate camera evidence. No physical improvement is claimed yet.
