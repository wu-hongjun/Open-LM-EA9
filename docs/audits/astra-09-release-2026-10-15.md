# Astra lane 09 — release footprint and reproducibility

Offline proposal for upstream C 3.3, October 15, 2026. Apply lane 09 last,
after frame/TX and lanes 02, 01, 03, 05, 06, 07, 08, 10. Lane 06 supplies the
motor overlay; do not also apply root `apply_motor.py`. Root owns integration,
versioning, Git and publication. This lane never accessed a device.

## Finding and disposition

**Accept:** `EA9_NO_LOG` made legacy `diag`/`trail` writers no-ops, but did not
remove their callers' volatile reads, receive captures, histograms, counters,
rolling focus records, or sensor operations. Consequently the composed release
spent RAM, flash and runtime work on evidence that had no sink. Lane 02 removed
the shutdown park call, but main still registered the legacy park function,
retaining a dead callback and its entire implementation in the linked image.

The final pre-09 composition fails its original linker with ROM overflow; its
code plus initialized data end is **0xa93c**, 3,388 bytes beyond the permitted
0x9c00. The failing control is compiled from the same full composition with
ordinary `-O2`, including latest lane 08 fault/capability records and lane 10
control-commit fixes. A private analysis-only ELF is emitted using
`--noinhibit-exec` to inspect symbols; it is never packaged as an image. Neither
the linker region nor factory upper-copy boundary is enlarged.

`apply.py` gates only obsolete diagnostic paths with `EA9_NO_LOG`:

- RX pre-handshake/raw-window capture, normal/mode histograms, raw message
  observations and ID/record tallies. Ordinary capability negotiation remains
  in its consumed-request path, and active startup trace events remain live.
- Main's dead page writers, quiet/failed-handshake logging work, rolling focus
  log and obsolete park registration/function/configuration.
- Home's legacy page construction, initial diagnostic-only 20 ms ADC burst,
  and raw encoder trace samples; the final reference and safety predicates stay.
- Servo's legacy raw trace samples and peak/duty-first bookkeeping. Endpoint,
  outcome, target, retarget accounting and motor/fault decisions stay live.

`flags.json` appends `-Os` for `main`, `emount`, `em_frame`, `em_owner`,
`em_shutdown`, `startup_trace`, `focus_dist`, `focus_map`, and `focus_pred`.
The last three are pure arithmetic modules; their source is unchanged. Motor,
servo, UART, encoder and timer units keep `-O2`. No gains, polarity, timer bounds,
packet tables, lens profile, diagnostics range, or optical assumptions change.

## Measured result

| Full composition | Code + initialized data end | Margin before 0x9c00 | Static RAM |
| --- | ---: | ---: | ---: |
| Before lane 09, O2 | 0xa93c | -3,388 B | 3,964 B |
| After lane 09 and pinned unit flags | 0x9a68 | **408 B** | **3,076 B** |
| Savings | **3,796 B flash** | | **888 B RAM** |

These are linked totals including 1,280 bytes of initialized data, not `.text`
alone. The existing linker can accept `.text` while its manually placed data
load address overflows the diagnostic boundary, so the explicit end-symbol
check is essential. `run.py` requires at least 256 bytes of margin, verifies
removed symbols are absent and `st_note`, `st_flush`, `st_write_page` remain,
and checks the padded 20 KiB analysis image has all 1,024 diagnostic bytes erased.
Two complete ARM builds reproduce identical bytes.

This analysis image retains the frozen version byte; root's reviewed builder
owns the 3.3 version change and final digest. The analysis image is not published
and must not be treated as an installable release.

## Verification and alternate test contract

`test.py` performs **208 before/after executions** with ASan/UBSan and bounded
subprocess deadlines:

- 18 aperture/metadata cases, including all 65,536 opaque operands. Every UART
  send's complete bytes and length are serialized and compared exactly.
- 59 ownership/capture/shutdown cases, including six interruption cuts, immutable
  snapshots, 9–256-byte captures, session changes and failed transmissions.
  Every emitted frame is also compared exactly.
- Seven actual servo-source cases compare outcomes, encoder-read counts,
  motor-write counts and inhibit states. Frozen clock, stale velocity, retarget,
  final inhibit, runaway and wrong-way cases retain lane 06 contracts. New lane
  08 inhibit reasons are asserted for budget/runaway/wrong-way faults.
- Nineteen actual extracted homing-policy cases per build cover reference,
  cancellation, session/shutdown changes, timeouts, retry limits and frozen
  clocks. The release explicitly makes zero idle ADC burst calls; the control
  makes at least one for admitted homing. Failed homing asserts lane 08's reason.
- All 65,536 input values for map/distance helpers and 40,000 predictor samples
  produce exact identical output with O2 versus Os, including clock wrap,
  retargeting, termination and both directions.

The host protocol and home fixtures use O2 before and Os after. Servo fixtures
use O2 in both builds. This checks semantic regression under the intended
optimization choice, not ARM instruction timing.

Legacy no-log telemetry assertions are intentionally replaced by an explicit
release contract: disabled raw-observation counters remain zero, while all
wire assertions are retained. A direct `park_to_infinity` test is inapplicable
to a release where its symbol and callback registration are absent; shutdown
protocol tests and symbol absence cover that contract instead. The removed
`burst-stop` injection point no longer exists; zero-burst and pre-/mid-homing
cancellation assertions replace it. Without `EA9_NO_LOG`, main/emount/servo
still compile on ARM with legacy instrumentation available for a separate bench
harness; this is not a second release configuration or a restored park call.

## Reproduce and preservation

From the repository root, choose a **new** directory under the private parent:

```sh
python3 firmware/upstream-hardening/lanes/09-release/run.py --lane10 --output artifacts/private/astra-09-recheck
python3 firmware/upstream-hardening/lanes/09-release/test.py --build artifacts/private/astra-09-recheck
```

Verified evidence is under `artifacts/private/astra-09-verified/`:
`result.json`, `regressions.json`, before/after link maps and logs, complete
staged source, private analysis ELF/images and host fixtures. The result records
applicator/flag/test hashes. The builder validates frozen 3.2 source and candidate
image hashes before applying overlays, and confirms byte-identical linker,
packet table, ADC, motor, UART and startup-trace source across lane 09. Its
before/after staging prevents writes to the frozen source tree.

All released images, manifests, recovery copies, host installation pins and
canonical Application Support state are preserved. No device enumeration,
HID traffic, flash/updater action or motor operation occurred. Deliberate source changes and retained artifacts are limited to this lane,
its report and `artifacts/private/astra-09-*`.

The removed idle burst advances homing admission by the former sampling time;
removed raw trace SPI transactions and compiler optimization change incidental
poll/IRQ cadence. ADC initialization, pump ADC sampling, actual control encoder
reads, timer bounds and fault guards remain. Offline fixtures do **not** establish
mechanical, electrical, camera, latency or factory parity. Physical qualification
remains a separate explicit action. The 408-byte margin applies only to the
recorded composition and toolchain; any later changes must rerun the gate.
