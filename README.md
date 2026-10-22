# Open-LM-EA9

Research and development toward comprehensive, modular Techart LM-EA9 firmware,
a documented host communication protocol, and a polished, easy-to-use macOS app.
The initial target is a Sony A7C II and manually adapted Contax C/Y lenses.

The **macOS prototype uses native SwiftUI/AppKit and Swift IOHID**, following the
system audit. All flashed firmware is C. The [updated working recommendation](docs/system-design-recommendation.md)
is to build on upstream C and defer Rust while qualifying A7C II compatibility.

**Original stock 1.8.0 is restored and strictly byte/protected-data verified after
physical reconnect, as requested by the owner.** The entire 110,592-byte original
application slot and known metadata match. Boot code, saved records and factory
data are preserved; native state now reports stock. Custom-firmware camera logs
remain saved, and no further camera test is requested.
[Stock recovery record](docs/evidence/stock-18-af41-recovery-2026-10-21.md).

[Upstream C AF 4.1](firmware/candidates/4.1.0/README.md) for the original Contax
Zeiss 50mm f/1.4 passed strict installation verification but **failed camera
acceptance; further trials are held**. The owner confirms one photo saved after
a reported one-minute shutter delay/freeze; shutdown worked afterward. Actual
focus mode remains unknown. Read-only logs retain five power-on baselines,
a handshake/shutdown snapshot and a later startup `cs-rise-wait` failure. All 16 pages
are full, with code/protected data unchanged; the physical shutter cause remains
unresolved. App 0.24.1/build 34 disables ordinary 4.1 installation from any version,
while preserving read-only backup/recovery and all firmware pins.
[Camera evidence](docs/evidence/upstream-41-camera-failure-2026-10-21.md) ·
[Installation record](docs/evidence/upstream-41-upload-2026-10-21.md).

Three Astra lanes prepared the 4.1 checkpoint/watchdog/latch design. All 40 offline
firmware suites, 681 crash-decoder checks and 53 app tests passed; they did not
establish camera stability, physical homing or factory parity. Original recovery,
all 156 release/recovery/pin artifacts and every registry entry remain exact.
[Offline evidence](docs/evidence/upstream-41-crash-diagnostics-2026-10-21.md) ·
[Workbench](firmware/upstream-hardening/next41/README.md) ·
[Held test/log procedure](docs/upstream-crash-diagnostic-test.md).

The previously verified [upstream C AF 4.0](firmware/candidates/4.0.0/README.md), fixed to the
original Contax Zeiss 50mm f/1.4, passed strict USB installation verification but
**failed camera acceptance; further 4.0 trials are held**. The owner confirms two
files saved in reported AUTO mode, then a hard crash requiring battery removal.
Actual focus mode remains unknown. One read-only backup matches the pristine
installed flash/protected data exactly; all 16 diagnostic pages remain erased.
The crash left no persisted trace, so its location is unresolved. No extra camera
attempt is requested; improve crash persistence before another physical trial.
[Failure record](docs/evidence/upstream-40-camera-failure-2026-10-21.md) ·
[Installation record](docs/evidence/upstream-40-upload-2026-10-20.md).

App 0.23.1/build 32 disables ordinary 4.0 installation from every version and preserves
backup/recovery. The original image, original stock recovery and all prior pins
remain unchanged. Three Astra audits, 36 firmware suites and compiled evidence
remain bounded software results; they did not establish physical homing, reliable
capture/shutdown, optical AF or factory parity. The version 4.0 rollover only fits
the camera's one-byte BCD field.
[Offline evidence](docs/evidence/upstream-40-reference-2026-10-20.md) ·
[Workbench](firmware/upstream-hardening/next40/README.md) ·
[Held installation/test procedure](docs/upstream-reference-test.md).

The previously installed image is [upstream C AF 3.9](firmware/candidates/3.9.0/README.md)
for the original Contax Zeiss 50mm f/1.4. Upload and strict physical-reconnect
verification passed. **Camera acceptance failed; further 3.9 trials are held.**
The owner reports two photos followed by blocked further capture, with normal
shutdown. Saved-file status and actual focus mode remain unknown; AF-S is only
a tentative recollection. Read-only logs
retain a 300-tick drive failure with only 20 ticks of stillness-anchor age
(40 required), then 17 consumed requests and no initialized AF-servo snapshot.
Code/protected data are unchanged. The physical cause and shutter decision remain
unresolved. [Camera evidence](docs/evidence/upstream-39-camera-failure-2026-10-20.md).

