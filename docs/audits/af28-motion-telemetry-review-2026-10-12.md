# AF 2.8 motion telemetry evidence and review

October 12, 2026. Independent audit of the proposed measured-motion observer,
following the retained [AF 2.6 counterexamples](night-firmware-correctness-2026-10-12.md)
and [AF 2.7 integration review](af27-integration-review-2026-10-12.md).
The starting source is AF 2.7 commit
`6d8440750eb3efa1cf24dbce2d4e27c3e937600c`.

No USB/device enumeration, HID reports, updater, camera, motor or application
state changes were performed. The audit owns this document and ignored scratch
files under `artifacts/af28-review/` only. No production source, released
candidate, recovery image or firmware pin was edited by this reviewer.

## What the evidence establishes

The protocol evidence is the pinned upstream
`weiziqian/E-mount-protocol-RE` commit
`3a94a8d2e6a7786ab3e05b1319b421e76744b4c0`, retained under
`references/upstream/weiziqian/E-mount-protocol-RE/`. Its confidence labels
describe the author’s native/manual/Yongnuo observations and reconstruction;
they are not new A7C II measurements.

| Field | Evidence and confidence | Consequence for AF 2.8 |
| --- | --- | --- |
| `0x05 pl[22]` bit 6 | Focus/lens motion is marked **CERTAIN** by upstream `docs/msg_0x05.md:55`; bits 0–5 are lens-specific and bit 7 marks reporting | Change bit 6 consistently with the observer while retaining the other bits |
| `0x06 pl[0]` bit 7 | At-rest versus moving/just-stopped is **PROBABLE**, upstream `docs/autofocus.md:374` | Keep existing candidate encodings; do not invent an undocumented unknown code |
| `0x06 pl[1]` | `0`, `0x02`, `0x04` direction mapping is **POSSIBLE**; physical polarity remains **UNKNOWN**, `docs/autofocus.md:375,492` | Measure reversal independently of a new target; retain existing polarity mapping as candidate policy |
| `0x06 pl[20..21]` | Current position on the same scale as targets is **CERTAIN** | Keep one fresh admitted coordinate sample for the packet pair |
| `0x06 pl[2..3]` | Native forecast field is established, but a native implementation also suppresses its forecast, `docs/msg_0x06.md:168` | Equality of current/ahead positions is not evidence of rest |
| `0x06 pl[32..38]` | Seven signed frame differences, newest last, are **CERTAIN** on Yongnuo and **PROBABLE** generally, `docs/msg_0x06.md:37` | Preserve existing candidate sign/units; do not call this factory PID velocity |
| Completion tail | Arrival/Stop meanings are **PROBABLE**, `docs/autofocus.md:408` | Event eligibility and measured physical motion remain distinct obligations |

The REA-assisted original-instruction reconstruction provides separate factory
evidence. `research/stock-1.8/stock_model.c:447` models the factory frame-sync
routine `0x5120` copying the same sampled protocol position into both `0x06`
position fields. The recovered `0x8d94` routine at line 706 tests target crossing
or a pre-existing completion flag, without a velocity/dwell condition. Factory
common timeout/Stop completion therefore does not prove physical rest.

An additional independent replay against the retained stock application
SHA-256 `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`
passed twelve `0x5120` cases and eighteen `0x8d94` cases:

- Frame sync writes identical current/ahead fields regardless of the seeded
  completion flag; the tested motion bytes are unchanged by that routine.
- Target crossing can return complete with nonzero seeded velocity, and the
  common completion flag can return complete before crossing.

These tests assert those routines only. They do not establish every firmware
writer, physical motor/sensor behaviour, live interrupt ordering, camera field
consumption or ARMv6-M instruction legality in the emulator. Synthetic extreme
positions are arithmetic fixtures rather than camera-accepted coordinates.

The factory main model also maintains a separate low-byte
old-position-minus-new-position buffer at SRAM `0x668`
(`stock_model.c:613`). No established copy from that buffer into the seven-byte
wire trace was found in the model. That bookkeeping does not justify reversing
the candidate trace sign or labelling its per-VD trace as factory-equivalent.
Factory PID velocity is a separate count difference per approximately
13.75-ms configured controller invocation.

