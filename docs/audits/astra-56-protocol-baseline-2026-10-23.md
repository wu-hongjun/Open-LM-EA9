# Astra56 — documentation consistency and baseline evidence

October 23, 2026. **The reviewed documents do not establish a camera-qualified upstream baseline or factory-equivalent replacement.** Their current summaries explicitly reject both claims. The actionable documentation problems are stale current-version/build guidance and historical recommendations that still read as active instructions when reached directly.

This report is a documentation-only review of [README](../../README.md), [system design](../system-design-recommendation.md), [October 15 reconstruction status](../reverse-engineering/status-2026-10-15.md), and [sanitized 4.1 camera evidence](../evidence/upstream-41-camera-failure-2026-10-21.md). It does not independently validate their underlying binary, device, reconstruction or test claims. No runtime defect, firmware fix or camera root cause is established here. No hardware action, firmware change, installation or new camera trial is proposed by this report. Only this audit document is changed.

## Findings, in priority order

### P2 — “current” reproduction instructions select historical 3.7

**Documented fact:** README lines 284–297 introduce “current offline firmware reproduction” but direct readers to the 3.7 workbench, 3.6 source prerequisites and `build-upstream-targeted.py`/`test-upstream-targeted.py`. The same README lines 18–36 identify 4.1 as the latest held custom release and link its separate workbench. Its accompanying navigation at lines 304–309 also emphasizes 3.7/3.6 procedures.

**Inference and impact:** A reader following the current reproduction block can test a historical source composition while believing it represents the most recent failed image. Successful results would not answer questions about the latest release. This is a provenance/document-navigation defect, not evidence that either builder produces incorrect bytes.

**Small correction:** Label that block “Historical 3.7 reproduction” and put a short version-to-workbench index beside the current status. Keep the old commands intact as historical instructions. Require reports to name the exact version and source identity tested; do not present “all tests pass” without that binding.

### P2 — the linked current design summary stops at 3.6/app 0.19.1

**Documented fact:** System design lines 3–18 call their section the updated working recommendation, describe 3.6 as the most recent candidate and identify app 0.19.1/build24 as current. README lines 11–36 and 139–151 instead record restored stock 1.8.0, held 4.1 and current app 0.24.1/build34. The 4.1 evidence lines 79–92 independently records the same recovery/hold disposition within this document set.

**Inference and impact:** The stack choice remains consistent—upstream C development and native Swift host—but the status attached to that choice is stale. A reader can mistake a design recommendation for a recommendation to resume the obsolete 3.6 qualification workflow or miss the owner's latest request to remain on stock.

**Small correction:** Add a dated current-status paragraph linking the latest recovery/failure evidence, then label the October 15 narrative historical. Retain the C/Swift direction as a development choice conditional on camera qualification. State that stock is the documented installed state and that the failed custom images remain held.

### P3 — historical Rust and recovery gates retain active-looking headings

**Documented fact:** System design lines 44–48 explicitly identify the following material as the earlier October 10 recommendation. That qualification is correct. Nevertheless, its later heading “Recommended direction” introduces Rust-first guidance at lines 82–97; the final selection gate at lines 359–361 again directs choosing Rust if its prototype passes. Lines 156–159 say installation has not been performed, and lines 332–350 retain earlier recovery/prototype tasks. These statements are superseded as descriptions of current project progress by that document's own introduction and README's current status.

**Inference and impact:** Direct section links and excerpts lose the distant historical qualifier. The phrase “C has the collected working hardware reference” in the old table (line 97) can be read too broadly as evidence of A7C II qualification. It does not establish that: the current design introduction expressly records direct 3.1 failure, and README records later failures.

**Small correction:** Prefix the old section headings and table with “Historical October 10”; identify the scope of the hardware-reference claim or remove that ambiguous wording. Keep historical evidence available without leaving it as the apparent current action list. Do not rewrite historical outcomes as successes.

### P3 — the reconstruction status is correctly bounded but needs a current-status pointer

**Documented fact:** The dated status document explicitly says that reconstruction is incomplete (lines 3–6), records only a bounded semantic-model union (lines 13–20), and says the active upstream controller is **not** the recovered factory PID (lines 22–27). It distinguishes earlier 2.4–3.0 factory-derived experiments from the upstream development line. Its last recorded camera outcome is the 3.6 failure at lines 58–64.

**Inference and impact:** This is a sound historical technical statement, not a false parity claim. Its dated scope can nevertheless be missed because README links it as the general factory-reconstruction status. The word “active” describes a development line, whereas the latest README says the installed firmware is stock.