Three Astra lanes reviewed drive-phase homing, subsequent focus requests and original factory instructions. The release removes an unused
blocking ADC dependency and adds bounded failed-home observations and a consumed
request count. The physical homing failure and shutter-block cause remain
unresolved; no guard is relaxed or completion fabricated.
[3.9 upload record](docs/evidence/upstream-39-upload-2026-10-20.md) ·
[Offline evidence](docs/evidence/upstream-39-homing-2026-10-20.md) ·
[Build/test workbench](firmware/upstream-hardening/next39/README.md) ·
[Separate upload/test procedure](docs/upstream-homing-test.md).

The previously verified [3.8 image](firmware/candidates/3.8.0/README.md) passed
upload and strict physical-reconnect verification, but **camera acceptance
failed and further trials are held**. The owner reports hunting, apparent focus
for one photo, a motor reset and no further photos; shutdown was normal.
Read-only logs identify `home-drive-unsettled` with code/protected data unchanged
and no initialized AF-servo snapshot. Actual focus mode and whether a file was
saved remain unknown. The retained capture/shutdown exchange cannot be mapped
to the first shutter attempt.
[Camera/log evidence](docs/evidence/upstream-38-camera-failure-2026-10-20.md) ·
[Installation record](docs/evidence/upstream-38-upload-2026-10-19.md).

The previous, held image is [upstream C AF 3.7](firmware/candidates/3.7.0/README.md)
for the original Contax Zeiss 50mm f/1.4. Seven additional Astra lanes prepared
motion fault snapshots, capture/TX ownership and post-flush shutdown tracing,
with strict partial-record interpretation. A lossless packet initializer and
compact diagnostics retain the flash margin without changing the controller or
wire layout. The firmware identity intentionally changes to 3.7. **3.7 is uploaded
and strictly byte-verified after physical reconnect, including an independent
full-image/protected-data audit. Camera acceptance failed: the owner reports
some movement, no achieved focus and a freeze after one photo. Further 3.7
camera trials are held.** A read-only backup retained a complete focused
snapshot with `home-failed`, matching local capture/shutdown TX returns and
VD-timeout/PA23 footers. The failure phase and freeze cause remain unresolved.
[Camera evidence and Astra review](docs/evidence/upstream-37-camera-failure-2026-10-17.md).
An [October 19 owner repeat](docs/evidence/upstream-37-repeat-camera-failure-2026-10-19.md)
confirms AF mode, two saved photo files before another freeze and battery
removal required for recovery. Its new summary again records
`home-failed`; diagnostic storage is now full, so detailed later events were
omitted. The hold remains in place.
[Live installation record](docs/evidence/upstream-37-upload-2026-10-17.md). [Evidence](docs/evidence/upstream-37-tracing-2026-10-15.md)
and the [held test/log procedure](docs/upstream-targeted-trace-test.md)
record the completed gates and limits. Hardware access occurred only during the separately
authorized owner-coordinated installation and verification.

The [eight-hour firmware hardening pass](docs/firmware-hardening-2026-10-15.md)
has closed and its heartbeat is paused. [Final results and remaining gates](docs/evidence/firmware-hardening-final-2026-10-15.md)
record source improvements and the failed 3.6 camera trial; stable firmware and
factory parity remain unachieved. The first eleven Astra
lanes produced frozen [upstream C 3.3](firmware/candidates/3.3.0/README.md).
Earlier follow-up audits produced [3.6 offline](firmware/candidates/3.6.0/README.md):
a scoped startup EIC handoff prevents competing receive producers while keeping
UART reception active, retaining 3.5's target/time and 3.4's encoder/query fixes.
It retains the upstream C controller and aperture policy. Exact repeat builds,
production-path regressions with failing controls, independent composition and
compiled writer/stack checks, and all 53 Swift tests pass.
[Evidence and limitations](docs/evidence/upstream-36-handoff-2026-10-15.md).
The offline decoder also distinguishes inconsistent or partial multi-boot logs.
**3.6 is uploaded and strictly byte-verified, but camera capture/shutdown failed.
Further 3.6 camera trials are held.** The owner reports slight focus movement,
shutter-press freeze and shutdown nonresponse. A read-only backup preserved 13
valid diagnostic pages: a sticky `servo-wrong-way` inhibit and a later shutdown
UART-disable marker. This does not locate the shutter failure or prove camera
power-off. [Failure evidence](docs/evidence/upstream-36-camera-failure-2026-10-15.md).
The owner authorized the interactive installation after
[3.2 strict verification passed](docs/evidence/upstream-32-upload-2026-10-15.md).
No hardware was accessed during scheduled work; the separate
[3.6 installation record](docs/evidence/upstream-36-upload-2026-10-15.md)
tracks the owner-coordinated USB steps. Physical compatibility remains failed.
Earlier released images and original recovery remain exact.

