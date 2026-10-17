# Firmware development

The latest candidate is [upstream AF 3.7 tracing](candidates/3.7.0/README.md), prepared
offline for the original Contax Zeiss 50mm f/1.4. It retains the upstream C
controller, guards, optical maps, aperture policy and wire layout, with targeted
motion/capture/shutdown diagnostics and a lossless packet initializer. It has
completed its separate upload and strict byte verification after physical
reconnect, including an independent full-image/protected-data audit; firmware
identity changes to 3.7. Its first camera cycle/log retrieval remain pending.
It does not establish a shutter-freeze fix. See the
[live installation record](../docs/evidence/upstream-37-upload-2026-10-17.md). See [3.7 evidence](../docs/evidence/upstream-37-tracing-2026-10-15.md) and the
[build/test workbench](upstream-hardening/next37/README.md) for exact prerequisites,
pins and conditional limits. App 0.20.0/build 25 provides a separately named 3.7
action while retaining the 3.6 camera-failure hold and older command meanings.
Preserve the original 3.6 image for research; do not repeat its failed camera test.

**Hardware gate:** [3.2 strict verification passed](../docs/evidence/upstream-32-upload-2026-10-15.md)
after owner-confirmed physical reconnect. The separately authorized
[3.6 upload and strict verification passed](../docs/evidence/upstream-36-upload-2026-10-15.md)
after its own physical reconnect. The later camera cycle failed, and a read-only
backup/log review was completed. The
[coordinated camera and log procedure](../docs/upstream-handoff-test.md)
is held for this image.
No offline test establishes capture, exposure, optical AF or factory parity.

Upstream 3.1 failed the A7C II check with aperture `--` and blocked shutter;
AF 3.0 failed capture/shutdown. Further trials of those images are held. The
sections below retain their historical implementation and build boundaries.


The [committed original stock 1.8.0 recovery bundle](recovery/stock-1.8.0/README.md)
includes the vendor application and an encrypted exact same-unit backup. Its
offline unpack/verification tool sends no USB reports; the key stays outside Git.

## Earlier custom firmware and metadata qualification

The first installable candidate was a **metadata qualification build with motor
motion disabled**. It uses C for the inspected SAMD21 register and E-mount paths;
it is not the production autofocus firmware or a decision against a later Rust
implementation. The macOS app and USB loader transport use native Swift.

The previous **AF 2.2 candidate** reconciles REA findings with the upstream
controller for Contax Zeiss 50mm f/1.4. The frozen **AF 2.3 candidate** adds received-
frame admission, coherent ISR snapshots, faulted Stop handling, operation
ownership, frame-paced telemetry and bounded initialization. It was installed and
USB-byte-verified after physical reconnect. The owner reports eventual loaded
50mm focus with substantial hunting; sharpness and camera qualification remain
unverified. The earlier stock 1.8.0 comparison matched its full application slot
to the original backup; the owner reported much less hunting. Camera use before
strict verification changed its saved-settings record. That historical failure
was subsequently closed by an explicit reviewed-motion resolution without
relabeling the strict failure. See the
[2.3 hardware record](../docs/evidence/af-23-upload-2026-10-11.md) and
[current stock comparison record](../docs/evidence/stock-18-comparison-2026-10-11.md).
The requested unknown-aperture behavior and current fixed-range declaration are
assessed in [manual aperture policy](../docs/manual-aperture-policy.md).
Historical custom 3.0 build and checks (these do not build upstream 3.6):

```sh
python3 scripts/build-firmware.py --variant arbitrated-af
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
```

The custom `ea9` source builds **AF 3.0** under `ea9/build/arbitrated`, with camera BCD
0x30 and loader 3.0.0. `em_arbitration` separates capture/RX/TX/session/shutdown
ownership; `af_readiness` admits bounded nonblocking homing. Factory-derived
capture opener echo and shutdown ordering are tested against original instructions.
The preceding controller/completion/aperture/observer policies are retained.
The candidate has 392 bytes flash margin, 2,380 bytes static RAM and 8,192 bytes
reserved stack. It was prepared offline; the separately authorized October 14
upload and strict physical-reconnect readback passed, with separate offline
audits. Camera acceptance subsequently failed: half-press focus, full-press
freeze, no saved photo and battery-required recovery. Further AF 3.0 trials are
held; see [the failure investigation](../docs/evidence/af-30-camera-failure-2026-10-14.md). See [the installation record](../docs/evidence/af-30-upload-2026-10-14.md).
AF 2.9 remains held after capture freeze and battery-required recovery.
See [the 3.0 candidate](candidates/3.0.0/README.md) and
[implementation, evidence and limits](../docs/evidence/af-30-candidate-2026-10-13.md).
Factory phase scheduling, saved-origin policy, physical timing and camera
qualification remain incomplete.

The following 2.4 observations are historical. It uses a modular factory-derived controller, tested directly
against the original instructions. Its authorized upload and strict byte verification passed after physical
reconnect, including an independent audit. **Its owner focus attempt failed**:
motor response without acquisition/photo release, a dark view and no shown
f-number in P/A. Actual focus mode/exposure remain unknown. Further 2.4 camera
testing is suspended. Stock 1.8 recovery passed strict byte verification after
physical reconnect and an independent audit. A stock display/lifecycle and
matched AF-S baseline remain pending. See [the failure and controller counterexamples](../docs/evidence/af-24-camera-failure-2026-10-11.md),
[completed recovery record](../docs/evidence/stock-18-af24-recovery-2026-10-11.md)
and [historical USB record](../docs/evidence/af-24-upload-2026-10-11.md). See the [algorithm and explicit differences](../docs/reverse-engineering/factory-af-baseline.md)
and [validation record](../docs/evidence/factory-af-baseline-2026-10-11.md).
Templates/pins for 2.0–2.9 remain frozen; their build-script variants verify
committed size/digest instead of compiling changed source under old versions.
Pinned custom versions remain admitted for backed-up upload, strict reconnect
verification and stock restoration. AF 2.2–2.9 and 3.0 profiles are at `0x9f00`,
with application writes stopping at `0xa000`. Python preparation defaults to
3.0; use `--variant serviced-af` for the frozen 2.9 template, or another explicit
historical variant. Current native `prepare-af` selects 3.0.
See the [audit](../docs/audits/firmware-correctness-2026-10-11.md) and
[offline build/test record](../docs/evidence/software-polish-2026-10-11.md).

The 50mm 2.2 image was installed and **USB byte-verified after physical reconnect**.
See the [installation record](../docs/evidence/af-22-upload-2026-10-11.md).
The owner reported motor movement and proper A7C II shutdown with the earlier
byte-verified 2.1 image. For 2.2 the owner also reported normal startup, quiet idle and normal motor
shutdown. Those historical tests preceded arrival of the C/Y-to-M converter;
the later 2.3 loaded-lens report does not verify optical sharpness or AF-S settings.
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
pinned released templates and separate fixed upstream candidates. The earlier
custom templates personalize only a reserved profile row; a custom template with
its zeroed row is intentionally invalid. Upstream 3.1–3.7 images have no runtime
profile row and reject edited profiles.

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
