# Astra40–41 — AF 3.7 retained camera trace

The owner's authorized Astra investigation continued with two independent,
read-only offline reviews after root retrieved the failed camera cycle. No lane
accessed hardware, canonical Application Support, Git mutations or shared edits.
Both independently matched **all 49 source digests** to the
[3.7 manifest](../../firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json).
Source references below are line numbers in that reproducible manifest-matched
`src` tree, reconstructed by the [3.7 workbench](../../firmware/upstream-hardening/next37/README.md).
Root independently audited the backup and integrated the sanitized findings.
[Camera evidence and limits](../evidence/upstream-37-camera-failure-2026-10-17.md).

## Astra40: homing readiness

The explicit `home-failed` emitter is `main.c:778`. Its failure label can be
reached through shared iteration-budget exhaustion (`661`, `700`), failure to
observe qualifying drive stillness before its deadline (`675–682`), or failure
to observe qualifying settle stillness before its deadline (`704–711`). The
single marker cannot identify which branch occurred. Cancellation and
coordinate-inhibition exits use the separate cancellation path.
`startup_trace.c:118` retains the first nonzero fault without its occurrence time.

Failure inhibits motion and clears deferred work (`main.c:776–782`). Failed
homing is not retried (`794–795`); reference readiness commits only after both
phases succeed (`764–773`). Foreground focus service requires `g_homed`
(`1811–1816`), with independent readiness/inhibit rejection in `focus_exec`
(`1497–1500`). This explains a software path to inhibited focus after the marker;
it does not prove the camera-freeze cause.

Homing drives directly (`main.c:648–652`) and does not initialize the AF motion
collector. That collector starts at servo/deadband entry (`servo.c:145`,
`main.c:1276`, `motion_trace.c:12–23`), from static zero state
(`motion_trace.c:5`). Thus an all-zero collected record permits homing movement.
Legacy homing samples are compiled out by `EA9_NO_LOG`.

The [earlier readiness audit](astra-03-homing-2026-10-15.md) treats stationary
feedback as a software reference policy; frozen feedback/stiction can satisfy
it. The [REA comparison](firmware-correctness-2026-10-11.md) leaves the ordinary
enabling writer of stock homing unresolved and describes replacement
post-handshake homing as experimental. Neither warrants changing polarity,
timeouts or thresholds from this trace.

**Proposed discriminator, not yet run:** exact 3.7 homing linked with real
query/status dispatch and synthetic hardware boundaries. Separately exercise
drive deadline, settle deadline, frozen-clock work budget and a communication
pump that returns after crossing each deadline. Check bounded return, sticky
cutoff, no reference commit and defined subsequent protocol behavior. Existing
lane03 fixtures use a simplified one-millisecond pump. Also examine optical
query handling after inhibition (`main.c:1082–1085`, `1102–1105`) while foreground
remains outside normal focus service; a liveness question is not a demonstrated
camera-freeze explanation.

## Astra41: capture and shutdown ownership

The retained window has four ordinary owners and one raw owner. All are
accepted/taken/completed successfully in a valid session, with identity matching
throughout. All six TX START/RETURN pairs match immutable identity and flags;
none has an unmatched retained START. Raw completion precedes shutdown
admission and the returned shutdown echo. The UART-disable marker follows.

Relevant source boundaries are `em_owner.c:2` (raw classification and VD
readiness), `emount.c:369` (TX admission and immutable trace identity),
`emount.c:1766` (raw completion/retry clearing/status disable), `emount.c:774`
(shutdown admission/ownership cancellation), `emount.c:439` (echo to powerdown),
`main.c:891` (terminal sequence), and `startup_trace.c:47` (retention/sealing).

Local completion is established for these retained transmissions, not camera
acceptance. Status is disabled after raw completion, with no later retained
ordinary re-enablement before shutdown. Whether the body expected further
status is unobservable. VD-timeout/PA23 markers and an absent delay-return footer
do not establish camera power state or a delay hang; capacity was not exhausted.

**Proposed discriminator, not yet run:** synthetic replay of ordinary readiness
completion → CS interruption during status → VD release → successful raw echo →
additional VD pulses → shutdown. Check immutable pairing, retry clearing,
status gating and shutdown progress; vary an ordinary readiness request after
the echo and session/shutdown changes during TX. This can test a software wait
condition without claiming camera acceptance.

Neither review proves a new causal software defect. Retention omissions,
unknown actual focus/exposure settings and the absence of physical bus/motor
measurements remain limits. Do not remove guards or publish a remedy claim
without a discriminating failing control and a separately versioned candidate.