The prototype includes all eight requested lens profiles, local metadata editing,
versioned JSON import/export, verified USB backup, and a staged application
upload/read-back path for lens metadata. The current app (0.24.1, build 34) refreshes
connection and local verification history automatically. Device shows product
photos, connection, dated firmware and the last verified lens, with a dropdown
to choose and apply another profile on firmware that supports runtime profiles.
Lens Library remains a secondary gallery/editor.
It marks installed 3.6, 3.7, 3.8, 3.9, 4.0 and 4.1 as held and disables ordinary installation
of these failed images. The 3.9 and 4.0 install controls are disabled while held; explicit native
prepare/apply commands retain their historical pinned research meaning. Image
pins and read-only backup/recovery access remain preserved.
The upstream candidates use the original fixed 50mm profile; they cannot apply
runtime lens edits. [Factory reconstruction remains partial](docs/reverse-engineering/status-2026-10-15.md).
The **historical upstream C startup diagnostic 3.2 for Contax Zeiss 50mm f/1.4
was uploaded and strictly byte-verified after physical reconnect**. The owner
requested proceeding to 3.6 before a 3.2 camera cycle. It
repairs first-window opener loss reproduced in 11 frozen-3.1 cases, restores
stock lens ID 234 as a compatibility control and
adds bounded startup/handshake records in a reserved application tail. It retains
upstream's AF algorithms and optional aperture-field behavior. All 12 repaired
arrival cases, eight upstream host outcomes, nine compiled ARM writer checks,
seven decoder tests and 53 Swift tests pass. It is **not camera-qualified**;
the A7C II aperture/capture behavior remains unverified for that image.
The upload retained fresh backup, durable journal and physical-reconnect guards.
[Current installation and test record](docs/evidence/upstream-32-upload-2026-10-15.md).
[Candidate](firmware/candidates/3.2.0/README.md) ·
[Implementation/evidence](docs/evidence/upstream-32-startup-diagnostic-2026-10-15.md) ·
[One-cycle and log-retrieval procedure](docs/upstream-startup-diagnostic-test.md).

The **direct upstream 3.1 baseline for Contax Zeiss 50mm f/1.4 is uploaded and
strictly byte-verified after physical reconnect**. **Camera acceptance failed:**
the owner reports aperture `--`, no shutter release and no motor movement;
normal shutdown is confirmed. Further 3.1 trials are held. It builds the
current pinned upstream commit `d52ed06`, preserving its controller, protocol,
main loop, homing/park and driver C implementations. Only build compatibility,
version/lens constants and corresponding pupil-row configuration differ.
Both upstream host builds pass; all 53 Swift tests pass. App 0.14/build 17 and
the explicit native `apply-upstream` path retain fresh backup/journal/reconnect/
strict verification guards. This comparison is fixed to the original 50mm
f/1.4 profile; runtime lens edits cannot change its compiled firmware. A fresh
two-pass backup matched the previous verified AF 3.0 flash exactly. All 320 pages
were acknowledged; no post-START read was sent on the armed connection.
Fresh two-pass readback and a separate offline audit matched the full fixed
image/metadata and unchanged protected flash/factory data. Actual focus mode and
other settings remain unverified; motor silence alone does not prove an AF fault.
App 0.14.1 marks the image as held and disables ordinary baseline installation.
[Failure and five-case startup investigation](docs/evidence/upstream-31-camera-failure-2026-10-14.md) ·
[Installation record](docs/evidence/upstream-31-upload-2026-10-14.md) ·
[Baseline provenance and limits](docs/evidence/upstream-baseline-2026-10-14.md) ·
[Candidate](firmware/candidates/3.1.0/README.md) ·
[Upload/camera procedure](docs/upstream-baseline-test.md).

