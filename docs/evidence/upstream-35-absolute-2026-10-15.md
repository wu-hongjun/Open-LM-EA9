# Upstream C 3.5 — absolute target handoff and sampled time contracts

**Prepared offline; not uploaded or camera-qualified.** Root integrated distinct
Astra follow-ups 19/20 on frozen 3.4, measured one release-only counter omission,
and obtained exact-image stack and independent composition reviews 22/23.
Workload research 21 supplies limits rather than a guessed production change.
[Machine-readable evidence](upstream-35-absolute-2026-10-15.json) ·
[campaign](../audits/astra-hardening-campaign-2026-10-15.md).

## Changes supported by failing controls

[Target audit 19](../audits/astra-19-absolute-target-2026-10-15.md) reproduces an
unintended destination shift: main computes `want-here`, then the relative servo
reads another start and adds that delta. Even with every sample inside physical
advertised coordinates, a target at 5952 becomes 5984, or zero becomes -32. A
relative instruction resolving to 1400 becomes 1432. The shifted destination can
prevent arrival or spend a retarget merely correcting the initial shift.

The shared `servo_move_from(start,target,...)` entry uses main's existing sample
and resolved absolute target. Main deadband, predictor and servo now agree on
that pair; the controller reads fresh feedback before any drive. REL/DEFOCUS
resolution is unchanged, and in-place retargets keep their existing absolute
meaning. `servo_move_rel` remains available, sampling once and delegating to the
same control body. The diagnostic-only park uses its existing sampled position
and target zero. No duplicate controller, changed gain, mapping or new origin is
introduced. Twenty proposal cases pass, ten frozen invariants fail, and seven
legacy relative-API probes retain identical complete observed output.

[Time audit 20](../audits/astra-20-time-contract-2026-10-15.md) reproduces homing
accepting stillness after query or encoder work crosses a phase deadline.
A final unsigned elapsed check after the stillness sample prevents HOME_READY
at/after the 300/500 ms cap. Normal and ordinary-wrap success, original minimums,
and cap-minus-one success remain. Existing failure/cutoff and fault reason paths
handle rejection. The contract is the sampled post-operation acceptance time;
it cannot undo time already spent driving inside a delayed operation, or promise
physical cutoff at that instant.

The same audit demonstrates an exceptional signed-divisor predictor error in
the final pump of a timed-out move. Under the admitted coordinate bound, the
signed numerator magnitude is at most 33554432, so division by any positive
unsigned interval above INT32_MAX is exactly zero. The new explicit branch
implements that identity without a guessed latency threshold, changing neither
normal arithmetic nor smoothing. The approximately 49-day synthetic gap is not a
camera observation. Whole-counter-cycle aliases cannot be recovered from two
32-bit samples and remain deferred; no servo period or watchdog policy is added.
Audit 20 passes 62 executions, including 12 frozen failing controls, and 8 path guards.

## Measured fitting composition

The target/home overlay has 256 bytes before diagnostics. Adding the predictor
fix without cleanup leaves 248 and is rejected by the 256-byte release floor.
Root and Astra 21's ARM-preprocessed consumer review establish that
`em_frame_period_n` is read only by an excluded legacy logging page. Gating only
its increment under `#ifndef EA9_NO_LOG` removes no release reader, I/O or live
trace field. Actual `em_frame_period_ms` measurement stays active.

This omission saves 16 flash bytes and 4 static RAM bytes in the composition,
leaving 264 bytes before the unchanged 1 KiB log area. Code plus initialized data
ends `0x9af8`; static RAM is 3072 bytes; the reserved stack remains 8192.
The linked relative wrapper and legacy counter are discarded by section GC.
The compiler flags and per-unit optimization choices remain unchanged.
Measurements and release/debug parity scripts are in
[the workbench](../../firmware/upstream-hardening/next35/README.md).

The [3.5 image](../../firmware/candidates/3.5.0/README.md) has SHA-256
`04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632`.
Its 20,480 bytes, [manifest](../../firmware/candidates/3.5.0/contax-zeiss-50-f1-4.manifest.json)
(SHA-256 `a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de`)
and full delta patch reproduce exactly in two fresh builds. Six of 46 manifest
files change from 3.4: servo C/header, main, predictor, protocol C and version
header. All earlier published images/manifests/Trusted constants are preserved;
[56 prior artifacts and historical registry entries](upstream-35-preserved-2026-10-15.json)
match the committed baseline.

## Exact-final regression and independent review

