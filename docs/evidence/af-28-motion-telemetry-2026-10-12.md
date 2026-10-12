# AF 2.8: measured post-completion motion — October 12, 2026

The post-completion telemetry defect is corrected in the offline AF 2.8
candidate. Command completion no longer clears or clips the measured movement
state. The app is packaged as 0.11.0/build 14. No adapter enumeration, USB/HID
report, updater, flashing, motor operation or owner Application Support change
occurred. This is software validation; physical settling and camera AF/exposure
remain unqualified. The last recorded adapter image remains stock 1.8.

## REA basis and deliberate policy

REA recovers three facts relevant to this change:

- `0x8fc8` updates measured position/velocity history even when drive is disabled.
- `0x8d94` completes on target crossing or the common completion flag, without
  establishing zero velocity or a quiet settling interval.
- `0x5120`, with its phase gate open, copies the same sampled position into both
  `0x06` position fields, irrespective of the completion flag.

The tracked [original-instruction replay](../../scripts/test-stock-motion-reporting.py)
passes 12 frame-sync and 18 completion fixtures. It explicitly seeds nonzero
status bytes to check that this particular frame-sync writer leaves them alone.
[Retained results](af-28-stock-motion-oracle-2026-10-12.json) declare the seeded
gate, synthetic extremes and original-byte identity. These fixtures establish
that local writer/decision, not every possible firmware writer or physical
settling. The [independent audit](../audits/af28-motion-telemetry-review-2026-10-12.md)
records protocol confidence and the integration review.

Upstream evidence marks `0x05` bit 6 as focus-motion reporting, while the `0x06`
rest bit is probable and direction/polarity interpretation is less certain.
Forecast equality does not prove rest: native/manual modes can suppress
prediction, and factory frame sync copies equal positions. The factory backend
therefore restores that equal-position behavior and removes the upstream
predictor from its linked image. The legacy host backend retains its predictor;
its measured movement flags also belong to the independent observer.

## Pure observer and integration

[`focus_motion.c`](../../firmware/ea9/src/focus_motion.c) has no device, timer,
protocol, target, motor, completion or fault dependency. Callers supply fresh
validated unwrapped tracker counts, milliseconds, VD counter and negotiated
10–30 ms period. Its state is session/reference-local.

Movement is measured relative to a retained raw anchor. A displacement of at
least the existing four encoder counts establishes direction and movement;
quiet frames do not rebase that anchor, so slow cumulative drift is eventually
seen. This avoids one-count chatter at an absolute quantization boundary.
Four counts are the existing protocol resolution, not an owner-unit noise gain.
The observer does not claim that smaller displacement means physical stillness.

Rest requires a whole negotiated period, at least one new VD, and no observed
resolution-sized displacement during that interval. Repeated same-timestamp
calls cannot establish rest. A late sensor sample, skipped VD, same-ms VD burst,
or more than two periods without VD invalidates freshness and rebases the
window. Unsigned subtraction handles clock and VD wrap. Unknown is a separate
internal state; it cannot silently become observed rest.

The caller uses existing moving/just-stopped status with direction zero for
unknown freshness. There is no demonstrated unknown wire sentinel. This is a
conservative candidate fallback, not recovered factory semantics. The existing
positive/negative direction codes are retained; optical polarity is unverified.

History preserves the previous candidate's signed raw displacement divided by
four, truncating toward zero, per consecutively observed VD. No elapsed-gap
movement is fabricated as one-frame velocity. A rebase clears history; the
first resumed VD seeds a baseline, and only the following fresh consecutive VD
can append a measured delta. An independent review caught the earlier partial-
interval resume proposal; its counterexample is retained as a regression.
Empty history zeros are not measurements of missed frames. The internal factory
history and PID velocity have different timing/sign contracts; this per-VD
candidate history is not claimed equivalent to either.

`main.c` samples the observer through `focus_report_at`, including idle samples.
Idle feedback is refreshed before `em_poll` can send pending status. Only
session initialization and committed tracker-reference reset clear the observer.
Move, Scan, Drive, retarget, Stop, deadline and completion do not clear it.
The same observer result supplies `0x05` motion and `0x06` movement/direction;
near-limit bits and existing position clamps remain in the transport module.
`em_clear_velocity` discards history after a gap/reference reset.