The previous **AF 3.0 candidate for Contax Zeiss 50mm f/1.4 was uploaded and
strictly byte-verified after physical reconnect**. Fresh two-pass backup/readback and
separate offline audits passed. **Camera acceptance failed:** the owner reports
half-press focusing followed by full-press freeze, no saved photo and battery-
required recovery. Further AF 3.0 trials are held.
[Failure and new factory comparison](docs/evidence/af-30-camera-failure-2026-10-14.md).
[October 14 installation record](docs/evidence/af-30-upload-2026-10-14.md).
The candidate was prepared offline,
with factory-derived capture interlocks/raw opener echo, priority shutdown
without new motion, and nonblocking bounded reference acquisition. Cancelled
homing needs a fresh motion command to retry, within a two-attempt per-boot
budget; faults remain sticky. The October 13 preparation pass used no hardware;
the separately authorized October 14 upload is recorded above.
[Implementation, factory evidence and limits](docs/evidence/af-30-candidate-2026-10-13.md).
[Candidate and exact pins](firmware/candidates/3.0.0/README.md).
25 new arbitration/readiness cases and 40 retained link cases pass; exact frozen
controls detect 8 AF 2.9 and 15 AF 2.8 defects. All 51 Swift tests, the full
firmware suite and retained original-instruction comparisons pass. The signed
app/CLI produce the same personalized image as Python. It has 392 bytes of
flash margin, 2,380 bytes static RAM and 8 KiB reserved stack, with high-water
and physical timing unmeasured. Older images and original recovery stay exact.

Historical **AF 2.9 camera acceptance failed and further trials are held**.
On that image, the owner reports focus followed by capture freeze
requiring battery removal, then reset movement with no later focus movement;
shutdown worked on the latter reboot. The actual focus mode/reference state
remain unknown. Software fixes do not prove the physical cause or factory
parity. AF 3.0 also failed capture. New finite original-instruction replay exposes a
phase-driven interruption/raw-echo divergence for five tested non-`0x0a` IDs;
the physical cause is not proven. No replacement firmware was built by this
investigation and no more AF 3.0 camera trials are requested.
[AF 2.9 failure record](docs/evidence/af-29-camera-failure-2026-10-12.md).
[AF 2.9 installation](docs/evidence/af-29-upload-2026-10-12.md).

