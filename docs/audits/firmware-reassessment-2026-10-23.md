# Firmware reassessment — October 23, 2026

**We have a buildable, recoverable experimental firmware, not a reliable A7C II
replacement.** Repeated local fixes did not close the camera's complete
startup → motion → capture → re-arm → shutdown lifecycle. Developing more AF
behavior before that baseline was repeatable was the wrong sequence. More
passing component tests cannot substitute for that missing result.

This pass uses three Astra lanes: [55, runtime/diagnostic causality](astra-55-failure-causality-2026-10-23.md),
[56, documentation consistency](astra-56-protocol-baseline-2026-10-23.md), and
[57, validation gaps](astra-57-validation-gap-2026-10-23.md). Lane 56's initial
runtime task failed with an automated safety flag; it subsequently completed
only a public-document consistency review. Root reviewed production source and
integrates the reports. The [receipt](../evidence/firmware-reassessment-2026-10-23.json)
binds the checks and preserved artifacts. No device access or new image follows
from this audit. Last verified installed state remains
[original stock 1.8.0](../evidence/stock-18-af41-recovery-2026-10-21.md).

## What is established

| Finding | Evidence and consequence | Boundary |
| --- | --- | --- |
| Diagnostic capacity can disable otherwise clean startup. | Production 4.1 appends a baseline before board/protocol initialization and halts when it cannot append. Actual-C tests reproduce 16 clean POR baselines followed by refusal of the 17th boot; a sufficiently populated terminal session exhausts it sooner. The camera backup has all 16 pages occupied. | Proven availability problem in 4.1. It can affect later boots; it does not establish the first shutter-delay cause. |
| A composed test substitutes the homing gate. | Historical lane 50 unconditionally defines `HOME_GATE_OPEN()` as 1. A private source mutation closing that gate still passes that runner. The corrected replay preserves the production conditional and rejects the same mutation at readiness. | Proven test boundary problem. The released4.1 gate is 1; this is not a newly discovered closed gate in the image. The frozen master also rejects changed source identities. |
| Recovered factory contracts are incomplete integration evidence. | The reconstruction ledger covers selected original routines and finite supplied states. The upstream C controller is not the recovered factory PID. Production blocking status/TX orchestration approximates a factory deferred-callback/phase machine. | We have not measured complete peripheral scheduling or camera deadlines, or established factory-equivalent behavior. There is no evidence that changing gains repairs the unresolved lifecycle failure. |
| Motion safety can leave AF unavailable. | Failed reference qualification and sticky inhibition reject further motion; `focus_exec` refuses execution without a valid home/reference. Earlier camera logs record failed homing followed by consumed requests and no normal-servo snapshot. | A safe motor stop does not establish a camera-understood failure/completion path. This can explain unavailable AF conditionally; the body's shutter decision and hard-freeze cause remain unproven. Do not fabricate success or relax motor guards. |
| Passing suites do not execute one complete physical camera lifecycle. | Capture re-arm tests supply VD/readiness traffic. Homing tests supply encoder trajectories, time and pumps. Shutdown-tail tests replace trace writes with zero-time hooks; watchdog/flash tests run separately. | These tests catch real local defects and remain useful. Their composition and clock/peripheral assumptions leave timing and reachability gaps. |
| The latest trace cannot correlate the shutter attempt to one execution boundary. | The4.1 backup contains several boot records, one handshake/shutdown cohort, and a later stage8 `cs-rise-wait` failure before watchdog arm. Events are filtered/evicted/omitted and storage is full. | Neither local TX return nor the later startup timeout proves why the earlier photograph took approximately one minute. No absent watchdog record proves where that failure occurred. |

Source binding is the exact4.1 image
`fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641`
and its [49-source manifest](../../firmware/candidates/4.1.0/contax-zeiss-50-f1-4.manifest.json).
The [boot/watchdog module](../../firmware/upstream-hardening/followup/52-durable-crash/watchdog.inc)
and [baseline-record module](../../firmware/upstream-hardening/followup/52-durable-crash/retained.inc)
provide the diagnostic gate. The [historical lane 50 runner](../../firmware/upstream-hardening/followup/50-readiness-capture/run.py)
provides the overridden test gate. Individual reports give exact source locations,
commands, failing controls and limitations.

