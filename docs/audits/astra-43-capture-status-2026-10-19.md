# Astra43 — bounded AF3.7 capture/status replay

**No new capture/status liveness defect was reproduced; no production patch is
proposed by this lane.** The exact AF3.7 path deliberately stops periodic status
after a successful raw capture echo. Original stock instructions also return to
initialization mode after the echo and remain silent on VD alone. An ordinary
readiness request re-arms both implementations. Removing the candidate's status
disable would change this protocol policy without a demonstrated fix for the
owner's camera freeze.

The October 19 owner report remains two saved photos in AF followed by freeze
and battery removal. Its full capture history was omitted for diagnostic
capacity. These synthetic sequences are discriminators proposed by
[Astra40–41](astra-40-41-af37-camera-trace-2026-10-17.md), not a reconstruction of
the missing later camera events. The earlier retained raw echo and shutdown TX
returns establish local completion only, never camera acceptance.

## Exact inputs and replay

The runner verifies all 49 source digests and the host peripheral shim against
[the 3.7 manifest](../../firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json)
before execution and verifies the source digests again afterward. It links the
real `emount`, `emount_packets`, `em_frame`, `em_owner` and `em_shutdown` units
from `artifacts/private/targeted37-repeat/src`. Hardware UART, CS and VD are
synthetic boundaries; only test state accessors are appended to private source
copies. Startup packet initialization uses the pinned existing test adapter.
Trace storage is an observation collector with the production diagnostic ABI;
flash persistence, motor execution, main-loop homing and physical bus timing
are outside this test.

Eleven cases pass under AddressSanitizer and UndefinedBehaviorSanitizer:

- Status interruption during either member of the status pair, followed by a
  VD-gated raw echo. Polling before VD cannot send the raw request.
- Failed raw TX retains its owner for retry; success clears it.
- VD, readiness, session, shutdown and ordinary-control insertion during raw
  TX. The outgoing snapshot remains byte-identical to its original synthetic
  request, even when the receive buffer changes.
- Failed readiness TX retries without prematurely re-enabling status.
- Session or shutdown insertion during readiness TX prevents stale readiness
  publication.

Applicable cases then run eight VD/poll steps in the post-capture state,
ordinary readiness, a fresh status pair, a second capture/re-arm and shutdown.
VD alone remains silent. Readiness restores status; subsequent capture and
shutdown complete. TX RETURN identity, flags and session match their START
across the interrupt insertions. There are no unbounded test loops: process
execution is limited to ten seconds per case, with fixed finite pulse counts.

Three concrete mutations fail the replay: retaining status after raw echo,
allowing readiness publication only once per handshake, and leaving the raw
retry owner set after successful TX. The latter two fail after the first
capture, rather than merely preventing initial setup. These controls establish
sensitivity to the tested contracts; they are not failures in frozen AF3.7.

[Source-bound runner](../../firmware/upstream-hardening/followup/43-capture-status/run.py)
· [test cases](../../firmware/upstream-hardening/followup/43-capture-status/test_replay.c)
· [sanitized result](../../firmware/upstream-hardening/followup/43-capture-status/results.json).

## Upstream and original stock comparison

The pinned upstream commit is `d52ed06cc449918f938e0695fbf29a0c4141f2b2`.
Its `src/emount.c` has SHA-256
`eb4a24fd7b63fa53a92f534642e3284f3bc339c155d7e2bdbe5e9fb704bdca2e`,
verified by this runner and the retained collection digest. At lines 940–942,
VD requests status whenever `em_handshake_done` is set. At lines 1537–1543,
answering ordinary readiness sets that flag. This upstream revision lacks the
candidate's raw capture owner and post-echo status-disable path. Its simpler
status policy is not evidence that the added capture policy is defective.

The REA-assisted factory study is checked against the original pinned stock
1.8.0 application, SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
The [factory runner](../../firmware/upstream-hardening/followup/43-capture-status/factory_replay.py)
first re-executes the pinned lane04 original-instruction tests and then extends
them with one, two and four capture/re-arm cycles. Across seven cycles,
original CS/VD handling selects capture mode, the echo callback returns the
synthetic request, and explicit TX completion callbacks return to mode1.
Eight additional VD calls per cycle produce no transmission or scheduled
status work. Original ordinary readiness dispatch restores mode4; subsequent
VD reaches the connected status phase. The contrary expectation that raw echo
alone resumes periodic status fails this original-instruction oracle.