The historical **AF 2.8 candidate is uploaded and strictly byte-verified after physical
reconnect**, but **camera acceptance failed**: the owner reports frozen preview,
poor focus response, darker exposure and a later shutdown hang requiring battery
removal. Further 2.8 trials are suspended. **Original stock 1.8 was subsequently restored
and strictly byte-verified after physical reconnect**, with a separate readback
audit. All 128 KiB match the stock snapshot immediately before AF 2.8 installation.
[Recovery record before AF 2.9 installation](docs/evidence/stock-18-af28-recovery-2026-10-12.md).
See [the camera failure record](docs/evidence/af-28-camera-failure-2026-10-12.md).
The software milestone was prepared and tested offline. A pure measured-motion
observer now preserves coast/reversal after command completion, requires a fresh
quiet interval before reporting rest, and discards stale per-frame history.
It follows REA's factory frame-sync behavior by reporting the same measured
position in both fields. Fixed aperture/opaque `0x34`, factory control law,
drivers and completion policy remain unchanged. See
[implementation, tests and limits](docs/evidence/af-28-motion-telemetry-2026-10-12.md).
The [October 12 native upload](docs/evidence/af-28-upload-2026-10-12.md)
completed with a fresh two-pass backup; no post-START read was sent. Subsequent
two-pass readback and a separate offline evidence audit matched the complete
candidate/profile and protected flash/factory data. The displayed f/1.4 is an
owner observation; it does not qualify exposure or AF. Older images and stock recovery are preserved. Sensor noise, physical settling, exposure and optical AF remain
unqualified; factory reconstruction remains partial. The candidate has 400 bytes
of flash headroom and uses 2,200 bytes of static RAM.
The app displays **Actual aperture: Unknown** separately from its fixed camera
f-number; the lens ring still controls the physical iris. The historical **AF 2.4
factory baseline** replaces the upstream controller with independently implemented
stock speed/PID/callback/completion semantics. Its pure controller passes 7,323
original-instruction comparisons. Its authorized upload and strict two-pass
USB verification passed, including an independent audit. **Its first owner
focus attempt failed**, with motor movement but no focus/photo release, a dark
view and no shown f-number in P/A. Further 2.4 camera tests are suspended.
Actual focus mode and exposure settings remain unverified. The unchanged
controller also reproduces small-correction and full-travel session faults in
the inherited mechanical simulator; these are readiness gaps, not a proven
hardware diagnosis. See [the failure investigation](docs/evidence/af-24-camera-failure-2026-10-11.md)
and [the baseline design](docs/reverse-engineering/factory-af-baseline.md).
AF 2.3 hardens received frames, command snapshots, Stop handling, bounded query
processing and startup waits. It was byte-verified after physical USB-cap
reconnect. With the 50mm lens and C/Y-to-M converter, the owner reports eventual
focus and substantial hunting; sharpness, actual AF settings and loaded shutdown
remain unverified. Original same-unit stock **1.8.0 was restored for comparison** and its full
application slot matched the original backup; the owner reported much less
hunting. After the failed AF 2.4 attempt, the original stock 1.8 application
has been restored again and **strictly byte-verified after physical reconnect**,
with an independent audit. The owner reports stock AUTO overexposure and a
selectable P-mode aperture, widest f/2, then one-stop overexposure at physical
f/1.4 / camera f/2. The reported exposure failure is accepted; the photo was
not retained and does not block firmware investigation. Exact cause, lifecycle
and controlled AF-S remain unqualified. [Historical stock exposure record](docs/evidence/stock-18-af24-recovery-2026-10-11.md).
During the earlier stock comparison, camera use before readback changed 13 stock saved-motion bytes, causing strict
verification to fail. A later explicit reviewed resolution matched a fresh
backup to that audit and archived the failure without relabeling it a strict
pass; bootloader and factory data remain exact. [AF 2.4 installation and
reconnect progress](docs/evidence/af-24-upload-2026-10-11.md) is recorded separately;
comparison settings from the earlier stock report remain unknown.
AF 2.1 and 2.2 were previously byte-verified, with 2.1 owner reports of
motor movement and proper shutdown. For 2.2, the owner reports normal camera
startup, no observed startup movement without input, quiet idle and normal motor
shutdown. Homing and measured timing remain unverified. The converter is now
available for a controlled loaded-lens baseline.
The Biotar is 58mm f/2, as confirmed by the owner. For current offline firmware
reproduction, first follow the pinned toolchain and exact 3.6 source prerequisites
in the [3.7 workbench](firmware/upstream-hardening/next37/README.md). Existing
materializations are preserved; choose fresh private output paths:

```sh
python3 scripts/build-upstream-targeted.py --output artifacts/private/recheck37
python3 scripts/test-upstream-targeted.py --build artifacts/private/recheck37 --output artifacts/private/recheck37-tests
./scripts/swift-local.sh test
./scripts/build-macos-app.sh
```

The earlier `build-firmware.py` and `build-upstream-baseline.py` reproduce/check
historical metadata/custom firmware and 3.1 respectively; they do not build 3.7.
On a fresh checkout, restore the ignored photographed assets as described in
[photo provenance](references/visuals/README.md) before packaging the app.
For interactive app use, open `dist/Open LM-EA9.app` after the build. Keep it
closed during CLI USB operations and offline runs; normal app refresh enumerates
connected devices. Building or passing tests does not authorize a flash.

