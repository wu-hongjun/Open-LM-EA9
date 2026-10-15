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
window. **Owner physical reconnect confirmation and strict byte verification
are still pending.** Camera testing/log retrieval has not occurred. Do not
infer the reconnect from elapsed time or inspect the adapter during scheduled
passes. The earlier upload authorization is not permission to replace it with
an unreviewed future candidate. Coordinate hardware actions in the chat.

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