**Small correction:** Add a pointer to the current release/recovery status and qualify “active upstream C controller” as the upstream development candidate's controller. Preserve the historical case counts and their limitations. Do not update reconstruction coverage merely because more release tests were added.

## Claims that should remain explicit

No unqualified assertion of factory parity or successful upstream camera qualification was found in the reviewed current summaries. README lines 30–33 and 113–121 explicitly separate offline improvements from camera stability and factory parity. System design lines 28–32 expressly records the direct 3.1 failure. The reconstruction status explicitly rejects complete equivalence and factory-PID integration in the upstream line. These disclaimers are substantive and should remain beside any concise status replacement.

“Baseline” currently denotes several different things: exact restored stock bytes, the direct upstream 3.1 comparison, the historical factory-derived AF 2.4 controller experiment, and a future camera acceptance gate. None is interchangeable with a demonstrated working replacement. Use those full labels when summarizing them.

The 4.1 document is particularly careful about evidence scope. A saved photograph proves a file was produced in that reported attempt; it does not establish repeatable capture. A local handshake/TX record proves the recorded software milestones, not body acceptance. No initialized normal-servo snapshot does not exclude homing or other movement. Missing watchdog records and missing terminal footers do not establish where execution stopped. The later startup wait failure does not explain the earlier one-minute delay. Preserve those distinctions when compressing the evidence.

## Evidence needed for a trustworthy baseline

These are outstanding evidence requirements, **not instructions to perform another trial**. The latest documented disposition is restored stock and no further custom camera test requested.

| Question | What the reviewed record supports | Evidence still needed before a stronger claim |
| --- | --- | --- |
| Which image was tested? | Strict installation verification is documented separately from camera results. | Exact source/image identity attached to every new analysis and result; resolve the stale reproduction entry point first. |
| Why did direct 3.1 show aperture `--` and block capture? | README and design report that failure, normal shutdown and unknown actual focus/settings. | A causally discriminating startup/handshake observation tied to that failure; the four reviewed documents do not establish its cause. Do not infer an aperture-field fix from the display alone. |
| Why did later custom releases fail focus/capture? | README records differing observed failure patterns; 4.1 includes a saved file, freeze, incomplete trace and a separate later startup failure. | Correlation between the particular shutter attempt, boot/session, camera settings, protocol progress and motion/reference state. Similar owner symptoms do not establish one shared cause. |
| Is the reconstructed AF algorithm integrated? | Historical 2.4–3.0 used a factory-derived module; the upstream line uses a different controller. | A declared integration boundary and caller/scheduling evidence before claiming any factory-derived algorithm controls a particular candidate. Pure-controller comparisons alone cannot establish whole-firmware behavior. |
| Are ownership and timing correct end to end? | Reconstruction status documents finite dispatch/lifecycle contracts and deliberate policy differences. | Evidence covering actual interrupt delivery, peripheral timing, camera response deadlines and production callers. A design diagram or synthetic interleaving suite is not measured whole-device scheduling. |
| Was shutdown accepted physically? | 4.1 owner reports shutdown; software retains UART-disable, VD-timeout and a pin-write boundary. | Correlated physical/power evidence for any claim about the electrical shutdown sequence. A missing footer alone is not proof of a hang. |
| Can diagnostic exhaustion change operation? | 4.1 evidence lines 71–74 says a full tail intentionally prevents another normal start and may affect later use. | Explicit accounting for diagnostic capacity/boot cohorts in any future baseline plan. Do not attribute the first reported delay to exhaustion without temporal evidence. |
| Is optical AF/exposure qualified? | Partial owner observations, unknown settings and historical stock exposure limitations are documented. | Matched settings and saved-image evaluation for the specific lens/body/candidate. Restoring original bytes does not itself establish optical or exposure parity. |

The smallest useful next documentation step is one authoritative status block plus a version-specific reproduction index. The smallest useful investigation output is a single falsifiable explanation tied to the exact failed candidate and its observed boundary, with a stated counterexample and remaining hardware uncertainty. Repeating broad hardening totals, changing language stacks, or merging more reconstructed behavior would not fill the documented causal gaps by itself.

## Review validation

Reviewed all four named Markdown documents, compared their current/historical version and qualification statements, and checked the cited line locations. No binaries, runtime tests or device observations were used to substantiate this report. No firmware root-cause conclusion or production change is claimed.

Root integration subsequently corrected the README reproduction entry point and
the design's current status, labeled the earlier stack/selection sections
historical, and added a current-status pointer to the dated reconstruction
ledger. Line locations above refer to the reviewed `bd2ad4a` document versions.
The [consolidated reassessment](firmware-reassessment-2026-10-23.md) records the
separate runtime/test findings and their limits.