- [Held fixed 50mm AF 3.7 tracing candidate](firmware/candidates/3.7.0/README.md)
- [AF 3.7 build/test workbench](firmware/upstream-hardening/next37/README.md)
- [AF 3.7 installation and one-cycle log procedure](docs/upstream-targeted-trace-test.md)
- [Held 50mm AF 3.6 candidate and exact pins](firmware/candidates/3.6.0/README.md)
- [AF 3.6 build/test workbench and prerequisites](firmware/upstream-hardening/next36/README.md)
- [AF 3.6 coordinated install, camera cycle and log retrieval](docs/upstream-handoff-test.md)
- [Direct upstream baseline and validation](docs/evidence/upstream-baseline-2026-10-14.md)
- [Fixed 50mm f/1.4 upstream 3.1 candidate](firmware/candidates/3.1.0/README.md)
- [AF 3.0 capture/shutdown arbitration and homing readiness](docs/evidence/af-30-candidate-2026-10-13.md)
- [Prepared 50mm f/1.4 AF 3.0 candidate](firmware/candidates/3.0.0/README.md)
- [AF 2.8 post-completion motion design and validation](docs/evidence/af-28-motion-telemetry-2026-10-12.md)
- [Prepared 50mm f/1.4 AF 2.8 candidate](firmware/candidates/2.8.0/README.md)
- [Independent AF 2.8 telemetry evidence and integration review](docs/audits/af28-motion-telemetry-review-2026-10-12.md)
- [Tonight's independent audits, integrated fixes and open issues](docs/evidence/overnight-audit-polish-2026-10-12.md)
- [Prepared 50mm f/1.4 AF 2.7 candidate](firmware/candidates/2.7.0/README.md)
- [Factory sensor/origin reconstruction and original-instruction tests](research/stock-1.8/extensions/2026-10-12/README.md)
- [AF 2.6 implementation and offline validation](docs/evidence/af-26-candidate-2026-10-11.md)
- [Prepared 50mm f/1.4 AF 2.6 candidate](firmware/candidates/2.6.0/README.md)
- [AF 2.5 implementation, testing and remaining camera gates](docs/evidence/af-25-candidate-2026-10-11.md)
- [Prepared 50mm f/1.4 AF 2.5 candidate](firmware/candidates/2.5.0/README.md)
- [AF 2.4 camera failure, controller counterexamples and stock recovery](docs/evidence/af-24-camera-failure-2026-10-11.md)
- [Completed stock recovery and planned display/AF-S comparison](docs/evidence/stock-18-af24-recovery-2026-10-11.md)
- [Historical AF 2.4 upload/reconnect and reviewed stock resolution](docs/evidence/af-24-upload-2026-10-11.md)
- [Loaded A7C II AF-S comparison procedure and observations](docs/evidence/af-24-camera-comparison-2026-10-11.md)
- [Explicit reviewed stock camera-use resolution policy](docs/stock-restore-resolution.md)
- [App 0.7, AF 2.4 factory baseline and validation](docs/evidence/factory-af-baseline-2026-10-11.md)
- [Prepared Contax Zeiss 50mm f/1.4 AF 2.4 candidate](firmware/candidates/2.4.0/README.md)
- [App 0.6 polish, firmware 2.3 hardening and offline validation](docs/evidence/software-polish-2026-10-11.md)
- [Independent firmware correctness audit](docs/audits/firmware-correctness-2026-10-11.md)
- [Reproducible stock 1.8 application model and finite comparison harness](research/stock-1.8/README.md)
- [Whole-firmware REA coverage and remaining boundaries](docs/reverse-engineering/whole-firmware-reconstruction.md)
- [Current Device dropdown, automatic refresh and lens-change guide](docs/macos-device-workflow.md)
- [AF 2.3 upload and reconnect byte-verification record](docs/evidence/af-23-upload-2026-10-11.md)
- [AF 2.3 loaded-lens hunting observation and lifecycle test plan](docs/evidence/af-23-camera-lifecycle-2026-10-11.md)
- [Stock 1.8 restoration and controlled loaded-lens comparison](docs/evidence/stock-18-comparison-2026-10-11.md)
- [Manual aperture, fixed camera reporting and unknown-aperture research](docs/manual-aperture-policy.md)
- [AF 2.2 upload and reconnect verification record](docs/evidence/af-22-upload-2026-10-11.md)
- [AF 2.2 bare-adapter camera lifecycle procedure and owner observation record](docs/evidence/af-22-camera-lifecycle-2026-10-11.md)
- [Committed original 1.8.0 application and encrypted same-unit recovery backup](firmware/recovery/stock-1.8.0/README.md)
- [AF 2.2 reference, timing, homing and completion design](docs/af-reconciliation.md)
- [AF 2.2/app 0.5 build, test and owner observation record](docs/evidence/af-reconciliation-2026-10-10.md)
- [Prototype user guide, stack decision and module boundaries](docs/macos-prototype.md)
- [USB lens apply procedure, profile format and recovery limits](docs/usb-metadata-milestone.md)
- [Current USB milestone measurements and camera checks](docs/evidence/usb-metadata-milestone-2026-10-10.md)
- [A7C II photograph confirms the 50mm lens metadata](docs/evidence/camera-50-metadata-2026-10-10.md)
- [Autofocus candidate, module boundaries and qualification plan](docs/autofocus-milestone.md)
- [AF-S installation, camera test and restoration runbook](docs/af-s-test.md)
- [50mm AF upload and reconnect verification record](docs/evidence/af-50-upload-2026-10-10.md)
- [Bounded waits, native AF support and readiness evidence](docs/evidence/autofocus-ready-2026-10-10.md)
- [Offline AF build and host-check evidence](docs/evidence/autofocus-candidate-2026-10-10.md)
- [REA reconstruction of the official AF controller](docs/reverse-engineering/stock-phase2.md)
- [Installable metadata firmware and build provenance](firmware/README.md)
- [Local profile format and qualified backup protocol](docs/macos-prototype-formats.md)
- [Prototype validation and connected-device results](docs/evidence/macos-prototype-2026-10-10.md)
- [Device overview and firmware-query validation](docs/evidence/macos-device-overview-2026-10-10.md)
- [Visual design and simple lens workflow](docs/macos-visual-design.md)
- [Photo sources, credits and offline asset verification](references/visuals/README.md)
- [Visual prototype validation](docs/evidence/macos-visual-redesign-2026-10-10.md)

- [Product direction, modular boundaries and stack-selection criteria](docs/product-direction.md)
- [Recommended system design and qualification gates](docs/system-design-recommendation.md)
- [USB-cap investigation and measured read-only access](docs/usb-cap-investigation.md)
- [Complete flash backup, chip/protection checks and physical-check record](docs/usb-cap-followup.md)
- [Proposed management-mode entry and recovery qualification](docs/management-entry-design.md)
- [USB-only development boundary and reconnect results](docs/usb-only-next-steps.md)
- [Parallel firmware, protocol and macOS audits](docs/audits/README.md)
- [Independent Astra implementation audit and optimization priorities](docs/audits/astra-implementation-audit-2026-10-10.md)
- [Astra audit corrections and offline validation](docs/evidence/astra-audit-remediation-2026-10-10.md)
- [Reference collection, sources and provenance](references/README.md)
- [Prior-work analysis and captured frame evidence](references/analysis/prior-work-analysis.md)
- [Reference implementation and recovered firmware](docs/reference-research.md)
- [Rust feasibility study (candidate only)](docs/rust-architecture.md)
- [Requested lens inventory](profiles/requested-lenses.json)
- [Host-test evidence](docs/evidence/upstream-hosttest-2026-10-10.txt)
- [Stock-image verification](docs/evidence/stock-image-verification-2026-10-10.txt)

The native app prototype is implemented. Local editing does not change the
adapter. Stock upload and byte verification have passed on this unit; the custom
50mm metadata image has also passed two-pass USB byte verification as firmware 2.0.0.
An A7C II photograph confirms 50mm, f/1.4 and the Contax Zeiss lens name in saved
EXIF. Focus mode, the camera display and clean shutdown remain unconfirmed
for that metadata-only session. A separate upstream-AF
candidate now has bounded peripheral waits, native AF upload/restoration support
and passes host and lifecycle checks. Its earlier 50mm f/1.4 image was installed
and byte-verified as firmware 2.1.0 after physical reconnect. The owner subsequently
confirmed motor movement and proper shutdown on the
A7C II; optical qualification was pending at that milestone. The previous
2.2.0 candidate makes the reference/timing/completion policies explicit, passes
host checks and is packaged separately. It was installed and byte-verified as
2.2.0 after owner-confirmed physical reconnect, with protected flash and factory
data checks passed. AF 2.3 subsequently added frame/command/Stop/startup hardening
and passed native two-pass USB verification plus an independent offline audit.
The owner then reported loaded-lens focus with hunting and requested a factory
baseline. The [stock restoration record](docs/evidence/stock-18-comparison-2026-10-11.md)
records exact application equality and the post-camera saved-settings mismatch; the
[AF 2.3 installation record](docs/evidence/af-23-upload-2026-10-11.md) is historical.
Application USB management and broader camera qualification remain pending.
Backup uses the qualified stock loader's CHECK/READ operations; follow
the user guide's closed-updater and physical-reconnect prerequisite.

Local source snapshots, supporting documents, the recovered official 1.8.0
application image, and a copy of the original updater are under references/.
Downloaded reference snapshots and the original updater remain excluded from Git;
their index, provenance, checksums, analysis, and verification scripts are tracked.
At the owner's request, the original 1.8.0 application and an encrypted complete
same-unit recovery backup are committed under `firmware/recovery/stock-1.8.0/`.
The decryption key and raw unit-specific evidence remain private. The original evidence
copies in artifacts/private/ are retained for existing links.
