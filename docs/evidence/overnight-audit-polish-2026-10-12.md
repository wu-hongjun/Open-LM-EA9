# Overnight firmware audit, RE progress and polish — October 12, 2026

The requested three independent lanes completed a bounded overnight pass over
AF 2.6 commit `d023745022e9375c54282221be8d6fee4df2ad61`. That commit was
already on `origin/main` and was pushed/checked before the audits began. Root
integrated the reproduced fixes and measured optimization as **AF 2.7**, with
app **0.10.0/build 13**. No device enumeration, USB/HID report, updater, upload,
motor operation or owner Application Support change occurred. The last actual
adapter image remains the separately recorded, byte-verified stock 1.8 image.

## Independent findings and disposition

| Lane / finding | Evidence | Disposition |
| --- | --- | --- |
| Correctness: full completion FIFO loses Stop acknowledgement | Two completed tiny Moves then idle Stop, through production dispatcher and emitted status frames | Fixed in 2.7; bounded Stop-preserving overflow policy |
| Correctness: identical absolute targets spend all 16 redirects | Parsed request every 16 simulated ms; old session faults at the seventeenth repeated target | Fixed in 2.7; compare admitted quantized absolute destination before budget/PID/deadline reset |
| Correctness: predictor end reports rest while mechanics still coast | Original production-main simulator moves another 89 counts after an at-rest report in a full-travel example | Open; no guessed braking, settling or sensor-noise gains |
| Optimization: release still performs unused raw capture and flash-log decision work | Same compiler/options; baseline template reproduced exactly; 68+68 sanitized host runs match | Gate only diagnostic blocks with `EA9_NO_LOG`; retain all motion/transport/safety logic |
| App: corrupt firmware history silently leaves an old lens actionable | New isolated AppWorkflow test fails on the original implementation | Fixed; surface recovery state, hide stale verified lens and inhibit conflicting actions; preserve corrupt file |
| Factory RE: sensor boundary and restored reference previously stubbed | Three new C11 models, original instructions, exhaustive response words and startup-prefix traces | Tracked research extension; no factory-reference transplant into custom coordinates |

Read the full [correctness audit](../audits/night-firmware-correctness-2026-10-12.md),
[optimization audit](../audits/night-firmware-optimization-2026-10-12.md),
[factory progress](../reverse-engineering/stock-re-progress-2026-10-12.md)
and [independent integration review](../audits/af27-integration-review-2026-10-12.md).
The audit lanes did not edit production code; root owns the changes and release.

## Firmware policy and modular boundaries

`factory_af.c` remains the instruction-tested pure factory law. The change is
in `factory_servo.c`, which owns admission, cancellation, mechanical fault guards
and deadlines. Equal four-count wire destinations, including equal clamped
values, are consumed without spending a redirect or resetting the leg. Raw
relative/defocus operands are resolved by the caller first; a repeated delta
that resolves to a different absolute destination still counts as a new leg.
Feedback validation, Stop polling, total-time, runaway, wrong-way, no-progress,
I/O and timebase guards remain active. Distinct requests still exhaust their
finite budget; deduplication is not a way to extend drive indefinitely.

`emount.c` retains a two-slot foreground-owned completion FIFO, one event per
status frame. When full, a Stop replaces the newest completion while keeping
the oldest completion before it. A newer Stop removes a pending older Stop and
appends itself after intervening completions. This bounds space and protects
Stop without emitting stale order. During review the first in-place coalescing
proposal failed Stop → Move → Stop; it was corrected before release. This FIFO
policy is our explicit overflow policy, not a claim about the factory scheduler.

`EA9_NO_LOG` now removes raw pre-handshake/normal-window copies and diagnostic
foreground decisions/locals. Request snapshots, consumed-frame ownership,
negotiation, frame cadence, parsing, homing, queries, fault guards, focus service
and shutdown remain active. The independent optimization alone saved 640 flash
bytes and 620 static RAM bytes. After adding the new queue/retarget code and
version byte, 2.7 retains **524 bytes of initialized flash margin** and uses
**2,192 bytes of static RAM**, 620 fewer than 2.6. The 8 KiB reserved stack is
unchanged; per-function stack estimates do not establish runtime high-water.
The build now records the actual linked layout and requires at least one
256-byte row of spare flash. Profile overlap and RAM bounds remain enforced.
No diagnostic flash writer, legacy servo or heap allocator is linked.

Known aperture channels, opaque stock `0x34`, profile format, retained optical
rows, controller gains, motor limits and drivers remain unchanged from 2.6.
Camera metadata declares nominal f/1.4; the app reports actual iris as Unknown.
The passive physical ring controls stop-down. Camera exposure/AF acceptance and
`pl[46]` interpretation remain unqualified. No undocumented F-- sentinel,
exposure correction, new optical calibration or physical braking tune is added.
Obsolete scripted-test and two-instruction-ISR claims were corrected in comments.

## App and preparation

A failed local firmware-history decode now contributes an explicit recovery
error. The app no longer silently keeps the old verified lens actionable; it
retains the corrupt file for review, and recognizes a repaired valid history
on the next refresh. The before-test failed the stale-lens/action expectations;
the repaired implementation and complete app suite pass using synthetic state
and injected discovery, with no live HID operation.

