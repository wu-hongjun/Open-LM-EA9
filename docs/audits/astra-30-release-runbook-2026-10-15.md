# Astra 30 — frozen 3.6 / app 0.19 release and runbook consistency

**Complete, offline documentation audit. Four bounded documentation findings;
root's documentation corrections pass the separate after-review below. No new
firmware candidate is justified.** The current 3.6 candidate page and
camera/log runbook agree with the handoff evidence. Public entry points retain
stale version/build guidance and one incorrect statement about CLI state isolation.
Root owns any shared documentation changes.

Read first: the [timed ledger](../firmware-hardening-2026-10-15.md),
[campaign](astra-hardening-campaign-2026-10-15.md), and
[3.6 handoff](../evidence/upstream-36-handoff-2026-10-15.md). Scope was README,
firmware index/candidate/workbench, app guides/UI command labels, and 3.6
installation/camera/log sequence. Source reads below establish documentation
facts only; prior source, host safety, diagnostic and stack audits were not rerun.

No device enumeration/open, HID, updater, flash, motor, application launch,
network, canonical Application Support access, release/pin modification, shared
documentation edit, Git index write or commit occurred. Uploaded 3.2 remains
pending owner-confirmed physical reconnect and strict verification. No reconnect,
installation of 3.6 or camera cycle is inferred.

## Reproduction evidence

Run from the repository root:

```sh
python3 firmware/upstream-hardening/followup/30-release-runbook/audit.py
```

[The static reader](../../firmware/upstream-hardening/followup/30-release-runbook/audit.py)
reads repository text from the exact original commit in `source-pin.json` using
read-only `git show`/`git ls-tree` and writes only its sibling
[result.json](../../firmware/upstream-hardening/followup/30-release-runbook/result.json).
It stores SHA-256 and line-numbered excerpt boundaries for each examined source.
The captured result records all eleven stated observations as true, app
**0.19.0/build 23**, and **167 local Markdown link occurrences with no missing
targets**. External URLs were not visited; Markdown anchors were not checked.
This is reproducible original documentation evidence, not a firmware regression
suite. Rerunning it after root corrects or commits the documents reproduces the
same original excerpts and stale-text observations; it does not read revised
working-tree documents. The separate `verify-after.py` below checks those current
documents, with no assumption that the pending hardware status remains unchanged.

## 1. Firmware index presents held 3.1 as the current offline comparison

Exact excerpt, `firmware/README.md:3–6`:

> The current comparison is a [direct upstream 3.1 baseline](../../firmware/upstream-baseline/README.md),
> prepared offline for the original 50mm f/1.4 profile. Its protocol/controller/
> main/driver C files remain upstream; it uses a separate reproducible builder.

The same index says at lines 40–41, `Current source builds **AF 3.0** under
\`ea9/build/arbitrated\`, with camera BCD 0x30 and loader 3.0.0.` This describes
the retained custom source tree, but no current 3.6 pointer or historical scope
qualifier is supplied. By contrast, the root README says 3.1 camera acceptance
failed and further trials are held; 3.6 is prepared offline. The index never
mentions 3.2–3.6. The index's generic packaged-template statement at lines
110–113 also describes profile-row personalization, while 3.6 has no runtime
profile row (`firmware/candidates/3.6.0/README.md:20`).

**Narrow proposal:** replace the index's opening with current 3.6 candidate,
evidence and `upstream-hardening/next36/README.md` links; state 3.6 is offline
only and pending 3.2 must be resolved normally. Introduce the remaining material
as historical metadata/custom-AF implementation history. Qualify the 3.0 source
and profile-row statements as applying to that historical implementation.
Retain the old images, commands and historical findings exactly.

## 2. Current app guides identify older versions and omit the current action

Exact excerpts:

- `docs/macos-device-workflow.md:1`: `# Device workflow: prototype 0.15.0, build 19`
- `docs/macos-device-workflow.md:12–14`: `USB tools provide a separate **Install Startup Diagnostic 3.2.0** action; changing the dropdown does not install it. Other/edited profiles are rejected. The native CLI equivalents are \`prepare-startup\` and \`apply-startup\`.`
- `docs/macos-prototype.md:1–3`: `> Current app: **0.14.0, build 17** shows actual aperture as Unknown separately` / `> from the fixed camera f-number and packages the direct upstream 3.1 baseline.` / `> The baseline is fixed to the original 50mm f/1.4 profile and is prepared offline.`

