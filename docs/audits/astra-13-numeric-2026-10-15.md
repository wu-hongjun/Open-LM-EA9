# Follow-up 13 — numeric reachability and partial arithmetic proposal

Frozen 3.3 has signed arithmetic that assumes a physically plausible tracked
position. The existing tracker prevents its own int32 addition from wrapping,
but responsive inconsistent raw samples can accumulate a much larger coordinate
before that guard trips. Root reproduces two arithmetic defects from legal-format
14-bit raw sample sequences. **The proposal is partial and not release-ready.**

Astra identified the range gap and drafted a source proposal. Automated content
filtering interrupted its turns; root finished the C harness, corrected extraction
and timing fixtures, reproduced the failures and measured the proposal. No device,
network, updater, physical motor, flash or canonical state action occurred.
No published source/image/pin was changed.

## Source-path evidence

The complete production tracker function consumes 525 consecutive raw steps of
±4096 counts (one quarter of the 14-bit circle), reaching ±2,150,400 without
tracker overflow. These are inconsistent sensor histories, not plausible physical
lens travel. The actual release STOCK controller then receives an in-range target
in the opposite direction. Its directional runaway/wrong-way guards do not reject
being far away on the expected approach side. The first control step overflows
`err * 1000`; UBSan fails in the actual compiled servo function before a later
synthetic abort. Positive and negative sequences reproduce it.

A longer 524,287-step history reaches ±2,147,479,552, still representable. The
actual relative-target function then overflows before its final travel clamp:
positive 32767 or negative -32768 deltas are legal signed protocol operands.
The fixture executes the complete production target function and tracker, not
an arbitrary direct INT32 assignment. Both signs fail under UBSan. The main
caller is not executed, so this establishes the target calculation defect and
source reachability, not a complete end-to-end camera schedule or timing claim.

The partial proposal widens relative/defocus target calculation before clamping,
and widens the servo error/profile intermediate before saturating to cruise.
Four corresponding proposal cases pass. The harness uses real focus-map,
distance and predictor C modules, plus extracted complete target/STOCK/tracker
and the actual servo implementation. It substitutes inert motor/timer/sensor
boundaries and stops the tested servo after its first control step. No hardware
is driven. All 3,614,554 normal-range checks produce the same output hash before
and after: `6324421738769268570`. These count conversion, relative-target
and predictor checks; they are not 3.6 million servo trajectories.

## Explicitly unresolved

A direct arbitrary `INT32_MAX` predictor sample also overflows, but its reachability
through guarded production motion has not been established. It intentionally
remains a failing hypothesis probe in both versions, not an accepted fix. Other
near-limit differences, elapsed-time narrowing, full main-call displacement,
scan/drive calculation and complete predictor/servo range closure remain open.
The proposal does not validate corrupted sensor history or establish a safe
physical travel coordinate. It does not qualify the whole controller for int32
input merely by making these four probes pass.

```sh
python3 firmware/upstream-hardening/followup/13-numeric/run.py --output artifacts/private/numeric-recheck
```

[Results](../../firmware/upstream-hardening/followup/13-numeric/result.json) distinguish
four fault-reachable frozen failures, a passing normal control and the separately
unproven predictor case. [The source applicator](../../firmware/upstream-hardening/followup/13-numeric/apply.py)
is private-scratch-only. Before candidate integration, finish range closure or
justify a bounded fault policy without guessing physical calibration, and measure
its cost. Current widening introduces expensive 64-bit division support; the
combined query/arithmetic proposal fails the application/diagnostic margin gate.
