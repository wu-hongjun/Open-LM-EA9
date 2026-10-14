# Open-LM-EA9

Research and development toward comprehensive, modular Techart LM-EA9 firmware,
a documented host communication protocol, and a polished, easy-to-use macOS app.
The initial target is a Sony A7C II and manually adapted Contax C/Y lenses.

The **macOS prototype uses native SwiftUI/AppKit and Swift IOHID**, following the
system audit. The production firmware stack is still being qualified; Rust is
a candidate, not a requirement.

The prototype includes all eight requested lens profiles, local metadata editing,
versioned JSON import/export, verified USB backup, and a staged application
upload/read-back path for lens metadata. The current app (0.13.0, build 16) refreshes
connection and local verification history automatically. Device shows product
photos, connection, dated firmware and the last verified lens, with a dropdown
to choose and apply another profile. Lens Library remains a secondary gallery/editor.
The **AF 3.0 candidate for Contax Zeiss 50mm f/1.4 is uploaded and strictly
byte-verified after physical reconnect**. Fresh two-pass backup/readback and
separate offline audits passed. The first loaded-lens MF preview/capture/idle/
shutdown check is requested; camera acceptance remains pending.
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
parity. AF 3.0 now has separate strict readback evidence; qualify its MF preview, saved
exposure and shutdown before AF-S.
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
The Biotar is 58mm f/2, as confirmed by the owner. Build and open:

```sh
python3 references/visuals/fetch_assets.py
python3 scripts/build-firmware.py
python3 scripts/build-firmware.py --variant arbitrated-af
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
./scripts/build-macos-app.sh
open "dist/Open LM-EA9.app"
```

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