These are linked from the root README as the current workflow and user guide.
`apps/macos/Info.plist:11–12` declares **0.19.0 / 23**. Current
`DeviceOverview.swift:244–245` contains `Install Upstream AF 3.6.0` and calls
`installStartupHandoff`. `EA9CLI/main.swift:8` maps
`prepare-handoff-upstream` / `apply-handoff-upstream` to
`.autofocusStartupHandoff`. Neither app guide documents that action.

**Narrow proposal:** update both current banners to 0.19.0/build 23 and add the
explicit 3.6 action/CLI names with the candidate and `upstream-handoff-test.md`
links. Retain the accurate 3.2 pending transaction paragraph; state its strict
verification precedes any separately authorized 3.6 install. Scope the
dropdown/profile-edit instructions to firmware with runtime profiles; all
upstream 3.1–3.6 candidates use the original unedited 50mm profile.
Preserve the old prototype text under a clearly dated historical section.
In particular its `Refresh is manual` (line 156) and `No install, restore ...
profile-apply action exists` (lines 162–163) belong to the dated prototype,
not current operation. The existing workflow's automatic-refresh section and
current `DeviceOverview.swift:237–246` already document the changed behavior.

## 3. CLI guide incorrectly says the custom state directory isolates safety state

Exact excerpt, `docs/macos-prototype.md:177–179`:

> private identity. `--state-directory PATH` can isolate the persistent reconnect
> guard for development; use the shared default in normal operation. Run only
> one USB client at a time.

Root identified this claim during integration review; this lane independently
captured the exact source contradiction. `EA9CLI/main.swift:23–27` passes the
chosen directory to `DeviceService(stateDirectory:)`, but the public initializer
at `DeviceKit/NativeHID.swift:129–132` says:

```swift
public init(stateDirectory: URL) {
    self.stateDirectory = stateDirectory
    safety = USBConnectionSafety(directory: USBConnectionSafety.canonicalDirectory)
}
```

The flag cannot isolate the persistent reconnect guard. A developer following
the text could incorrectly assume an isolated library/history directory makes
hardware commands independent of the canonical safety state. No such command
was run to demonstrate this; the public initializer is conclusive.

**Narrow replacement:** “`--state-directory PATH` selects the library and
update-history directory. The reconnect guard and USB exclusivity remain shared
in the canonical safety directory. Use only preparation commands for isolated
offline image generation; do not treat this flag as isolation for hardware
operations.” The prepare branch returns before inventory
(`EA9CLI/main.swift:33–41`). This corrects documentation only and preserves the
existing guard.

## 4. Root build block never invokes the advertised 3.6 build or acceptance runner

Exact excerpt, `README.md:170–175`:

```sh
python3 scripts/build-firmware.py
python3 scripts/build-upstream-baseline.py
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
./scripts/build-macos-app.sh
open "dist/Open LM-EA9.app"
```

`build-firmware.py:15,25–35` defaults to checking the frozen metadata template;
`build-upstream-baseline.py:51–53` sets version BCD 0x31. Neither rebuilds 3.6.
The root block does not call `build-upstream-handoff.py` or
`test-upstream-handoff.py`, despite advertising current 3.6 near the top.
Packaging can still include the committed 3.6 resource: this finding does not
claim an incorrect packaged image. It is a missing current firmware
reproduction/validation entry point. The existing block also opens the app,
which is outside the current offline campaign boundary.

**Narrow proposal:** make the current offline build section point to
`firmware/upstream-hardening/next36/README.md`, include the following supported
block, and retain any old builders under an explicit historical heading.
App opening should be a separately described interactive action because normal
refresh enumerates devices.

```sh
# Pinned toolchain/reference dependencies and exact 3.5 source materialization
# at artifacts/private/absolute35a must already exist; see prerequisites below.
# Choose fresh output names under the existing artifacts/private parent.
python3 scripts/build-upstream-handoff.py --output artifacts/private/recheck36
python3 scripts/test-upstream-handoff.py --build artifacts/private/recheck36 --output artifacts/private/recheck36-tests
./scripts/swift-local.sh test
./scripts/build-macos-app.sh
```

The hard-coded prerequisite is verified at `build-upstream-handoff.py:20,33–36`:
`BASE=ROOT/'artifacts/private/absolute35a'`; the builder checks that directory's
manifest, all sources and delta against frozen 3.5. If missing, materialize only
the missing prerequisites in dependency order using the documented fixed paths:

```sh
# Existing pinned dependencies/reference snapshot required. Do not replace an
# existing materialization; verify/reuse it. Output parents must exist.
python3 scripts/build-upstream-diagnostic.py
python3 scripts/build-upstream-hardened.py --output firmware/upstream-hardening/build/final-33a
python3 scripts/build-upstream-bounded.py --output artifacts/private/bounded34b
python3 scripts/build-upstream-absolute.py --output artifacts/private/absolute35a
```

