# Eight-hour firmware hardening — October 15, 2026

**In progress.** Authorized window: **04:55:51–12:55:51 UTC**, October 15
(00:55:51–08:55:51 America/New_York). Hourly continuation is attached to this
chat, with an explicit end time. This document is the handoff between passes;
update the ledger below rather than starting another overlapping initiative.
Document, commit and push each completed, verified batch. At the deadline,
publish the actual results and unresolved gates, and pause the heartbeat.

The working foundation remains upstream C, with native Swift/IOHID on the Mac.
Use pinned upstream `d52ed06cc449918f938e0695fbf29a0c4141f2b2`, the archived
Entropy512/LexOptical evidence and the executable REA factory findings. Do not
transplant the entire earlier custom scheduler or controller merely because a
host fixture passes. Hardware observations and original-instruction comparisons
take precedence over proposed explanations.

## Hardware and release state

3.2 was [uploaded](evidence/upstream-32-upload-2026-10-15.md) before this work
window. In a later interactive turn, the owner explicitly requested resolving
its verification and installing 3.6, and confirmed physical reconnect. **3.2
strict verification passed at 12:02:46 UTC; the separate 3.6 upload completed
at 12:05:50 UTC and now awaits its own owner physical reconnect and strict
verification.** [Installation record](evidence/upstream-36-upload-2026-10-15.md).
No camera cycle/log retrieval occurred. These hardware steps are separately
owner-coordinated and do not extend the offline scope of scheduled passes.
Do not infer a reconnect from elapsed time or enumerate the adapter during a
heartbeat. Keep the pending 3.6 journal and reconnect guard intact.

Scheduled work is offline: no device enumeration/open, HID reports, updater,
flash, motor operation or canonical Application Support mutation. Preserve raw
backups, original factory firmware/recovery, keys, unit identity and real camera
exchanges privately. Preserve all released images and pins byte-for-byte. A
changed executable needs a new candidate version/digest and its own verification.
Do not overwrite 3.2 or silently select a new image in an existing CLI command.

## Priorities and acceptance gates

| Priority | Concrete work | Required evidence |
| --- | --- | --- |
| 1. Frame admission | Complete length/checksum/terminator validation; prevent checksum or window padding becoming operands | Archived positive corpus, malformed/truncated controls through actual production dispatcher; sanitizers; preserve nonzero tails |
| 2. Request ownership and capture | Reconcile factory phase-driven interrupted control exchange with upstream status/reply ownership; immutable request/sequence pairing | Original-instruction reference, adversarial CS/VD/TX orderings, failed controls against frozen source; no whole-scheduler transplant |
| 3. Shutdown and readiness | Audit pending-command priority, repeated/session-interrupted shutdown, bounded homing cancellation/failure and communication during motion faults | Composed production paths and explicit IRQ/peripheral cuts; preserve off state and finite work; no guessed origin/gains |
| 4. Diagnostics and footprint | Preserve initial breadcrumbs and fault evidence without active-bus NVM stalls; remove demonstrably unused work | Existing storage/power-cut/ARM writer tests; measured linker/RAM changes; identical protocol outputs where behavior should remain identical |
| 5. Release and host polish | Freeze a reproducible next candidate if justified, retain profile/variant boundaries and accurate app guidance | New version/pin, build/resource/native-preparation equality, relevant Swift and firmware tests; immutable older releases/recovery |
| 6. Camera acceptance | Startup/preview/aperture, one MF photo, idle/shutdown, then later bounded AF-S | Owner-confirmed reconnect + strict verification, one coordinated cycle and read-only logs first; saved-image/actual-setting evidence when available |

The first five gates can advance offline. They do not satisfy the sixth.
Factory PID reconstruction is substantial but factory-equivalent peripheral/
interrupt integration and A7C II optical behavior remain incomplete. Do not
label an offline candidate stable, camera-qualified or on par with stock.
Keep nominal camera f/1.4 and actual physical iris Unknown; do not introduce
guessed exposure compensation, aperture sentinels or optical tables.