## Concrete contradiction being fixed

AF 2.7 derives moving from `ahead != counts`, and ends its predictor when the
actuator command terminates. Its inherited simulator can then continue changing
position while the packets report at rest. Reversal can similarly make a
target-clipped forecast zero while actual motion still points away from the new
destination. The prior audit reproduced this independently of physical camera
testing.

Two facts refute the old equivalence between forecast equality and rest:
upstream documents suppressed native forecasts, and the original factory
frame-sync routine always publishes identical position fields. Removing the
target-bound predictor from the factory backend and observing displacement
separately is therefore defensible. It is not a reproduction of all factory
status-bit writers.

## Recommended bounded observer policy

The observer should be pure: validated coordinate samples, time and frame
cadence in; measured displacement/direction and explicit validity/freshness out.
It must not drive, tune, brake, delay or alter controller completion.

- Observe every fresh admitted tracker sample, independently of predictor and
  command lifetime. Preserve motion information through target crossing,
  timeout, Stop, and target reversal.
- Movement can require one declared four-count resolution unit from a retained
  raw motion anchor. This is not measured noise calibration. Quiet intervals
  must not reset that anchor and hide slow cumulative displacement. Per-VD
  history can retain the existing candidate’s signed raw difference divided
  by four, independently of the movement anchor.
- Repeated identical calls within one millisecond or one VD interval cannot
  establish rest. A complete unchanged continuously observed interval tied to
  the already negotiated frame period can establish an **observed-unchanged
  estimate**, not a physical zero-velocity guarantee.
- Separate missing/stale sensor observations from a missing VD. A missing VD
  does not prove sensor loss, although a conservative unavailable packet-window
  state is a defensible candidate policy. Resumed observation must regain
  freshness rather than rebasing indefinitely.
- Rebase after a late observation, missed frame interval, coordinate reset or
  new session. Do not fabricate missing per-frame velocity samples or report a
  pre-gap direction as a current measurement.
- Reset the observer on the committed reference change. Do not interpret a
  coordinate discontinuity as a large physical movement.
- Reject invalid feedback before observer arithmetic and leave the existing
  sensor/motor/session fault protections intact. Widen position differences
  before subtraction; use rollover-safe unsigned elapsed time.

Absolute cell comparisons have a boundary-jitter limitation: alternating
`+1/-1` encoder samples at zero cross a floor-quantizer boundary and can keep
movement asserted indefinitely. The final implementation instead uses a
retained raw displacement anchor with a symmetric four-count threshold.
Its per-VD history scales signed displacement, not absolute quantized cells.
Neither choice is hardware noise calibration; noise of four counts or more
can still be observed as motion, and sub-resolution movement is not a proof of
physical rest.

The parent’s proposed unknown fallback uses the existing moving/just-stopped
status with direction zero, without inventing an unknown wire bit. This must
be described as conservative candidate fallback, not a recovered factory
unknown encoding. Sensor noise and physical settling remain unmeasured.

Retaining event completion unchanged can pair a Stop/completion appendix with
observed coast or unknown motion freshness. The tail must not erase the measured
status. The original common completion flag supports separating those concepts,
but A7C II acceptance of the simultaneous fields remains a camera-testing
obligation. Do not claim that acknowledgement, crossing or deadline proves
physical rest or optical focus.

## Reproduction and implementation review status

The original-instruction replay is entirely offline:

```sh
tools/rea-analysis/venv/bin/python artifacts/af28-review/stock-telemetry-oracle.py
```

It records results and the replay script hash in
`artifacts/af28-review/stock-telemetry-oracle.json`. Its configuration creates a
new evidence directory; use another fresh directory for a subsequent run.

The original replay has been promoted to the repository-owned
[`test-stock-motion-reporting.py`](../../scripts/test-stock-motion-reporting.py),
which additionally seeds nonzero status bytes and accepts an explicit fresh
output directory. Its thirty original-instruction cases passed independently:

```sh
tools/rea-analysis/venv/bin/python scripts/test-stock-motion-reporting.py --output artifacts/af28-review/stock-final
```

## Implementation review outcome