The new digest-pinned `autofocusPolished` variant owns 2.7's resource and loader
identity. Explicit AF install/preparation selects it; the normal Device lens
profile action still preserves whichever supported variant was byte-verified.
All eight custom versions remain independently identified. Older templates
are frozen rather than rebuilt under their old versions. The current signed
app/CLI package is in ignored `dist/`; no app was launched against hardware.
Native and Python preparation of the 50mm candidate produce identical bytes.

[Prepared candidate and reproduction commands](../../firmware/candidates/2.7.0/README.md):
20,480 bytes, application `[0x5000,0xa000)`, profile row at `0x9f00`, BCD `0x27`.
Template SHA-256 `da4eaa0f41fe9ff5b2c896ee7d5d2526cfc8fa423f581b5f55f9a1ff3c2059bf`.
Personalized SHA-256 `e124d09ad3eb272fab699035ee1ff941417afa3c6dd900484e11ae44c9c890b4`.

## Validation

[Machine-readable validation](af-27-validation-2026-10-12.json),
[build inputs/layout](af-polished-build-manifest-2026-10-12.json),
[finite regressions](af-27-regressions-2026-10-12.json)
and [original controller comparisons](af-27-factory-oracle-2026-10-12.json)
retain exact source hashes and limits.

- 51 Swift tests: 7 LensCore, 34 DeviceKit and 10 AppWorkflow; variant-preserving
  profile changes include 2.7 and unsupported future-version admission remains rejected.
- 30 scripted factory-wrapper cases plus four quantized/clamped/cancellation/
  distinct-budget probes; six parsed command/FIFO regression cases.
- 510 Move/Stop sequences through length eight, checking actual transmitted
  tails, bounded depth, retained Stop and newest-Stop ordering.
- 13 legacy and 11 factory lifecycle cases; 21 hardening cases per backend;
  25 register-driver/delay/startup checks; eight metadata and AF profile fixtures.
- Frozen 2.6 fails both designated queue/retarget controls for the intended
  reasons; current 2.7 passes. Frozen 2.5's unsupported `0x34` override is detected.
- 56 opaque-query operand/length/sequence cases and two missing operands;
  32 complete original-instruction replies including original sender checksum.
- 7,323 original controller comparisons and an intentionally altered integral
  gain detected. The controller source is unchanged.
- Eight inherited mechanical targets, including subsequent movement after
  admitted small corrections and deadlines; these are simulation, not optics.
- New sensor/origin extension independently rerun: 68,648 finite cases/steps,
  wrong-byte-order mutation detected, four input/output guards passed.
- Locally signed app and standalone CLI built/verified; native/Python 50mm
  output compared byte-for-byte in isolated state. A forced ARM rebuild matches
  the bundled template exactly.

The new [frozen 2.6 input manifest](../../firmware/candidates/2.6.0/regression-inputs.json)
materializes byte-verified original sources from `d023745`. Its historical
regressions pass after current-source edits, with
[new reproduction evidence](af-26-frozen-reproduction-2026-10-12.json).
All **26** listed older templates, pins, candidate images/manifests and public
recovery files match their original bytes in
[the preservation check](af-27-preserved-releases-2026-10-12.json).
Private unit dumps and decryption keys remain excluded from Git. Raw audit/build
scratch remains ignored; public findings, authored models and sanitized evidence
are tracked. No historical camera/USB failure was relabeled a pass.

## How much factory firmware is reconstructed?

**Partial, not complete.** The existing 38-entry application host model is joined
by three bounded sensor/initialization models, for a union of **41 application
routine entries**. The new extension tests all 65,536 sensor response words,
selector/status boundaries, filter initialization, eight synthetic reference
sequences and eight original main prefixes through the first foreground poll.
The reader's byte order is big-endian with two low bits discarded. Factory
initialization first reports origin 4096, then settings restore can replace the
reference; raw sample 5000 with synthetic saved reference 4800 subsequently
reports 4146. Initialization → stop → restore → metadata order is tested under
explicit peripheral cuts. These facts do not establish a universal offset.

The whole ledger inventories 235 application and 145 boot entries. Discovery
counts and sums of overlapping finite test cases are not a reconstruction
percentage. Real SPI errors/readiness, peripheral/IRQ scheduling, homing-gate
reachability, optical calibration, boot/USB integration, some upper-image data
and `0x34` grammar remain open. No buildable factory-equivalent replacement or
physical factory AF parity has been demonstrated.

## Next evidence needed

The remaining telemetry issue needs a separate measured-motion observer design
with idle/coasting/reversal/reference-reset and stale-sample tests. Protocol
resolution and frame cadence can bound reporting, but owner-unit jitter and
settling have not been measured; this pass deliberately avoids guessed gains.
Actuator termination, physical rest and optical focus must remain distinct.

Upload of 2.7, physical reconnect/strict readback, loaded-lens lifecycle/aperture/
saved exposure and one bounded AF-S comparison are separate hardware work in
[the runbook](../af-s-test.md). No hardware comparison passed during this night.
The bounded audit/RE/polish pass is complete; its hourly continuation backstop
can be disabled once the changes are committed and remote equality is checked.