## Pass ledger

### Initial pass: framing and operand boundaries

Added the independent, allocation-free C admission module in
[`firmware/upstream-hardening`](../firmware/upstream-hardening/README.md).
Frozen 3.2 currently dispatches complete-looking headers without validating
their full framing. Actual production-dispatcher tests reproduce **eight**
malformed admissions: checksum, terminator, zero/high declared length,
truncated init, header-only init, corrupt Move and a truncated larger frame
whose first complete Move record is still dispatched. The affected init fixture
can falsely arm handshake readiness; Move fixtures can publish a motor command.

Four additional checksum-valid short frames padded to a larger CS window
reproduce operand contamination: `0x08` capabilities, `0x01` offer, normal
`0x04` mode and normal `0x03` aperture observations can read checksum/padding.
The admission overlay bounds their semantic guards and request snapshot by the
validated frame length, retaining the actual window length for raw diagnostics.
It does not guess missing payload values or reject nonzero window tails.

The module passes **207,131 checks**, including **3,456 archived valid frames**
(both directions), every strict frame prefix, deliberate corruption, nonzero
tails, null input and the full uint16 length arithmetic boundary. There are
**1,240 padded valid windows** in this replay. The actual patched dispatcher
passes all **15 probes**, while frozen 3.2 fails the intended twelve malformed/
operand cases and passes the same three valid controls. ASan/UBSan are enabled.
The ARM Cortex-M0+ module object is **128 code bytes, zero static data/BSS**;
this is not a whole linked-image size or measured physical execution time.

[Machine-readable first-pass evidence](evidence/hardening-frame-admission-2026-10-15.json)
binds inputs, overlay and source hashes. No release was modified, no new image
was built/published, and no USB report or camera action occurred in this pass.
This is a tested integration overlay, **not an installed fix**. The capture
fixtures and shim do not execute real UART interrupt timing. No surviving A7C II
trace proves malformed input caused the observed freeze.

**Original follow-on plan (completed by the batch below):** audit request/status ownership using the
[factory interruption findings](evidence/af-30-camera-failure-2026-10-14.md).
Extend the production probes to CS/VD arrivals during status 05/gap/06 and
ordinary control replies, immutable request/sequence handoff and shutdown
priority. Reuse [`investigate-af30-capture-interruptions.py`](../scripts/investigate-af30-capture-interruptions.py)
as a factory oracle, not as proof that the failed AF 3.0 scheduler should be
restored. The gated overlay is staged in the test runner only. Plan any compiled
new candidate separately; first measure linked footprint because 3.2 has only
340 bytes before its diagnostic storage. Unused raw-capture work under
`EA9_NO_LOG` is a previously demonstrated optimization lead, not an approved
behavioral simplification until equivalent outputs are reproduced here.

## Primary and local references

