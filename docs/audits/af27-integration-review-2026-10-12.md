# AF 2.7 integration review

October 12, 2026. Independent follow-up to the
[AF 2.6 correctness audit](night-firmware-correctness-2026-10-12.md), reviewing
the parent’s uncommitted AF 2.7 changes over
`d023745022e9375c54282221be8d6fee4df2ad61`. Production sources were frozen
for this review; tests and release documentation may subsequently expand.

No remaining blocking issue was found in the reviewed retarget, Stop-queue or
release-diagnostic changes. This conclusion covers these software changes,
not camera compatibility or physical autofocus qualification. No hardware
reports, private-state changes, commits, production edits or recovery-image
changes were performed by this review.

## Stop overflow and ordering

The final `em_post_event` policy retains a Stop under a full two-slot FIFO,
retains the oldest completion before it, and supersedes an older pending Stop
by removing it and appending the newest Stop. Ordinary completions cannot
evict a pending Stop. Depth stays bounded and the transmitter still emits
at most one event per status frame.

The initial proposed in-place coalescing had an ordering issue: `[Stop, Move]`
followed by another Stop remained `[Stop, Move]`. Stops separated by completed
motion are not consecutive duplicate acknowledgements. The parent corrected
this during review to `[Move, Stop]` and added the production-main
`stop-reordered` regression, including the intermediate VD drain that makes
the pending sequence reachable.

An independent property probe tested all 510 Move/Stop event sequences of
lengths one through eight, using the real queue and transmitted `0x06` tails.
It verified bounded depth, exactly one retained pending Stop when any Stop was
posted, and a newest Stop at the tail when the last posted event was Stop.
The corrected implementation passed. A reconstructed initial in-place-coalesce
negative control failed specifically on Stop → Move → Stop:

```text
queue properties passed: 510 event sequences, bounded depth, Stop retained and newest Stop emitted last
queue property FAILED length=3 sequence=5 stops=2 found=1 last=0x1d
```

This overflow policy is a deliberate bounded candidate policy. The factory
uses staged event bytes rather than this FIFO; the test does not establish an
exact factory queue algorithm or camera acceptance of overflow coalescing.

## Quantized target deduplication

The wrapper admits/clamps the new target and quantizes it to the existing
four-count wire coordinate before comparing it with the current target.
Only a changed admitted target consumes a redirection budget and rearms the
controller/leg deadline. This fixes repeated identical absolute requests
without altering the pure factory PID.

The surrounding feedback, I/O, runaway, wrong-way, no-progress and total-time
guards remain active. The retarget hook is still polled before the abort hook,
so deduplication does not skip Stop/replacement ownership. Relative and defocus
operands are resolved to absolute positions by the caller before this comparison;
the code does not deduplicate their raw operands.

Four additional scripted wrapper probes passed under AddressSanitizer and
UndefinedBehaviorSanitizer:

| Probe | Verified outcome |
| --- | --- |
| Twenty-three 4000–4003 requests with zero retarget budget | Same quantized target; zero redirects; bounded healthy deadline at 376 simulated ms |
| Same duplicate stream, cancellation hook at 100 ms | Aborted with zero redirects and released drive |
| Repeated `INT32_MAX`, admitted to the same upper-limit target | Zero redirects; bounded healthy deadline; feedback remains within admitted bounds |
| Two distinct destinations, retarget budget one | Hard timeout at the second destination; one counted redirect; released drive |

The cancellation-hook probe is not a camera-wire Stop test. Parsed Stop and
command ownership remain covered separately by the production-main tests and
the existing wrapper suite. Simulated time is not a hardware-period measurement.

## Release diagnostic gating and regression script

The new `EA9_NO_LOG` guards in `main.c` remove diagnostic capture flushing,
quiet-log bookkeeping and related flash-log decision work. The guards in
`emount.c` remove raw pre-handshake/normal-window copies. Protocol admission,
command parsing, consumed request ownership, negotiation, handshake status,
homing, focus dispatch and shutdown remain outside those diagnostic blocks.
No new motor action or removed fault guard was found in this diff.

The updated `test-polished-candidate.py` passed all six production-main cases:
`stop-fifo`, `stop-pending`, `stop-coalesce`, `stop-reordered`, `repeat`, and
`single`. Frozen AF 2.6 failed the two designated bug negative controls. The
script also passed eight inherited mechanical target cases, the frozen 2.5
opaque-query negative control, and 32 complete original-instruction `0x34`
response comparisons. The pure controller/aperture sources checked by the
script remain identical to their AF 2.6 manifest.

The first exploratory script invocation overlapped the parent’s test edits
and lacked `stop-reordered`; it is superseded by the second invocation below.
Release evidence must come from the parent’s final stable validation run,
including any promoted tests, rather than that exploratory output.

## Reproduction and source identity

The review’s local results and additional diagnostic probes remain in the
ignored `artifacts/af27-integration-review/` directory. Reproduction commands:

```sh
tools/rea-analysis/venv/bin/python scripts/test-polished-candidate.py --output artifacts/af27-integration-review/script-regressions-final
artifacts/af27-integration-review/queue-properties
artifacts/af27-integration-review/quantized-target 0
artifacts/af27-integration-review/quantized-target 1
artifacts/af27-integration-review/quantized-target 2
artifacts/af27-integration-review/quantized-target 3
```

The script requires a fresh output directory; use another new path for a
subsequent invocation. `queue-properties.c` includes production `emount.c`
directly, links the ordinary packet/profile modules and host shim, and checks
actual transmitted tails. `quantized-target.c` links the ordinary factory
wrapper/controller, I/O guard and coordinate map, with scripted feedback and
clocks. Both were compiled with `-std=gnu99 -O1 -Wall -Wextra`,
`-fsanitize=address,undefined -fno-sanitize-recover=all`. The queue probe also
defines `EA9_NO_LOG` and uses the inherited host CMSIS shim. The parent has
the exact source/build commands for promoting these tests into the repository.

Reviewed production source SHA-256:

| Source | SHA-256 |
| --- | --- |
| `firmware/ea9/src/emount.c` | `baceceb2b825c4723937809b55e712b4cdb60c7ccf902cc06118220c2a3f17a7` |
| `firmware/ea9/src/emount.h` | `81af89b2d2ceeb4dc9de628c1435d412ba697960aa2d3b1c8f6b198a7cca16a3` |
| `firmware/ea9/src/factory_servo.c` | `760c6ede751484cc9f234716ca7af0a4839bf6abcfe7373a38656187b0d4e1b6` |
| `firmware/ea9/src/main.c` | `8a092971941154f289b77aa2d984f1166b4d56098ebf3f2b052f6cab88991cf1` |

`integration-results.json` additionally records probe/test/script hashes and
the independent property/wrapper outputs. The report does not validate the
final app package, source-to-binary reproducibility, upload transaction or
firmware pins; those remain the parent’s separate release checks.

## Retained open issue

The predictor-lifetime versus measured-motion finding from the initial audit
remains open. AF 2.7 intentionally does not introduce guessed braking,
settling or sensor-noise gains. The remaining camera tests must distinguish
actuator termination, physical rest and optical focus; the software changes
above establish none of those physical equivalences. Factory reconstruction,
optical calibration, saved exposure and AF-S performance remain qualified
only to the extent of their separate evidence records.
