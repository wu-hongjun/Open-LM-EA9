# Follow-up 16 — query answer capacity and foreground pump service

The frozen 3.3 queue, even with follow-up 12 applied, can **silently lose an
already-admitted query**. `em_take_query()` removes the request regardless of
answer capacity; `em_post_query_answer()` returns void and discards the result
when four answers are already buffered. The proposed overlay retains requests
until answer capacity exists and runs the existing bounded worker in `pump()`
before status transmission. This is a staged future overlay, not a published
image or a camera-qualified change.

The exact production changes are confined to two sites:

- `emount.c`, `em_take_query()`: add `g_ans_n >= EM_QUERY_Q` to the early-return
  condition under the existing saved-mask lock.
- `main.c`, `pump()`: call `focus_answer_queries()` immediately before `em_poll()`,
  outside the existing `g_homed` reporting gate.

The [applicator](../../firmware/upstream-hardening/followup/16-query-flow/apply.py)
requires follow-up 12's bounded, session-owned worker to be present and accepts
only private scratch source trees. It changes neither the conversion functions
nor the receive/transmit grammar. Root integrates and measures any future image.

## Reproduction and correctness argument

The runner verifies every frozen final-33a source against the published 3.3
manifest before and after testing. Its baseline is that source plus follow-up
12. It does not repeat follow-up 12's in-flight epoch race or replenishment
budget tests.

Eight checksum-valid `0x04` requests, alternating position-to-distance and
 distance-to-position, are admitted in two groups of four. The actual production
worker converts the first group, filling the answer queue. The second group is
then admitted while the query queue is empty, so no receive-queue overflow is
involved. In the baseline, another worker pass removes all four new queries and
silently loses their answers. Eight conversions produce only four answers on
actual encoded `0x06` frames; repeated later status frames remain empty. If one
status is sent between groups, the baseline delivers six of eight and loses two.
A Drive event case delivers four of eight while reducing first-tail capacity.
These wire observations are recorded independently of the failing assertions.

`EM06_LEN_IDLE` is 48 and `EM06_LEN_MAX` is 56. Three-byte query answers therefore
fit two per idle tail; a four-byte Drive event leaves room for one. The proposed
worker leaves four requests pending when answers are full, or two after a
partial drain. Successive real status/worker passes deliver every admitted
request exactly once, in FIFO order, with tags, values, frame bounds, checksums
and termination checked. The `pump-backlog`, `homing-stream` and `servo-backlog`
cases also deliver all eight through partial tails.

Checking capacity at dequeue is sufficient for the current source because the
query worker is the sole answer producer, and all of its invocations run in the
single foreground context. Conversion calls only `focus_map.c`/`focus_dist.c`
pure arithmetic; no path calls `pump()`, `em_poll()` or another answer producer.
An interrupt may append incoming queries, or reset the session; it cannot consume
the remaining answer slot. Follow-up 12 already rejects publication after an
epoch/readiness change. The guard is not a general reservation API for future
concurrent answer producers. The finite incoming queue can still reject new
arrivals when itself full; this patch prevents loss of requests already admitted,
not arbitrary-load losslessness.

## Why service belongs in the pump

In final-33a, `focus_answer_queries()` is called only in the main loop's
`step == 1` block. That foreground loop cannot reach it during `servo_move_rel()`.
The configured STOCK and PARK servo callbacks both point to `pump()`, and the
servo calls that callback each iteration and once at final feedback. Homing's
drive and settle loops also call `pump(0)` while `g_homed` is clear. Before this
proposal, those pump calls service status but never convert pending queries.

The source-bound test compiles the entire production `servo.c`, the exact pump
and worker bodies extracted from `main.c`, and the production protocol, queue,
frame, ownership and conversion modules. Encoder time/position, motor outputs,
voltage sampling and transport are synthetic host I/O. The current-position
report is an observed stub: this lane is about query flow, not position-report
math or physical motion. Requests are injected after the synthetic servo has
started. Both the original baseline and capacity-only variant finish a successful
servo move without sending any query answer during it. The proposal sends both
answers during the move. A second case injects two four-query groups during the
same move and sends all eight before return, in five pump calls.