The [final acceptance entrypoint](../../scripts/test-upstream-absolute.py) passes
on the fresh repeat build. It binds sources, image, manifest and bundled resource,
then runs retained commit/capture/diagnostic/query/numeric/home regressions,
new target/time checks, counter parity, both independent composition suites,
compiled stack evidence, nine compiled ARM writer cases and decoder boundaries
for actual 3.2/3.3/3.4/3.5 pins. The added decoder tests cover 37 synthetic
version/pin/page/native-manifest cases, preserving full-image installation checks.

The time fixture initially failed because it injected at absolute read ordinal 3,
which becomes the second feedback sample after the redundant entry read is
removed. The new 3.5 fixture injects at the first controller feedback sample:
ordinal 2 for 3.5 and 3 for frozen 3.4. Outcomes and wire expectations are unchanged.
The independent review keys its cut to active predictor feedback rather than
that ordinal. This is a fixture boundary correction, not relaxed firmware criteria.

[Review 23](../audits/astra-23-composition35-2026-10-15.md) passes 40 exact-source
composition cases, seven relative probes and four counter comparisons; four
correction-removed controls fail as intended. It executes home into absolute/
relative/defocus motion, phase deadlines with capture/session/shutdown/faults,
reference-reset epoch cancellation, first/final feedback faults, ordinary-wrap
retarget/arrival and exceptional final forecasts. Move/Scan/Drive caller tests
also show that an internal deadband `SERVO_OK` after an injected cancellation
does not publish completion or advance Scan. A near-target coordinate-capacity
rejection is excluded by actual tracker/target bounds; hardware SPI timeout is
nonreturning. No extra production patch is justified by that internal return.

The exact-final counter comparisons restore only its increment in private source
copies. Release/debug variants have identical VD period, real predictor/forecast,
complete wire, CS behavior and live-trace bytes over 17 samples, including counter
wrap. Each sends 34 simulated status frames and serializes 12 valid pages only
after an allowed flush into host memory. Root's separate baseline counter test
also passes four release/debug comparisons. No board NVM was accessed.

[Stack review 22](../audits/astra-22-stack35-2026-10-15.md) validates 46 sources,
133 compiler records, 138 linked functions, 462 call/branch sites, 14 indirect sites
and 17 runtime frames. The conditional all-vector envelope remains 1560 bytes
against 8192 reserved. Twenty negative evidence controls reject; an exact-budget
positive passes. The new analyzer is a checked transparent derivative of frozen
14 with only its default input path and 3072-byte RAM expectation changed. Source,
ELF/raw/image, callback words, call inventory, library bodies/frames and physical
caveats remain enforced. Fresh-build ELF/map container pins may be rebound only
after exact image/raw/manifest/source and normalized disassembly/symbol/program-
header equality. The final runner verifies analyzer integrity before loading it.

All 53 Swift tests pass. Signed app 0.18/build 22 and CLI package successfully;
isolated native preparation produces exact 3.5/3.4/3.3/3.2/3.1/3.0 images and rejects
an incompatible 85mm profile without output. Commands for earlier candidates retain
their versions. The current UI offers the explicit 3.5 action under USB tools.
No app was launched, and no canonical state store was changed.

## What remains unproven

The [public workload study 21](../audits/astra-21-workload-2026-10-15.md) freshly
validates 840 Entropy512 and 2035 LexOptical body 0x04 frames with zero query records.
Those archives do not establish real query batch size, rate or response deadline.
Twenty-eight synthetic controls document finite queue admission and split tails;
they do not demonstrate A7C II overload or justify arbitrary buffer growth.

The shared starting sample changes the initial control/guard sample baseline
and removes one sensor transaction. Source parity cannot establish physical
loop timing, motor/mechanical behavior, exposure, capture/shutdown reliability
or optical AF. Stationary feedback still does not prove infinity; donor optics
remain uncalibrated for the Contax lens. The actual iris is Unknown while the
compiled camera report remains nominal f/1.4. Factory reconstruction is
[partial](../reverse-engineering/status-2026-10-15.md); this candidate retains
the upstream controller rather than the historical factory-derived PID module.

No hardware enumeration/open/report/updater/flash/motor action occurred. Uploaded
3.2 still needs owner-confirmed physical reconnect and strict verification;
its pending journal and guard are unchanged. 3.5 is offline only. Resolve that
transaction before a separately authorized operation using the
[future camera/log procedure](../upstream-absolute-test.md). No new camera cycle
is requested by this document; factory parity and camera stability remain open.
