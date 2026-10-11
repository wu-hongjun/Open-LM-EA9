# App 0.6, AF 2.3 correctness and reproducible stock research

October 11, 2026, America/New_York. This work polishes the software while the owner
awaits a C/Y-to-M converter. **The installed adapter remains on byte-verified AF
2.2.0. No HID feature reports or firmware uploads occurred in this pass.**

## Product result

App **0.6.0, build 9** keeps Device as the first view and Lens Library as the
secondary photo gallery/editor. The Device view presents connection, dated
firmware identity and last USB-verified lens information, followed by the profile
dropdown. A compact status panel explains the next action and why a control is
unavailable. The selected-on-Mac preview reports the actual focal length and
manually reported aperture that will be encoded; choosing it remains local.

Guidance covers disconnected/multiple/unqualified devices, one-time setup,
missing firmware/lens identity, unsaved edits, incomplete zoom position, USB
acknowledgement, reconnect, pending verification, foreign-unit updates and a
completed profile match. The same operation guards drive both text and controls.
The two-second monitor still reads only OS descriptors and bounded local history.
It cancels with the view, skips busy work and resets acknowledgement on changed
connections. It performs no CHECK, READ or START.

The audit found two host correctness issues beyond presentation:

- A missing AF lens record previously fell back to metadata-only 2.0. The main
  profile action now requires verified variant identity, offering an explicit
  read when it is missing. Its fresh pre-upload backup must match the selected
  pinned code and a valid profile before START or journal creation. The first
  stock-to-metadata path additionally requires the pinned stock application.
  If another tool changed firmware, the backup is retained, local inspection
  evidence is refreshed and no upload starts. Explicit install/restore actions
  retain their variant-choice behavior.
- A stock/unsupported read previously could leave an older custom lens record
  visible. `LensInspection` archives that record, saves the read's dated version,
  and publishes a setting only after code/profile recognition. Supported stock
  leaves no custom lens setting. An unsupported image retains its new backup and
  clears stale lens history. A newer differing version observation also hides
  the older applied record before an explicit full-image read. Version comparison
  accounts for second-resolution observation timestamps so an ambiguous
  same-second update cannot retain a stale lens setting.

`DeviceWorkflow` owns presentation decisions; `AppModel` owns observable local
state and explicit actions; `LensInspection` owns verified-read publication;
DeviceKit retains qualification, same-unit backup, image admission, journal,
exclusive session and reconnect ownership. No management wire format was added.
New backup manifests identify the host as `0.6.0-prototype`; schema 1 is retained.

Packaging now stages and signs the complete app before replacing the last usable
bundle, with rollback on publication failure. The CLI still publishes a signed
new executable inode. The release app and CLI passed ad-hoc codesign/strict
verification. This is a local prototype build, without notarized distribution.

## Current-source AF 2.3 result

The [independent correctness audit](../audits/firmware-correctness-2026-10-11.md)
reproduced malformed-frame admission, incoherent interrupt snapshots, delayed
Stop, stale handed-forward commands, faulted Stop suppression, mixed-operation
completion, per-poll velocity history, oversized shutdown parking and unbounded
initialization waits. A final sustained-query regression also exposed foreground
starvation; each pass now consumes at most four FIFO queries before focus dispatch.

The fixes retain the existing pure reference/control/completion modules, upstream
controller tuning and board boundaries. Full received frames are admitted before
publishing commands. Bounded critical sections preserve the caller's PRIMASK.
Stop remains eligible after a motion fault without clearing that fault. Scan/Drive
replacements unwind their owner instead of announcing the old operation's success.
Status history advances once per newly observed body VD edge. An oversized
shutdown request cannot park without a complete supported echo snapshot.
Clock waits before SysTick use a finite poll ceiling without claiming measured
milliseconds; early core-clock failure enters inhibited idle before protocol or
homing. Later EIC/UART waits use existing sticky fault/deadline/poll policies.

This source builds as **2.3.0 / camera BCD 0x23**, with a separate resource and pin.
Frozen 2.0/2.1/2.2 resources and their digests remain unchanged. Their build-script
variants verify the released artifacts; they cannot relabel current source with
an older version. Current source builds only with `--variant hardened-af`.
Dependency identity checks remain active under optimized Python.

The [final build manifest](af-hardening-build-manifest-2026-10-11.json) pins all
production sources and dependency archives. The template is 20,480 bytes,
SHA-256 `8996767bfc8e8625739e1c7619a54db1dd0b8da8150526b9afa4c9a490434e88`.
Application code/profile remain within `0x5000..<0xa000`; profile is the last
256-byte row at `0x9f00`. Diagnostic flash writers are absent; linked motor and
servo entry points are present. The linker reports text 19,024, initialized data
1,280 and bss/stack 9,688 bytes; these are link sizes, not measured runtime peaks.
Only 176 bytes remain between current code/data initializers and the profile row,
so further firmware growth needs a reviewed layout or size reduction.

The [committed 50mm candidate](../../firmware/candidates/2.3.0/README.md) reports
Contax Zeiss 50mm f/1.4. Image SHA-256 is
`39222b5f5b232045a7599da1afc45753bb8ea0f12c338501131f49e0dcb854a4`.
Native preparation and Python personalization produce identical image bytes.
App/CLI image admission, backup, journal and reconnect verification accept 2.3
under its own pin while retaining older variants. **Main GUI profile changes
preserve verified firmware; explicit Experimental AF and CLI prepare-af/apply-af
select 2.3.** That installation action is available for a subsequent requested
hardware milestone; it was not invoked here.