Factory PID, wrapper, motor/encoder drivers, reference policy, aperture policy,
optical packets, retarget budgeting, fault guards, completion events and motor
limits are byte-identical as source to 2.7. No braking gain, settling dwell,
optical calibration, exposure correction, factory-reference transplant or
undocumented aperture mode is added. A completion/Stop tail can coexist with
observed coast or unknown freshness. It remains an actuator/command outcome,
not physical rest or optical lock.

## Regression evidence

[Validation summary](af-28-validation-2026-10-12.json),
[finite regressions](af-28-regressions-2026-10-12.json),
[controller oracle](af-28-factory-oracle-2026-10-12.json), and
[build inputs/layout](af-observed-build-manifest-2026-10-12.json) pin the sources.

- 13 sanitized pure observer cases cover coast, slow movement, reversal/net-zero
  paths, stale sampling, skipped/missing/resumed VD, first-resumed history,
  same-ms bursts, reference reset, counter wrap, admitted margins, sub-resolution
  boundary jitter and slow cumulative movement across quiet frames.
- Four production-main tests check actual transmitted frames: small/full-travel
  coast, measured reversal plus Stop, and gap/reference reset. They check both
  motion channels, equal factory positions, event tails and checksums. Coasting
  eventually reaches resolution-limited rest after fresh quiet observations.
- The same coasting probe fails for the intended reason against exact frozen
  2.7 source: it reports at rest while the simulated mechanism still moves.
  Current small/full examples return with positive residual velocity and report
  movement. These are simulation results, not owner-unit measurements.
- 51 Swift tests pass, including preservation of the installed firmware variant
  for normal lens changes and rejection of unsupported future versions.
- Existing 30 wrapper, four target-budget, six queue/retarget, 510 event-sequence,
  13 legacy/11 factory lifecycle, 21 hardening per backend and 25 register-driver/
  delay/startup checks pass, plus eight metadata/AF profile fixtures.
- 7,323 original factory-controller comparisons still pass; altered gain is
  detected. Prior frozen 2.5/2.6 negative controls and 32 full original opaque
  `0x34` reply comparisons pass with their intended outcomes.

The inherited history regression now seeds empty history rather than fabricating
an initial jump from zero, seeds the first VD baseline, then verifies a genuine
following interval. Its frame cadence/ownership assertion remains covered.
Final-read fault injection now keys off the motion owner's active state, keeping
that guard covered after removing the factory predictor.

## Release, preservation and separate hardware work

[Contax Zeiss 50mm f/1.4 candidate](../../firmware/candidates/2.8.0/README.md):
20,480 bytes at `[0x5000,0xa000)`, profile at `0x9f00`, loader 2.8.0/BCD 0x28.
The linked image has 400 bytes of flash headroom, 2,200 bytes static RAM and an
unchanged 8 KiB stack reservation. High-water and physical timing are unmeasured.
No logger, legacy servo, predictor or heap allocator is linked into the factory
release. A forced ARM rebuild matches its bundled template. Native and Python
50mm preparation match byte-for-byte; app and standalone CLI signatures verify.

All 30 listed older binaries, trust pins, candidate manifests and public stock
recovery files remain byte-identical in
[the preservation record](af-28-preserved-releases-2026-10-12.json).
Frozen 2.7 regression inputs are materialized from `6d84407` with per-file digest
checks; [its historical reproduction](af-27-frozen-reproduction-2026-10-12.json)
is separate from current validation. Neither original 2.7 evidence nor a
historical failure is relabeled. Private unit backups/keys and raw scratch stay
excluded from Git.

The [separate runbook](../af-s-test.md) adds quiet-idle/noise acceptance alongside
loaded-lens exposure and bounded AF-S comparison. Noise spanning four or more
counts can keep movement asserted; neither owner-unit jitter nor physical
braking/settling is measured. Sub-resolution drift is not proof of zero velocity.
Camera acceptance of equal positions, unknown fallback and completion while
coasting remains unverified. No upload or hardware round trip occurred here.
