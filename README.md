# Open-LM-EA9

Research and development toward comprehensive, modular Techart LM-EA9 firmware,
a documented host communication protocol, and a polished, easy-to-use macOS app.
The initial target is a Sony A7C II and manually adapted Contax C/Y lenses.

The **macOS prototype uses native SwiftUI/AppKit and Swift IOHID**, following the
system audit. The production firmware stack is still being qualified; Rust is
a candidate, not a requirement.

The prototype includes all eight requested lens profiles, local metadata editing,
versioned JSON import/export, verified USB backup, and a staged application
upload/read-back path for lens metadata. The current app (0.5.0, build 8) refreshes
connection and local verification history automatically. Device shows product
photos, connection, dated firmware and the last verified lens, with a dropdown
to choose and apply another profile. Lens Library remains a secondary gallery/editor.
The modular AF 2.2 candidate is installed and byte-verified after physical
USB-cap reconnect. AF 2.1 was previously byte-verified, with owner reports of
motor movement and proper shutdown. Camera behavior remains unverified for 2.2;
focus lock/sharpness await the owner's C/Y-to-M converter.
The Biotar is 58mm f/2, as confirmed by the owner. Build and open:

```sh
python3 references/visuals/fetch_assets.py
python3 scripts/build-firmware.py
python3 scripts/build-firmware.py --variant reconciled-af
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
./scripts/build-macos-app.sh
open "dist/Open LM-EA9.app"
```

- [Current Device dropdown, automatic refresh and lens-change guide](docs/macos-device-workflow.md)
- [AF 2.2 upload and reconnect verification record](docs/evidence/af-22-upload-2026-10-11.md)
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
A7C II; focus qualification remains pending the C/Y-to-M converter. The current
2.2.0 candidate makes the reference/timing/completion policies explicit, passes
host checks and is packaged separately. It is now installed and byte-verified as
2.2.0 after owner-confirmed physical reconnect, with protected flash and factory
data checks passed. See the [current installation record](docs/evidence/af-22-upload-2026-10-11.md).
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