## Why the upstream repository did not immediately solve compatibility

The [direct upstream 3.1 trial](../evidence/upstream-31-camera-failure-2026-10-14.md)
also failed on this body: aperture `--`, blocked shutter and no motor movement,
with normal shutdown. It was a useful comparison, not a demonstrated working
A7C II baseline. Subsequent fixes address real source faults, but none has
established repeatable capture/shutdown acceptance on this body. The upstream
code's historical measurements/comments cannot be treated as calibration or
camera qualification of this particular adapter, lens and body.

The [metadata-only 2.0 photograph](../evidence/camera-50-metadata-2026-10-10.md)
is a useful earlier positive control: a saved image carried 50mm, f/1.4 and the
lens name with motor motion disabled. It does not establish repeated capture or
clean shutdown. Conversely, a later saved photograph does not establish that AF
completion, capture re-arm and the next shutter attempt all worked.

All flashed application candidates have been C. Rust migration is unrelated to
these failures. The native Swift updater's strict byte checks establish which
image was installed and what data was preserved; they cannot establish runtime
protocol or optical correctness. The current evidence does not point to a
wrong image being uploaded as the explanation for these failures.

## What changes in this pass

1. Add a source-bound actual-C diagnostic/startup counterexample in
   [lane 55](../../firmware/upstream-hardening/followup/55-failure-causality/).
   It records the availability failure rather than relabeling the existing
   fail-stop policy as healthy behavior. Synthetic page shapes are explicitly
   synthetic; no private camera traffic is copied into tests.
2. Add the prospective [lane 57 corrected replay and regression](../../firmware/upstream-hardening/followup/57-validation-gap/).
   It preserves the real homing gate, checks both zero and positive delay,
   threshold/wrap behavior and a rejected closed-gate control. Frozen historical
   runners, release evidence and the 4.1 master remain unchanged.
3. Update README's reproduction entry point from historical3.7 to held 4.1;
   update the design's current status to restored stock/current host and label
   the older stack recommendations historical. Existing source coverage counts
   do not increase just because this review adds tests.

Root reran both new suites, including the historical false green, corrected
rejection and intended diagnostic-failure controls. Three additional controls
confirm that optimized Python (`-O`) is rejected before creating output, so
assertion-based validation cannot silently disappear. Root and Astra cross-review
keep the tested macro behavior separate from whole-device timing claims.

No runtime policy is patched and no4.2 candidate is prepared. Simply ignoring a
full/torn log would bypass the existing crash-latch design; that is not a
justified production fix. A future diagnostic policy must preserve genuine
fault latches and motor inhibition while separating ordinary log-capacity loss
from permission to start the camera protocol.

## Next development gate

Before another camera candidate, produce one falsifiable explanation of a
specific failure boundary and a regression against the exact production caller.
The useful work is narrower than another general hardening pass:

- Define the healthy-log-full versus real-crash contract, then test repeated
  startup/capture/shutdown lifecycles with persistence included. Preserve fault
  evidence and motor cutoff; do not add active-session flash writes casually.
- Exercise the production foreground, servo, protocol, trace and shutdown path
  together under supplied interrupt/time schedules. Fail explicitly for missing
  model boundaries; do not force readiness, skip the powerdown callback, or
  report a healthy MCU loop as proof the body is progressing.
- Compare the required factory phase/callback contract at the failed boundary,
  including who re-arms capture/status and when. Retain source/instruction
  evidence; avoid changing controller gains and protocol ownership together.
- Identify the smallest missing physical observation. USB-cap backups observe
  persisted state after the camera session; they do not observe live E-mount
  timing. A matched, correlated body session or electrical trace is still
  required for measured timing claims. Unknown focus mode remains unknown;
  exposure mode AUTO/A does not establish MF/AF-S.

Future hardware work needs its own owner-coordinated step. This review requests
no new camera experiment and leaves stock installed. Reproducible source fixes,
complete factory reconstruction and camera acceptance remain distinct milestones.