For homing, the test executes the exact production pump repeatedly with
`g_homed == 0`; synthetic receive callbacks inject two four-query groups at the
voltage-sampling boundaries of the first two pump calls. All eight answers are
sent in order while position reporting remains disabled. This is a test of the
actual **unhomed pump path**, not an execution of the full homing state machine or
a physical homing experiment. The source call sites in both homing loops establish
where that pump is used. A deliberate mutant placing query service behind
`g_homed` fails both the unhomed query and homing-stream tests.

The conversion operands name protocol positions/distances and use fixed optical
constants. They do not read encoder origin, `g_homed`, predictor state or current
position. Therefore the reporting gate is unnecessary for these conversions.
The worker's existing handshake, shutdown, abort, inhibit and epoch checks still
apply. Its per-pass work remains at most four conversions. Executed pump depth is
one throughout; the conversion call graph has no recursive pump edge. The new
call increases nested servo/homing stack use and instruction work, so final linked
footprint/stack and hardware timing gates still belong to integration.

## Archived protocol and REA limits

The locally archived
[autofocus protocol, §2.5 and §4.2](../../references/upstream/weiziqian/E-mount-protocol-RE/docs/autofocus.md)
describes `0x22` and `0x2E` as operand conversions and says their answers ride in
the next `0x06`, with **PROBABLE** confidence. Its `0x2E` operand-zero meaning is
explicitly unknown; this proposal does not reinterpret it. The archived
[message 0x06 notes](../../references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x06.md)
also distinguish observed idle traffic from reverse-engineered event behavior.
These support serving pure queries during foreground motion, but do not establish
a measured camera response deadline or prove the lens model's optical accuracy.

Read-only inspection of the existing REA archive found no independent proof of
a factory query deadline or a homing readiness requirement. Relevant factory
records show a different architecture: `0x5308` stages received instruction data,
`0x5a2c` publishes completion events and changes the status length to 50, and
`0x8b70` loops through `0x5dd4`/`0x5e00`. They do not contain this upstream
four-entry query/answer worker. Evidence records, all in the pre-existing
`references/private/rea-analysis/phase3/app` archive:

| Record | Evidence ID |
| --- | --- |
| `function-5308.json` | `ev_fe024fd24d03a8e47565abd27ca72b9daffd5113202830a549917edeac5a84ae` |
| `function-5a2c.json` | `ev_c560091e12e280d9c679e7541d6a0c32bf67a9c7a29d18cd35eb61907b6066f0` |
| `function-8b70.json` | `ev_407d75644b8bab5a2077d6cbc09e791989b74d8e9712c50ec40dde18e29d25ee` |

These are archived decompiler observations, not original source or new device
observations. They are not used to infer missing factory behavior. The proposed
service placement is justified by the actual upstream pure-conversion path and
its source-bound tests, with the archived protocol's stated uncertainty retained.

## Results and rerun

[Results](../../firmware/upstream-hardening/followup/16-query-flow/result.json):
17 cases per source variant, all 17 proposal cases pass under ASan/UBSan. Across
the prior-12 baseline, capacity-only variant and deliberately homed-gated mutant,
18 intended negative controls fail. This count is scenario invocations, not 18
independent defects. Positive controls cover FIFO/refill, one-answer Drive tails,
ordinary wire byte identity, session reset clearing both queues, shutdown status
suppression, handshake/abort/inhibit gates and saved interrupt-mask preservation.
Entire proposed `main.c` and `emount.c` units also compile for Cortex-M0+ with
warnings as errors. No final linked image, footprint claim or hardware timing
claim is made by this lane.

```sh
python3 firmware/upstream-hardening/followup/16-query-flow/run.py \
  --output artifacts/private/astra-16-query-flow-recheck
```

Use a fresh output directory. Final run artifacts are in
`artifacts/private/astra-16-query-flow-final3`. Frozen images, source trees, pins,
old lanes and canonical application state were untouched. No network, discovery,
USB/HID, updater, flash or physical motor operation occurred.