- [Upstream C implementation](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9), re-opened October 15; repository reports Sony a9 II testing, which does not qualify A7C II.
- [LexOptical message implementation](https://github.com/LexOptical/E-Mount/blob/master/Message.cpp) and [archived evidence analysis](../references/analysis/prior-work-analysis.md).
- [REA reconstruction ledger](reverse-engineering/whole-firmware-reconstruction.md), [factory AF baseline](reverse-engineering/factory-af-baseline.md) and [sensor/origin extension](reverse-engineering/stock-re-progress-2026-10-12.md).
- [Previous independent audit/polish dispositions](evidence/overnight-audit-polish-2026-10-12.md).
- [One-cycle camera and log retrieval runbook](upstream-startup-diagnostic-test.md).


### Eleven-lane integrated batch: upstream C 3.3

The owner requested at least ten Astra lanes. All ten ran in waves, with an
additional independent host lane. [Campaign and reports](audits/astra-hardening-campaign-2026-10-15.md)
record findings, failing controls and dispositions. Root integrated verified
frame, capture/shutdown ownership, transport, homing, motor/servo/session and
aperture bounds. The independent composed-source review reproduced five
additional failures and fixed request-pointer lifetime and readiness/TX commit
races. The REA lane rejected a blanket sequence rewrite and documented deliberate
snapshot/shutdown policy divergences from factory behavior.

[Candidate 3.3](../firmware/candidates/3.3.0/README.md) is frozen offline, SHA256
`adc4b5de9a717b1a573425006ef565962bf5c56ab2233a4eca9192feb7ad11cd`.
Two fresh builds reproduce image/manifest/complete patch. Final-source 7 commit,
65 capture/session, 14 diagnostic and 9 compiled ARM writer cases pass; root
release cleanup 208 regressions and all 53 Swift tests pass. App 0.16/build 20 and
explicit new CLI preparation match that image. [Evidence](evidence/upstream-33-hardening-2026-10-15.md)
and [machine-readable results](evidence/upstream-33-hardening-2026-10-15.json)
retain limits and exact pins. Code plus initialized data ends 0x9a68, leaving 408
bytes before logs, with 3,076 static RAM bytes and 8 KiB reserved stack. Physical
stack high-water and IRQ/timing budgets remain unmeasured. All 47 prior released
image/manifest/recovery/pin artifacts are byte-identical.

**Hardware state unchanged:** no enumeration/open/report/updater/flash/motor or
canonical Application Support writes. Uploaded 3.2 still awaits owner-confirmed
physical reconnect and strict verification. 3.3 has not been installed. Read the
[future procedure](upstream-hardening-test.md); do not infer authorization to
flash 3.3 from this offline milestone.

**Next bounded offline passes:** audit the remaining query/event publication
and capture-state combinations against the original-instruction contracts;
add source-bound regressions for any demonstrated gap. Review whole-chain
stack/interrupt assumptions and remaining encoder/servo arithmetic ranges using
actual reachable bounds. Do not claim physical timing or optical parity. Keep
3.3 frozen; any changed executable requires a separately versioned candidate.
Do not respawn completed lanes just to fill the requested count. Preserve the
current installation journal and keep camera acceptance separate. At 12:55:51 UTC,
record actual results and pause the heartbeat as previously instructed.


### Follow-up source lifetime, numeric and whole-chain stack audit

Root continued the remaining query/event and numeric-bound scope using new
follow-up lanes 12–14 rather than respawning completed lanes. Astra 14 completed
the stack audit; automated content filtering interrupted Astra 12/13, and root
completed their benign local C tests and proposals. The existing 11 completed
Astra lanes remain separately recorded. No hardware or canonical state was used.

The [query audit](audits/astra-12-query-2026-10-15.md) reproduces an old-session
answer emitted in a new handshake's 0x06 tail, plus an unbudgeted replenished
worker. A staged epoch-owned, four-query-budget worker passes 22 cases, while
frozen 3.3 fails 18 intended scenario controls. Normal and raw-capture outputs
remain identical; four additional demonstrations retain the old stale wire bytes.
Shutdown/abort/inhibit queue facts and synthetic arrival-rate limits are explicit.

The [numeric audit](audits/astra-13-numeric-2026-10-15.md) reproduces four
signed-overflow cases reached through legal-format but inconsistent raw sensor
histories. A partial widening proposal passes them and preserves 3,614,554 normal
checks. The arbitrary predictor probe remains separately unproven reachable and
unfixed; whole-controller range closure is still required. The combined query/
arithmetic ARM measurement ends 0x9e84, 644 bytes beyond diagnostic storage; it
fails the required margin despite a successful text link. **No new image was
produced, published or installed.** Do not mistake the workbench for a candidate.

The [stack audit](audits/astra-14-stack-2026-10-15.md) establishes a conservative
conditional 1,560-byte compiled whole-chain envelope against 8,192 reserved bytes.
Root reran its analyzer and six negative evidence guards. Existing REA evidence
already resolves the intended stock MSP/VTOR handoff at 0x2510; CONTROL/PSP,
PRIMASK, inherited IRQ transition/state and physical execution remain unverified.
This result applies only to frozen 3.3, not the future overlays or measured safety.

[Workbench, tests and results](../firmware/upstream-hardening/followup/README.md)
retain exact scope, failing controls and proposals. All 52 tracked release/recovery/
pin artifacts, including 3.3, match the previous committed bytes. The previous
3.3 qualification stays offline-only; new known source findings should be resolved
in a separately versioned next candidate before promoting it for camera testing.
The pending 3.2 installation transaction remains unchanged.

**Next bounded pass:** finish reachable arithmetic closure and replace expensive
widening with a justified bounded policy or mathematically equivalent calculation;
recover the required code/data margin without removing fault guards or shrinking
reserved logs. Compose query ownership and rerun complete source/host/release
checks only when the proposal is ready. Review the unchanged completion/status
policies against REA where new evidence is needed. Keep all published pins frozen.


### Follow-up range closure and query flow: bounded C 3.4

Astra15 finished the production coordinate/servo/predictor certificate and actual
scale-field writer inventory. Root replaced the oversized partial widening with
coordinate admission before accumulation, keeping the original target, servo,
predictor and optical calculations. Astra16 reproduced admitted queries lost
when answer capacity was exhausted, and queries unserviced during active servo
or unhomed pumping. The new worker retains requests and services bounded pure
conversions through the existing foreground pump.

Independent composed review17 then found and reproduced false HOME_READY after
a coordinate rejection had already inhibited the driver. The final candidate
marks that home terminally failed, preserves the original fault and reference,
and clears pending motion. Six home cases and nine composed pump/servo cuts
pass; five guard-removed readiness controls fail as intended. Astra18 reviewed
the actual compiled nested paths: conditional 1,560-byte all-vector envelope
against 8,192 reserved bytes, with seven negative evidence guards. Root reran
those checks and validated normalized disassembly/symbol/program-header equality
for the fresh same-image build before rebinding only ELF/map path-container pins.

[3.4](../firmware/candidates/3.4.0/README.md), SHA256
`fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9`,
is prepared offline. Two builds reproduce image, manifest and full patch exactly;
code/data ends 0x9aec with 276 bytes before the unchanged logs. Exact-source
capture/shutdown, arithmetic, query, home/fault, compiled writer, stack and decoder
checks pass with failing controls; all 53 Swift tests pass. Signed app 0.17/build21
adds a separate explicit 3.4 action/commands, preserving earlier command images
and full pristine-tail verification. The 52 prior release/recovery/pin artifacts
are unchanged. [Unified evidence](evidence/upstream-34-bounded-2026-10-15.md)
and [future coordinated procedure](upstream-bounded-test.md) retain all limits.

**Hardware remains untouched:** uploaded 3.2 still awaits owner-confirmed physical
reconnect and strict verification. No enumeration/open/reports/updater/flash/motor,
app launch or canonical state mutation occurred. 3.4 is not installed and no
camera test is requested during scheduled work. Range closure does not calibrate
physical travel; distinct encoder reads can still shift the internal relative
target, exceptional timer-gap conversion remains, and exposure/optical/camera
parity is unverified. REA reverse engineering is partial, not a factory-equivalent
controller certification.

**Next bounded offline work:** inspect demonstrated remaining distinct-read
coordinate semantics and elapsed-time/critical-section assumptions without
changing gains or guessing physical origin. Require a production-path failing
control before another behavior change and version any future executable.
Review release/runbook usability and trace observability as needed; avoid
repeating passed suites without a new concern. Keep all published pins and the
pending journal intact. Continue only until 12:55:51 UTC, then publish actual final
status and pause the heartbeat as authorized.

### Follow-up target handoff and time contracts: upstream C 3.5

Astra lanes 19–23 completed distinct target, elapsed-time, public workload,
compiled-stack and independent final-composition audits. Main previously resolved
an absolute target from one position sample, then the relative servo sampled
again and shifted that target. The new shared-start entry keeps the resolved
destination and starting sample together. Homing now rejects stillness success
if its post-operation sampled tick reaches the phase cap. An exact arithmetic
identity handles unsigned predictor intervals above INT32_MAX without a guessed
latency threshold or changed gains.

The composition with all three fixes initially left 248 bytes before diagnostics,
failing the required 256-byte release floor. Consumer review and exact release/
debug parity support omitting only an excluded legacy logging counter increment;
actual VD period measurement, wire output and live diagnostics stay intact.
[3.5](../firmware/candidates/3.5.0/README.md), SHA-256
`04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632`,
ends at 0x9af8 with 264 bytes before unchanged logs, 3,072 static RAM bytes and
8,192 reserved stack bytes. The conditional compiled stack envelope remains
1,560 bytes; its physical high-water is unmeasured.

Two fresh builds reproduce image, manifest and complete patch. Exact final
regressions with failing controls, independent composition and counter checks,
20 negative stack-evidence guards, nine compiled ARM writer cases and decoder
boundaries pass. All 53 Swift tests pass. Signed app 0.18/build 22 and its explicit
new prepare/apply commands preserve earlier command images and strict full-image
verification. All 56 earlier release/recovery/pin artifacts and historical
registry entries remain unchanged. [Unified evidence](evidence/upstream-35-absolute-2026-10-15.md)
and [future coordinated procedure](upstream-absolute-test.md) retain exact pins
and limits. No app launch, hardware access or canonical state mutation occurred.

The public traffic review contains no query records in the inspected body 0x04
frames. It cannot establish real query batch sizes or response deadlines; its
synthetic capacity controls justify no arbitrary queue growth. Independent
Move/Scan/Drive cancellation cuts show an internal deadband return cannot publish
success after ownership cancellation, so no speculative completion patch was
added. Shared-start sampling changes the initial velocity/guard baseline and
removes one sensor transaction; physical timing, calibration, exposure and optical
AF remain unqualified. [Factory reconstruction remains partial](reverse-engineering/status-2026-10-15.md);
the current controller is upstream C rather than the historical recovered PID.

**Hardware state unchanged:** 3.5 is prepared offline only. Uploaded 3.2 still
awaits owner-confirmed physical reconnect and strict verification. Do not infer
that event, bypass its journal, flash during scheduled work or request another
camera cycle here. Preserve all published artifacts.

**Next bounded work:** pursue a specific remaining factory contract or observability
gap only when it has inspectable evidence and a production-path failing control.
Avoid tuning gains, physical origin, watchdogs or queue sizes from simulated
timing. Do not repeat passing release suites without a new change or concern.
Continue within the authorized window; publish final evidence-based status and
pause the heartbeat at 12:55:51 UTC.

### Follow-up startup ownership and diagnostic cohorts: upstream C 3.6

Astra24 extends the original boot-to-app trace and refines the conditional core/
interrupt assumptions: normal reset supports MSP use; the boot path preserves
CONTROL/PRIMASK/priorities, leaves NVM IRQ5 enabled with modeled reset peripheral
INTEN zero, and starts SysTick with TICKINT clear. This is original-instruction
progress, not physical exception delivery or a reason to rewrite startup.

The interrupted Astra26 turn supplied a startup lead; root reproduced a real
single-producer violation when foreground first-window rescue is preempted by
EIC. Independent Astra28 found that the initial global interrupt mask delays a
final UART byte past rescue, so root rejected it. The accepted scoped EIC setup/
start keeps UART and SysTick live and enables EIC only after rescue/reset. Its
287 asserted sanitizer cases include 41 against exact final 3.6 source, frozen
failures and placement controls. Two logging-only RAM RX snapshots are omitted
to retain the existing margin floor; all 22 release units have no read consumer,
logging-enabled tokens stay identical and complete trace/wire parity passes.

[3.6](../firmware/candidates/3.6.0/README.md) is prepared offline, SHA-256
`d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`.
Two fresh builds reproduce image, manifest and complete patch. Code/data ends
0x9af4 with 268 bytes before unchanged logs; static RAM is 3,064 bytes and stack
reservation 8,192. Astra29 validates the exact compiled ordering, 1,560-byte
conditional stack envelope and 29 negative evidence controls. Root's unified
runner passes on the repeat build, including retained production-path regressions,
compiled writer and decoder boundaries. All 53 Swift tests, signed app 0.19/build
23 and isolated native preparation pass. All 60 prior released artifacts/pins
and historical registry entries remain unchanged.

Astra25's separate host-only decoder fix identifies impossible page/cohort
layouts that previously falsely completed CRC-valid snapshots. Root replays 448
production histories, 896 version decodes, 19 frozen controls, 1,827 mutations,
six v1 repeated summaries and the existing boundary suites. Valid partial and
unassociated evidence remains visible; CRC consistency is not authenticity or
installation verification. Root27 separately executes compiled 3.5 peripheral
wait/emergency-GPIO guards: 11 positives and a guard-removed control. No physical
time bound is inferred. [Unified evidence](evidence/upstream-36-handoff-2026-10-15.md)
records exact inputs, honest lane dispositions and remaining limits.

**Hardware unchanged:** uploaded 3.2 is still pending owner-confirmed physical
reconnect and strict verification. No device enumeration/open/report, updater,
flash, motor, app launch or canonical state mutation occurred. Do not bypass its
journal or infer reconnection. 3.6 is not installed, stable or camera-qualified.
Factory reconstruction remains partial; the active controller is upstream C.

**Remaining bounded work:** review release/runbook consistency and any concrete
new contract gap; do not repeat completed lanes or tune physical timing, origin,
gains or queue sizes without new evidence. EIC coalescing and UART boundary
limitations remain explicit rather than guessed away. Preserve all published
images. Continue only through 12:55:51 UTC, then publish actual final status,
commit/push completed work and pause the heartbeat as authorized.

### Release guidance and original terminal-tail evidence

Astra30 identified four public documentation defects, including stale app/
firmware versions and the false claim that `--state-directory` isolates the
physical reconnect guard. Root updated current guides and current 3.6 build/test
entry points, retaining historical commands and image meanings. Sixteen static
after-checks pass; original source excerpts are pinned to the reviewed commit,
with separate current-guide link and source checks. No runtime code changed.

Astra31 closes a specific original-instruction gap left by lane04: terminal
shutdown tail, original interrupt-mask helpers, UART disable and sleep setup.
Root repeats 35 cases and nine wrong-interpretation controls. The old shutdown
test cut `0x51c8` before the formatter and mislabeled those bytes as final UART.
The corrected live replay observes original formatting and UART boundary
`0x9180`; all 25 cases pass, including malformed-input normalization and its
contrasting pre-format observation. Historical JSON and its pins remain intact
with explicit adjacent corrections. No firmware change follows from this result.
WFI is stopped before execution or given an explicit synthetic wake; physical
sleep/wake, cancellation, motor arrival and ordinary reachability stay unproved.

In a separate interactive sequence, the owner explicitly confirmed physical
reconnect for the old 3.2 transaction. Native strict verification plus an
independent offline audit passed at 12:02:46 UTC. The owner-authorized 3.6 upload
then completed at 12:05:50 UTC after a fresh two-pass backup exactly matching
verified 3.2. No reports followed START on the armed connection. 3.6 now awaits
its own owner-confirmed physical reconnect and full strict verification;
camera testing has not started. [Live record](evidence/upstream-36-upload-2026-10-15.md).
This does not change the offline boundary for scheduled runs or subagents.

Root's final checks for this batch pass: 35 original terminal-tail cases, nine
contrasting interpretations, 25 corrected historical-oracle cases and a rejected
pre-format-as-wire mutation; 16 current-guide checks and 214 relative Markdown
targets. All 60 prior release/recovery/pin artifacts, frozen 3.6 image/manifest/
resource and both historical shutdown-oracle JSON files are unchanged.
[Integration evidence](evidence/release-guidance-and-factory-tail-2026-10-15.json).
