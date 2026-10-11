# Firmware prototype

The [committed original stock 1.8.0 recovery bundle](recovery/stock-1.8.0/README.md)
includes the vendor application and an encrypted exact same-unit backup. Its
offline unpack/verification tool sends no USB reports; the key stays outside Git.

The first installable candidate is a **metadata qualification build with motor
motion disabled**. It uses C for the inspected SAMD21 register and E-mount paths;
it is not the production autofocus firmware or a decision against a later Rust
implementation. The macOS app and USB loader transport use native Swift.

The installed **AF 2.2 candidate** reconciles REA findings with the upstream
controller for Contax Zeiss 50mm f/1.4. The new **AF 2.3 candidate** adds received-
frame admission, coherent ISR snapshots, faulted Stop handling, operation
ownership, frame-paced telemetry and bounded initialization. It remains offline
and requires USB verification and camera qualification before use:

```sh
python3 scripts/build-firmware.py --variant hardened-af
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
```

Current source builds separately under `ea9/build/hardened`, as camera BCD 0x23
and loader 2.3.0. Templates/pins for 2.0, 2.1 and 2.2 remain frozen; the corresponding
build-script variants verify their committed size/digest rather than compiling
changed source under an older version. All four versions remain admitted for
backed-up upload, reconnect verification and stock restoration. The reserved
profile row for 2.2/2.3 is `0x9f00`; application writes stop at `0xa000`.
See the [audit](../docs/audits/firmware-correctness-2026-10-11.md) and
[offline build/test record](../docs/evidence/software-polish-2026-10-11.md).

The 50mm 2.2 image is installed and **USB byte-verified after physical reconnect**.
See the [installation record](../docs/evidence/af-22-upload-2026-10-11.md).
The owner reported motor movement and proper A7C II shutdown with the earlier
byte-verified 2.1 image. For 2.2 the owner also reported normal startup, quiet idle and normal motor
shutdown. Loaded AF-S focus lock/sharpness still await the C/Y-to-M converter.
These observations do not qualify homing, measured timing or all focus commands.
See the [reference/timing/completion design](../docs/af-reconciliation.md),
[session evidence](../docs/evidence/af-reconciliation-2026-10-10.md),
[AF-S runbook](../docs/af-s-test.md) and
[factory REA reconstruction](../docs/reverse-engineering/stock-phase2.md).

The fork is based on [weiziqian/E-mount-impl-on-Techart-EA9](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9)
at commit `d52ed06cc449918f938e0695fbf29a0c4141f2b2`. The source snapshot in
`references/upstream` remains immutable. MIT and Microchip Apache notices are
retained in `ea9`; new profile and metadata-entry code uses MIT. Device headers,
CMSIS and compiler notices remain in their downloaded dependency archives.

Build from the repository root on Apple Silicon macOS with Python 3.12+:

```sh
python3 scripts/build-firmware.py
./scripts/swift-local.sh test
python3 scripts/test-firmware.py
./scripts/build-macos-app.sh
```

Dependency versions, official source URLs and digests are pinned in
`dependencies.json`. The local cache is ignored. The packaged Mac app includes
the pinned released templates and the new candidate and a digest pin; it personalizes only the
reserved profile row. A template with its zeroed profile is intentionally invalid.

Changes from the reference:

- The frozen metadata release uses a dedicated `metadata_main.c` entry point; the motion implementation is not
  linked. The inherited motion files remain available for a subsequent audited
  autofocus milestone. No flash logging is linked.
- `lens_profile.c` validates the versioned CRC-protected profile and applies
  focal length, manually reported aperture and lens name through the existing
  frame setters. No measured geometry from another lens is reused.
- Legacy adapter ID 234 and camera-reported custom firmware 2.0 are used. USB
  metadata declares 2.0.0; CHECK still runs in the original bootloader.
- Linker bounds reserve one row at `0xa000`. Startup headers/vector field names
  are adapted to DFP 2.0.4 without changing the interrupt-vector ordering.
- The inherited optical-row test now invokes the row setter explicitly; the
  new profile test proves startup retains the stock optical rows.

Use the [USB milestone procedure](../docs/usb-metadata-milestone.md) and its
[evidence record](../docs/evidence/usb-metadata-milestone-2026-10-10.md).
An actual Sony A7C II test is required to qualify displayed metadata, EXIF,
startup/shutdown and timing. No autofocus claim follows from these host tests.
