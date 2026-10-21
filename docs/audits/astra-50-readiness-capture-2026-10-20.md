# Astra50 — composed reference readiness and capture ownership

No downstream readiness/capture production defect is reproduced. This lane adds
an offline acceptance harness, without changing production behavior. The new
camera evidence identifies inhibited focus after failed reference; it does not
identify the shutter decision or map the retained raw owner to either reported
photo. Raw completion therefore continues to disable periodic status until an
ordinary readiness request succeeds.

The runner binds the frozen 3.9 image
`87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44` and manifest
`9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a`, verifies
all source pins and the host shim, and copies them into fresh private output.
Candidate mode checks the complete supplied candidate manifest, source tree,
image and shim. No frozen inputs or historical receipts are written.

The harness extracts actual foreground, home, report, query, focus-entry,
retarget, abort and focus-run functions. It links production servo, protocol,
frame, owner, shutdown, mapping, predictor and motion/trace modules. The new
validated encoder reset function is source-extracted when present, with its
coordinate assignment instrumented to count resets. Encoder input, motor pins,
time, interrupts and UART are synthetic boundaries. One tick advances at each
pump entry, making the supplied late-anchor deadline exact; no physical timing
claim follows. The focus input is a synthetic absolute target of 4200 protocol
units, resolved by production mapping to 224 encoder counts after origin reset.
The simple deterministic motor/encoder plant exercises the real servo loop; it
is not a model of physical stiction or optical focus.

Seven composed cases cover early and late successful home, failed home, session,
Stop and shutdown during home, and a new session between reference commit and
deferred-command execution. The successful cases assert one origin reset,
zero-based servo admission, the exact resolved absolute target, one servo call,
one Move completion, consumed pending ownership, and origin-relative current
and forecast positions with at-rest wire flags. They then execute three raw
readiness/ordinary re-arm cycles, retain an operand query during each silent
interval and deliver it after re-arm, acknowledge Stop, and complete shutdown.
The late trajectory moves until tick280 and holds; drive detach is asserted at
300. The frozen 3.9 acceptance assertion fails on that trajectory, while its
early home and five safety/ownership cases pass. Failed home never invokes the
servo or fabricates Move completion, while operand queries and shutdown remain
live.

Six specific mutants must fail their named assertion: keeping pending ownership,
omitting origin commit, rebinding a deferred old-session command to the new
session, suppressing Move completion, re-arming status after raw completion, and
blocking operand queries while inhibited. All C runs use ASan/UBSan and finite
10-second process limits. Synthetic wire checks verify length, checksum,
terminator, position/forecast, status, completion and query operands.

The lane49 overlay passes these cases and mutants. This establishes software
handoff under the supplied schedules; it does not establish that stationary
feedback is the physical endpoint, that optical focus is correct, or that the
camera accepts sustained captures. Lane49 owns the production homing/reset and
PWM-release change, including its register-level checks. Lane50 provides no
applicator and no speculative status-policy change.

Reproduce with a fresh private output:

```sh
python3 firmware/upstream-hardening/followup/50-readiness-capture/run.py \
  --apply49 --output artifacts/private/astra50-overlay-new
python3 firmware/upstream-hardening/followup/50-readiness-capture/run.py \
  --candidate PRIVATE_BUILD --output artifacts/private/astra50-candidate-new
```

No device enumeration, device opening, reports, flash transfer, physical motor
work, app/updater launch or canonical host-state access occurred. All operands
and frames in these tests are synthetic. Camera evidence and identifiers remain
private. This lane performs no Git changes.

## Final AF4.0 composition

The final `artifacts/private/reference40d` candidate passes all seven cases and
six mutation controls, retaining six frozen3.9 positives and the specific late
qualification failure. Private output is `artifacts/private/astra50-final40`;
the candidate receipt is `followup/50-readiness-capture/candidate40-results.json`.
Image SHA-256 is
`06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae` and manifest
SHA-256 is
`8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`.
The final failure-tail counter is also checked after a consumed inhibited Move,
with all first112 servo bytes remaining zero. The4.0 tail marker is versioned
separately by lane49/root; the unchanged3.9 decoder contract remains strict.

## Complete acceptance integration

The complete new4.0 master passes36 suite groups against `reference40d`, with
all49 source digests checked before and after,146 preserved release/recovery
artifacts exact, and historical registry entries unchanged. The receipt is
`firmware/upstream-hardening/next40/acceptance-results.json`; the full private
output is `artifacts/private/astra50-acceptance40-final1`.

The new next40 fixture adapters retain the14 historical template controls and
add source-extracted validated reset support. The former reset-session trigger
is moved to the coordinate commit boundary, preserving its assertions. The new
reset is an independent inhibition guard, so the candidate's home-inhibit mutant
explicitly removes both guards; the unchanged historical single-guard control
also runs against frozen3.9. These distinctions are documented in next40/README.

Private copies update only frozen harness compatibility: admitting version4.0
in ADC/shutdown/writer probes, rebuilding packet initializer controls using exact
candidate unit flags, and replacing now-supported4.0 with99.0 as the3.8 decoder's
unknown-version sentinel. The compiled packet writer, packet reset instruction
controls, original-stock capture/re-arm, old3.9 decoder307 checks, new4.0 decoder
373 checks, and final compiled composition remain actual executed checks.
Three master controls reject optimized Python, a wrong manifest and a wrong
image without writing an acceptance receipt. None of these adaptations edits
historical tests, artifacts, pins or receipts.