No remaining blocking issue was found in the final measured-motion observer
and integration diff. The pure observer, main packet publication and test
changes were reviewed against the policies above. Movement/direction now belong
to fresh validated displacement; command end and Stop do not reset the observer.
Reference commit and boot reset do. The factory backend publishes identical
current/ahead positions; the legacy backend keeps its target-bound predictor
while obtaining movement state from the observer. Idle feedback is refreshed
before the pending status pair is transmitted.

Two issues found during implementation review were corrected before closure:

1. After stale sampling or missing VD, the initial implementation treated an
   arbitrary rebase sample as a genuine previous-frame baseline. In the probe,
   a stale rebase at 52 ms followed by resumed VD at 53 ms emitted a one-ms delta
   as a per-frame trace entry. The final `history_ready` state discards that
   partial interval; the first changed VD establishes a baseline, and the next
   consecutive fresh VD publishes a measured difference. A continuously moving
   `resume-history` regression now checks zero at 53 ms and delta 17 at 70 ms.
2. Absolute floor-cell comparison reported continuous motion for synthetic
   `+1/-1` chatter at zero and near a positive cell boundary. The final retained
   raw motion anchor fixes that sub-resolution counterexample without adding a
   measured-noise claim. Quiet frames leave the anchor unchanged, and a slow
   one-count-per-frame progression eventually reaches the four-count movement
   threshold. Differential raw per-VD history avoids fabricated cell-boundary
   `+1/-1` trace entries.

Independent AddressSanitizer/UndefinedBehaviorSanitizer runs passed:

- Thirteen pure observer cases, including coast, reversal, slow movement,
  same-ms/burst samples, quiet windows, clock/frame rollover, negative/upper
  margins, stale/absent/skipped/resumed VD, reference reset, boundary chatter
  and slow accumulation across quiet frames.
- Four production-main transmitted cases: forty-count/full-travel coast,
  measured reversal plus Stop, and sampling gap plus reference reset. Packet
  checksums and identical factory current/ahead fields passed. Stop/completion
  tails retain observed moving flags.
- All twenty-one factory hardening and twenty-one legacy hardening cases,
  including invalid feedback, command/query ownership and final-read faults.

Production hashes were captured before and after this independent invocation
and were identical. The final
[`test-observed-candidate.py`](../../scripts/test-observed-candidate.py) also
passed independently: both coast probes fail for the intended reason in frozen
2.7 and pass in current source; prior frozen 2.6 queue/retarget negative controls,
frozen 2.5 opaque-query control, thirty-two complete original `0x34` responses
and eight inherited mechanics cases remain checked.

The earlier exploratory runs preceded the final anchor/history policy and are
superseded by `implementation-anchored-results.json` and
`observed-anchored-final/regressions.json` under the ignored review directory.
Release evidence should use the parent’s final canonical build/validation run.

Reviewed source SHA-256:

| Source | SHA-256 |
| --- | --- |
| `firmware/ea9/src/focus_motion.c` | `e3b210b77aa61698f3c2e6f3e055dac0508d94d230bc204387bc4e1b46b8c920` |
| `firmware/ea9/src/focus_motion.h` | `ce40601bce58b8606d99aa8a3bb979769ab6c13b16c018d0b1e015c4550b3b1e` |
| `firmware/ea9/src/main.c` | `ce405a9e3b3d80408b6225976c40ff3e9cea0ab1c209c0ce20670d60494dc4a1` |
| `firmware/ea9/src/emount.c` | `1ec2c54ddd22ca0224422990fe55635414885f23b6b69cc571f503e0d94fbf38` |
| `firmware/ea9/src/emount.h` | `c84aaff99222cdf4b9b8d2130a083217d909a77a5cd9fc7b485cd04c1e59fad7` |

The pure factory law, wrapper, drivers and completion policy remain distinct
from this telemetry change. The review does not validate the final app package,
upload transaction, firmware pins or hardware readback. No factory parity,
improved focus lock, optical sharpness, correct saved exposure or physical rest
is established. Four-count-or-larger noise, slow/sub-resolution motion and camera
acceptance of conservative unknown/moving status remain hardware obligations.