[Factory result](../../firmware/upstream-hardening/followup/43-capture-status/factory-results.json).
The machine's connected starting state is supplied, timers are explicitly
invoked, UART/DMA operations are cut, and peripheral registers are RAM-backed.
This is bounded instruction evidence, not ordinary boot reachability, real
interrupt scheduling, physical camera timing, or complete factory parity.
Stock's callback-time shared receive-buffer dependency remains a deliberate
difference from the candidate's immutable owner snapshots.

## Disposition and reproduction

Exact proposed production transformation: **none**. No pinned applicator is
provided because a production fix has not been justified by a failing control
on the baseline. Code size delta is zero; static RAM delta is zero; wire layout,
raw echo contents, readiness gating and shutdown policy are unchanged. The
AF3.7 manifest's 328-byte code margin is unaffected by this lane. These are
identity consequences, not measurements of a newly built firmware image.

Run from the repository root with fresh private output directories:

```sh
python3 firmware/upstream-hardening/followup/43-capture-status/run.py \
  --output artifacts/private/astra43-replay-new
tools/rea-analysis/venv/bin/python \
  firmware/upstream-hardening/followup/43-capture-status/factory_replay.py \
  --output artifacts/private/astra43-factory-new
```

The source runner also accepts `--candidate PRIVATE_BUILD` for integration. It
keeps the full 3.7 input checks, verifies every candidate source digest and its
shim/image against the candidate manifest, then replays those exact sources.
Candidate results stay in the private output directory; they do not overwrite
the committed baseline results.

Final private results are in `artifacts/private/astra43-pinned-final` and
`artifacts/private/astra43-pinned-factory`. No hardware enumeration, opening,
reports, flashing or motor actions occurred. No app/updater or canonical
Application Support state was accessed. No Git mutation or external message
was sent. Raw owner camera evidence and operands are not copied into the tests
or public results. AF3.7 camera acceptance remains failed; the camera freeze
cause remains unresolved by this lane.


## Final AF3.8 composition check

The same eleven real-protocol replay cases and three mutation controls pass
against the completed `artifacts/private/readiness38a` build. Every candidate
source digest (49 files), host shim and image is verified against its manifest,
in addition to the unchanged frozen AF3.7 checks. Public baseline results are
preserved. This verifies the capture/status contracts in the composed candidate;
it does not extend them to camera acceptance or motor behavior.

- Image SHA-256: `8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`.
- Manifest SHA-256: `be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0`.
- Private replay output: `artifacts/private/astra43-final38`.
- [Bound candidate result](../../firmware/upstream-hardening/followup/43-capture-status/candidate38-results.json).

An independent static [compiled callback check](../../firmware/upstream-hardening/followup/43-capture-status/review_compiled.py)
also verifies the final linked ELF's Thumb pointers: main registers
`powerdown_signal` and `motion_shutdown_inhibit`; `em_init` registers
`on_cs_edge` and `on_vd_edge` in the same argument positions as AF3.7. The legacy
park symbol is absent in both linked images. Each extracted ELF binary matches
its raw binary and candidate-image prefix. The complete `em_eic` object
disassembly and relocations are unchanged. The `emount` object differs only in
two `em_init` immediate instructions: the version marker changes from 55 to 56,
and its compensating addition changes from 179 to 178, preserving the derived
lens ID. Remaining code and relocations match exactly.

The final compiled main loop calls `focus_answer_queries` immediately before
`em_poll`; AF3.7's main loop does not. This is a static placement observation
for the separately owned readiness fix, not an execution test of its semantics
or a whole call-graph/stack proof. [Compiled result](../../firmware/upstream-hardening/followup/43-capture-status/compiled38-results.json)
is bound to both ELF and manifest hashes. Its private output is
`artifacts/private/astra43-compiled38-final`.

```sh
python3 firmware/upstream-hardening/followup/43-capture-status/run.py \
  --candidate artifacts/private/readiness38a \
  --output artifacts/private/astra43-final38-new
python3 firmware/upstream-hardening/followup/43-capture-status/review_compiled.py \
  --candidate artifacts/private/readiness38a \
  --output artifacts/private/astra43-compiled38-new
```