## Factory reconstruction result

The prior REA work recovered a 235-entry application inventory and 145-entry
bootloader inventory, classified image bytes, and authored finite application,
NVM, boot/HID and USB models. Those inventory counts describe discovery, not a
semantic completion percentage.

This pass fixes the application model's reproducibility gap: the authored C11
sources, retained finite validators, portable runner, pinned dependency and
public fixture outputs are now tracked in
[`research/stock-1.8/`](../../research/stock-1.8/README.md). The C/header are
byte-identical to the earlier authored study. The oracle is the committed official
1.8 application, exactly 20,172 bytes with SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
No private unit settings, raw backup or recovery key are required to reproduce it.

The [reproduction record](stock-model-reproduction-2026-10-11.md) reran **24,991
original-instruction comparisons across 38 routine entries**, with two detected
negative controls and ten input/output guards. Root reran the public runner and
guards successfully. The [whole-firmware ledger](../reverse-engineering/whole-firmware-reconstruction.md)
retains the boundaries of the other local models and the remaining work.

The replacement AF controller is **not a port of factory PID**. Factory semantics
include reference-relative wrapping, integer incremental PID/history, callback
cadence and persistence that differ from the upstream replacement. The current
candidate keeps those distinctions explicit rather than mixing arithmetic and
timing assumptions. The original-instruction model is a comparison tool; it is
not a flashable replacement image.

## Verification

| Check | Final result | Claim boundary |
|---|---|---|
| Swift tests | 7 LensCore + 32 DeviceKit declarations + 9 workflow tests passed, including parameterized 2.0/2.1/2.2/2.3 variants | Simulated USB, local history and controller state; no hardware reports |
| Integrated C/profile runner | 83 invocations passed | Current source, simulated motor, memory-backed registers and 14 profile cases |
| Independent C/profile review | 83 ordinary + 57 ASan/UBSan invocations passed | 18 hardening, 13 actual-main lifecycle, 11 startup-register cases and other bounded suites |
| Frozen-source controls | 16 of original 17 hardening contracts fail on 2.2; valid padded frame passes | Declared counterexamples, not observed device failures |
| Isolated query control | Removing only the bound fails the refill regression | Deterministic ISR hooks; no physical latency measurement |
| Stock model | 24,991 comparisons; two negative controls; 10 guard tests passed | Finite dummy-register/stub contracts; no whole-program or hardware equivalence |
| Original recovery | 7 acceptance/failure tests passed with the private key | Offline AES archive recovery and exact original-file pins; no hardware restore |
| Image/provenance | Native/Python 50mm bytes equal; final source hashes matched; legacy pins unchanged | Exact artifact identity, not optical qualification |
| Packaging/UI | Release build, signatures, sourced assets and native layout inspected | Disconnected screen/local selection; connected states tested with fixtures |

Exact commands/output are retained in [the independent test report](firmware-correctness-tests-2026-10-11.json),
[Swift output](software-polish-swift-2026-10-11.txt),
[integrated firmware output](software-polish-firmware-2026-10-11.txt),
[recovery output](software-polish-recovery-2026-10-11.txt), and
[the structured summary](software-polish-2026-10-11.json).
Negative evidence: [frozen hardening](firmware-correctness-negative-final-2026-10-11.json),
[held startup waits](firmware-correctness-negative-startup-2026-10-11.json),
[query-only mutation](firmware-correctness-query-negative-2026-10-11.json).

The actual app showed no connected adapter during inspection. All eight menu
entries, corrected Biotar 58mm name, 85mm/f1.4 local preview and secondary gallery
were checked, and preparation was restored to 50mm. The final compact Device
layout was inspected after packaging. No Read/Apply/Install/Restore action or
USB acknowledgement was invoked.

## Remaining work and next hardware milestone

The factory's ordinary homing enabling writer, real peripheral scheduling,
interrupt ordering, some stored/configuration data and the upper prefix's purpose
remain unresolved. Other boot/NVM/USB models are still local analysis artifacts.
There is no freestanding reconstructed factory image or whole-firmware equivalence
proof. Unicorn's Cortex-M0 selection accepted an unsupported MOVW control in the
prior study, so the instruction comparisons do not prove ISA legality either.

The current candidate's 192-count coordinate bridge, 5952-count travel, homing
settle, sensor plausibility, controller tuning, stopping distance and camera
sample/transmit phase are not physical calibration. A stationary sample can pass
settling without proving an end stop. Queue overflow behavior and measured UART/
critical-section margins remain to be qualified. No claim that every loop is
bounded follows from the specific initialization and query fixes.

The original 1.8 recovery bundle is unchanged and already committed; its private
key remains outside Git. The AF-to-stock hardware restoration round trip remains
unqualified. No USB-cap runtime management service was introduced: the evidenced
cap path enters the retained stock loader, and profile changes currently use a
bounded application upload plus mandatory reconnect/readback.

Next, a separately requested 2.3 upload would require the fresh same-unit backup,
physical reconnect and complete byte/protected-region verification. After that,
qualify startup, quiet idle, Stop/park/shutdown and loaded AF-S with the 50mm lens
and converter, then inspect focus lock and original-image sharpness. That evidence
must precede lens-specific tuning, additional loads, AF-C or video work.