The prerequisite chain is documented in the 3.6 → 3.5 → 3.4 → original hardening
workbench links, and confirmed by the corresponding builders' `BASE` constants.
The builders for 3.3 onward require fresh output paths; these are conditional
missing-input instructions, not a block to rerun over existing directories.
No builder or acceptance runner was executed during this documentation lane.

## Clean scope and limits

No concrete defect was found in the 3.6 candidate/runbook's release pins,
explicit command names, prerequisite reconnect/strict verification, manual iris
and nominal f-number distinction, MF-before-AF-S requirement, stop conditions,
or backup-before-another-cycle order. The runbook explicitly says ten-second
idle does not flush v2, terminal/battery-loss limitations remain, and changed log
bytes require `backup` plus the decoder rather than ordinary `inspect`.
It distinguishes structural validity, semantic trust and installation evidence.
These agreements are documentation review conclusions, not new physical or
decoder qualification. No optical/capture/shutdown or factory-parity acceptance
claim should be added, and no candidate change follows from this lane.

## Root integration and separate after-review

The findings above preserve the **original** source observations. Root subsequently
updated `README.md`, `firmware/README.md`, `docs/macos-device-workflow.md`,
`docs/macos-prototype.md`, and `docs/system-design-recommendation.md`. This lane
reviewed those working-tree diffs without editing the shared files.

Run the separate current-document check without overwriting the original result:

```sh
python3 firmware/upstream-hardening/followup/30-release-runbook/verify-after.py
```

[After-review script](../../firmware/upstream-hardening/followup/30-release-runbook/verify-after.py)
and [after-result.json](../../firmware/upstream-hardening/followup/30-release-runbook/after-result.json)
bind every original excerpt's source hash to original commit
`89e6d0dd2142e57c930540faa68632794769622e`, as fixed in
[source-pin.json](../../firmware/upstream-hardening/followup/30-release-runbook/source-pin.json),
separately record revised document
hashes/full text, and retain the original excerpts/hashes in `result.json`. All **16
after-checks pass**; all **204 local Markdown link occurrences** across the
current entry points and prerequisite workbench chain resolve. External URLs
and anchors remain outside this check.

The original comparison uses `git show` of that exact pinned commit, never the
moving checkout HEAD. Current HEAD is recorded separately. Root identified and
this lane corrected the initial use of moving HEAD before integration; rerunning
after a documentation commit therefore still checks the same original evidence.
Root also identified the original reader's initial use of working-tree files;
it now reproduces the pinned original commit and its tracked link targets.
Original excerpts/hashes were preserved when regenerating `result.json` with
the explicit source-commit metadata. Both documented commands were rerun and
passed after these reproduction corrections.

| Original issue | Root disposition reviewed |
| --- | --- |
| Firmware index calls 3.1 current | Current 3.6/evidence/workbench links added; old source/build/profile-row text explicitly scoped to historical implementation |
| App guides call 0.14/0.15 current | Both identify 0.19/build 23; 3.6 action/commands added; fixed upstream profile limits and pending transaction ordering explicit |
| Flag allegedly isolates reconnect guard | Text now correctly keeps guard and operation lock canonical; `USBConnectionSafety.swift:23,31` additionally confirms the lock uses the same safety directory |
| Current README runs only older firmware builders | Current 3.6 builder/runner provided, with prerequisite-chain link and fresh output rule; older command meanings preserved as history; app opening separated from offline validation |

The README now links the existing missing-input chain instead of presenting old
builders as the latest candidate. Source constants still require 3.2 diagnostic
materialization → `final-33a` → `bounded34b` → `absolute35a`; 3.6 then writes a
fresh private output. The workbench supplies each dependency step and warns that
parents must exist. No current runtime-profile or canonical-guard contradiction
remains in the reviewed edits. A residual AF 3.0 link labeled “the current
milestone” was reported to root and changed to a historical label before the
passing after-check. The system-design change scopes the prior Rust-first and
prototype recommendations as history and points to current 3.6 evidence.

No build, firmware/host suite, hardware operation or canonical-state access was
performed for this after-review. Root reported an owner-confirmed reconnect and
a separately coordinated verification operation while this lane remained
offline. This report supplies **no hardware result**; pending-status wording in
the captured documents describes their capture-time state and must be updated
only from root's actual installation evidence.

Root reran the current-document check after publishing the separate 3.2/3.6
installation facts: all 16 checks and **214** local Markdown targets pass.
The count above records the earlier Astra checkpoint. See
[root integration evidence](../evidence/release-guidance-and-factory-tail-2026-10-15.json).
