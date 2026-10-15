# Astra lane 04 — factory instruction contracts

Completed offline October 15, 2026. This lane changes no production, release,
factory image, unit data, Git state, or device state. The frozen C 3.2 reference
remains SHA-256 `e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
The lane reviews proposed capture/shutdown/homing policies; it does not qualify
candidate 3.3 or establish factory equivalence.

## Material correction and new bounded fact

**Ordinary stored replies do not universally stamp incoming sequence + 1.**
Original dispatcher `0x58a4`, reached after original CS rise/fall instructions,
retains synthetic ID34 template byte 4 = `0xa5` for incoming sequences 0,
`0x71`, and `0xff` in mode1. Connected mode4 phase0 and phase6 do not dispatch
that ordinary reply. CS updates the two status template pointers with sequence
+ 1; that is not a universal stored-control rule. Lane01's proposed universal
stamp therefore lacks factory support and changes frozen upstream behavior.
Recommendation sent to root and lane01: remove that stamp unless independent
protocol evidence justifies it. This lane does not edit lane01 or integration.
The nine exact checks are in `ordinaryTemplateSequenceCases`.

**Delayed factory capture echo reads the current shared receive buffer.** After
original CS/VD processing schedules `0x5261`, replacing synthetic receive RAM
before running `0x5260` replaces the transmitted request ID/sequence as well.
Leaving the buffer intact returns the first request. The immutable-snapshot
model fails the replacement control. This establishes a callback-time data
dependency; it does not prove a physical DMA overwrite race is reachable.
Candidate immutable snapshots are a deliberate robustness correction, not an
exact reproduction of factory request ownership.

“Raw exact echo” also requires a bounded qualifier: `0x5260` invokes the
original formatter, which rewrites checksum and terminator. An intentionally
incorrect synthetic checksum/terminator becomes the normalized valid frame.
This is an existing-memory formatter test, not evidence that factory RX admits
those malformed frames. Candidate complete-frame admission can legitimately
reject them.

## Capture, shutdown, readiness and origin contracts

- Thirty-two phase/ID/callback-gate controls confirm that ID34 in phase0 or6
  does not select mode5; phases2/3/5/12/13 do. ID0a has a separate receive-side
  trigger. Disabling the callback gate prevents these CS-derived transitions.
  A supplied connected mode4 state reaches phases12→13→2→3→5→6 using explicit
  CS, VD and callback invocations. This improves a purely seeded-phase check
  but does not establish ordinary reset-to-connected reachability or timing.
- Original shutdown dispatch accepts ID16 only in mode1/class2 among six
  controls. Acceptance resets the shutdown state to0, even if it was2.
  Candidate any-phase ISR priority, first-request snapshot and sticky OFF are
  deliberate policy differences. They must be justified by their own fault
  and cancellation tests, not labeled factory-equivalent.
- Four state0/state1 shutdown controls confirm active park is conditional on
  persisted option `0x200004bc`. Enabled park arms a target of192 reference
  counts for advertised lower bound4144 and clears prior completion. Without
  park, state1 still waits for completion. The ordinary park steps preserve
  the saved reference in these controls. The timer callback with timeout
  counter300 sets completion and clears armed state: completion is not proof
  of physically reaching the target. Omitting active shutdown park is a
  candidate safety policy, not a factory emulation claim.
- Existing whole-firmware and phase2 evidence finds no ordinary enabling
  writer for homing gate `0x20000530`; unresolved pointer writes prevent a
  whole-program unreachability proof. Lane03 readiness, bounded attempts and
  homing cancellation are upstream policies. Factory homing cannot justify
  forcing that gate or selecting a mechanical origin.
- Four original sensor-position cases reproduce the saved-reference/seam
  examples in the October12 sensor extension. In particular sample8191 with
  reference8192 reports8191, rejecting a naive signed linear offset model.
  These are synthetic arithmetic cases, not calibration. No original saved
  origin or unit setting is imported into the candidate's unrelated tracker.

## Reproduction and cuts

Run from the repository root, with Unicorn 2.1.4 installed:

```sh
tools/rea-analysis/venv/bin/python \
  firmware/upstream-hardening/lanes/04-factory/test_factory_contracts.py \
  --output artifacts/private/astra-04-new-run
```

The runner requires a new output path and normal Python assertion execution.
The [sanitized result](../../firmware/upstream-hardening/lanes/04-factory/results.json)
records the cases, seven negative controls, exact source hashes and immutable
stock input SHA-256 `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
The original image hash is checked before and after execution. The oracle is
original Thumb instructions; expected outcomes are independently stated in
this runner. No decompiled vendor source or binary payload is published.

Explicit cuts: DMA receive start/stop `0x91c4/0x91ac`; transmit helper `0x51c8`
and UART send `0x9180`; timer scheduler `0x609c`; main critical-section,
delay, NVM, UART-disable and sleep-preparation helpers; final motor drivers;
sensor reader `0x89a4`. PORT registers are RAM-backed dummies. The runner
records UART bytes synchronously and invokes scheduled callbacks itself.
The main shutdown sleep tail is not exercised. No WFI/wake equivalence is
claimed. Position cases supply the raw sensor value; the existing sensor
extension, not this lane, executes the lower SPI wrapper boundary.

Validation passed: 32 phase/gate cases, one conditional connected status path,
two echo-ownership controls, one malformed formatter control, six shutdown
dispatch controls, nine ordinary sequence cases, four park controls, one
explicit timeout completion and four origin cases. Counts describe different
contracts and are not added into a firmware coverage percentage. Seven wrong
interpretations are rejected by concrete contrasting fixtures. Existing output
and optimized-Python invocations were separately rejected before output.

## Disposition and physical limits

Accepted recommendations for integration review: retain immutable snapshots as
an intentional robustness policy; preserve factory phase/gate qualifiers;
remove unsupported universal ordinary-reply sequence stamping; explicitly
record shutdown priority/park/OFF and upstream homing as candidate policies.
Root owns final disposition and integration verification.

Deferred: ordinary boot-to-connected reachability, DMA/IRQ ordering, complete
camera grammar, physical sensor failures, homing travel/polarity, persisted
settings interpretation and A7C II optical/timing behavior. Rejected in this
lane: equating synthetic shared-RX replacement with a demonstrated hardware
race; equating timeout completion with mechanical readiness; importing the
factory reference into an unrelated homed coordinate system; treating a host
pass as camera stability or full factory parity.

References reviewed: whole-firmware reconstruction, stock-phase2,
factory-af-baseline, stock-re-progress-2026-10-12, public host models/oracles,
and investigate-af30-capture-interruptions.py. The prior AF3.0 interruption
result remains valid under its supplied-phase/callback cuts. This work narrows
its raw-echo wording and supplies contrasting phase/ownership/sequence tests;
it does not restore that failed scheduler or infer the camera freeze cause.
