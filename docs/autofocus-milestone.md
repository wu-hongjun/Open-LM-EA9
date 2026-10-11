# Autofocus implementation milestone

Current source/app follow-up: [AF 2.3 hardening](evidence/software-polish-2026-10-11.md)
adds frame validation, coherent handoff, Stop ownership, telemetry cadence and
bounded startup waits. It was installed and byte-verified after physical reconnect;
the [2.3 hardware record](evidence/af-23-upload-2026-10-11.md) and
[owner loaded-lens observation](evidence/af-23-camera-lifecycle-2026-10-11.md)
record eventual focus with substantial hunting; settings and sharpness remain
unverified. Original stock 1.8.0 is restored and the owner reports less hunting.
Its full application slot matches the original backup; the strict native
transaction remains flagged for changed saved-motion bytes following camera
use before readback. See the [stock comparison](evidence/stock-18-comparison-2026-10-11.md)
and [manual aperture policy](manual-aperture-policy.md).
The installation action now selects 2.3 explicitly; main profile changes preserve
the verified installed variant.

Previous follow-up: [AF 2.2 reconciliation](af-reconciliation.md) separates position
origin, reference state, timing and completion policies using the REA findings.
It was host-tested, installed and byte-verified after physical USB-cap reconnect.
See the [2.2 installation record](evidence/af-22-upload-2026-10-11.md)
and [software evidence](evidence/af-reconciliation-2026-10-10.md). The owner
confirmed motor movement and proper shutdown with 2.1; these observations do not
qualify 2.2. Those tests preceded arrival of the C/Y-to-M converter.

The metadata path has now passed an A7C II photograph check. Autofocus development
can proceed using the pinned upstream implementation and the independently
reconstructed factory controller. No complete factory reconstruction is required
before building the upstream candidate.

The camera's image sensor decides where focus should go. The adapter accepts
those commands, moves its helicoid using encoder feedback, and reports position,
motion and completion. Improving this system means coordinating the actuator,
protocol timing and lens optical declarations; changing PID gains alone does
not establish accurate autofocus across the image.

## First implementation

The first 2.1 release built a separate C candidate from upstream `main.c`,
`servo.c`, encoder, distance mapping and prediction modules. It shares the
CRC-protected lens profile at `0xa000` with the verified metadata build. The
app now packages frozen metadata 2.0, AF 2.1 and AF 2.2 plus new AF 2.3 with separate digest pins. The default remains
metadata-only; AF installation is explicit. Neither build writes hardware or user
update state. See [the current AF-S runbook](af-s-test.md).

| Module | Responsibility |
| --- | --- |
| `emount.c` | Frame admission, handshake, commands, status and completion events |
| `af_control.c` | Bounded command translation, exclusive motion ownership, session fault/shutdown state |
| `servo.c` | Encoder-feedback control, arrival, retarget, stall, runaway and timeouts |
| `io_guard.c` | Sticky faults, deadlines and finite poll ceilings, immediate GPIO release |
| `abs_encoder.c`, `motor.c` | SPI sensor and PWM/GPIO hardware access, IRQ-safe output attachment |
| `focus_map.c`, `focus_dist.c`, `focus_pred.c` | Position/distance conversion and camera-visible prediction |
| `lens_profile.c` | Validated lens metadata; no motor calibration fields |
| `main.c` | Startup, homing, focus execution, shutdown and module coordination |

The first build retains upstream tuning. Its control step is polled after at
least 5 ms, using actual elapsed time. The configured move uses a 30 ms stopping
profile, 25,000 counts/s cruise ceiling, 200..1280 drive magnitude, 300 ms stall
deadline, 3 s per-leg and 5 s total deadline. These are inherited parameters
from the upstream author's adapter, not measurements on this unit.

Changes made while enabling this path:

- Relative defocus multiplication widens to signed 64 bits before clamping;
  extreme wire operands cannot overflow into motion in the wrong direction.
- The absolute no-target sentinel is rejected in the command module as well as
  the protocol parser.
- Mechanical servo failures latch until a new boot. Subsequent focus or park
  commands cannot restart drive, and failed legs do not publish Move success.
  An ordinary camera Stop remains recoverable.
- Motion ownership prevents nested servo execution. When shutdown arrives in
  the protocol pump during homing or focus, the current owner is stopped and
  drive released. This case skips parking; shutdown from idle retains the
  bounded park-before-acknowledgement path. Powerdown runs once per boot.
- Diagnostic flash writers remain excluded and checked at link time. The AF
  target must contain `servo_move_rel` and `motor_drive`; the metadata target
  must contain neither.

The first AF release encodes camera version `0x21` (2.1) and loader version 2.1.0.
The 50mm 2.1.0 image was installed and byte-verified after physical USB-cap
reconnect. The owner subsequently confirmed motor movement and proper shutdown;
startup details and AF-S focus acquisition remain unverified.
See [the upload record](evidence/af-50-upload-2026-10-10.md). An all-zero template profile
is invalid and cannot start the camera/motor session.

## Factory algorithm research

The user-authorized Astra REA lane has reconstructed the official 1.8.0 AF
arithmetic and state transitions. See the
[factory dossier](reverse-engineering/stock-phase2.md) for addresses, confidence,
annotated private pseudocode and reproducible original-instruction checks.

Factory control computes a direction-latched desired speed from remaining
distance: 250, 100 or 50 counts per update above thresholds 600, 300 and 100;
otherwise signed error/2. It measures velocity by successive encoder positions
and applies an incremental PID:

```text
acc += 500*(e - old) + 150*e + 300*(e - 2*old + old2)
duty = signed_truncate(acc / 200)
nonzero duty gets magnitude floor 200, then clamp to ±1280
```

Original 32-bit wrap and signed narrowing are part of the recovered behavior.
History and accumulator survive stops and retargets. The recovered timer
configuration implies a nominal PID interval of 13.7518 ms and a timeout of
approximately 375–376 ms; these durations are derived from configuration at a
nominal 48 MHz clock, not measured on hardware. Stock encoder/reference
arithmetic, target origin and persistence differ from the upstream replacement.
No ordinary enabling writer for the stock homing gate has been established.

The upstream configuration originally named `STOCK` (renamed `UPSTREAM_PROFILE`
in 2.2) implements a different controller:
continuous stopping profile, feedforward and velocity correction. We will
compare controller behavior using the same motion/command fixtures rather than
silently replacing one with the other. A stock metadata patch remains a separate
[feasibility study](reverse-engineering/stock-metadata-patch-feasibility.md).

## Reproduce the offline candidate

From the project root, after the native prototype CLI is built:

```sh
python3 scripts/build-firmware.py --variant hardened-af
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
```

This builds the current 2.3 zero-profile template and checks seven personalized prime/macro
fixtures. The 50mm fixture is
`artifacts/firmware-milestone/hosttests/contax-zeiss-50-f1-4-af.bin` with an adjacent
manifest. To prepare a new local candidate using a Mac-generated metadata image:

```sh
dist/ea9ctl --state-directory artifacts/firmware-milestone/af-local-state \
  prepare contax-zeiss-50-f1-4 artifacts/firmware-milestone/af-50-profile.bin
python3 scripts/prepare-af.py artifacts/firmware-milestone/af-50-profile.bin \
  artifacts/firmware-milestone/af-50-candidate.bin
```

Preparation refuses existing output paths and sends no USB reports. The C
profile test, included in `--af`, remains the full profile decoder/packet check.
The current app/CLI admits this exact AF template/version to its pinned upload,
backup, inspection, reconnect verification and restoration workflow. The app
keeps AF installation in secondary USB tools. `prepare-af` builds offline and
`apply-af` selects the AF variant through the existing qualified transport; no
arbitrary-image flashing path was added.

## Remaining work before camera qualification

Bounded SPI/ADC, PWM and energized-path UART waits, delay fallback ceilings,
IRQ-safe motor inhibition, homing/shutdown integration tests and host image
admission are implemented. Homing must observe stationary drive and settle stages;
timeouts cannot establish zero. A faulted read cannot update the encoder reference
or unwrapped accumulator, or produce a successful final completion.

The register waits use a 2 ms deadline and 100,000-poll ceiling. Motion loops and
ADC bursts also use a 1,000,000-iteration ceiling; these are finite fallback
budgets, not measured elapsed-time guarantees with a failed clock. GPIO-only
emergency release never waits for PWM. Sticky I/O faults and shutdown inhibit
later attachment; an IRQ-preserving critical section prevents a UART interrupt
from releasing pins just before foreground code reattaches them. All fault masks
clear only at reset. Startup clock/UART/EIC initialization still has motor-off
liveness limits, and there is no independently qualified watchdog.

The exact 2.0.0 metadata template remains unchanged. Same-unit stock source,
shared host lock, durable recovery journal, no retry/post-upload reads and physical
reconnect requirements also remain in force. The original 1.8.0 source has been
revalidated offline, and the AF installation has passed reconnect/readback
verification. Mechanical reference and the AF-to-stock hardware round trip
remain pending. See [the completed upload evidence](evidence/af-50-upload-2026-10-10.md)
and [the historical readiness evidence](evidence/autofocus-ready-2026-10-10.md).

The first physical qualification should use the already selected Contax Zeiss
50mm f/1.4: P/A exposure mode, lens ring at infinity, still-image AF-S and a
central focus area. Establish startup/reference and immediate Stop/shutdown
behavior before repeated near/far acquisitions. Record saved metadata, actual
sharpness, latency, hunting and focus repeatability. Broader field accuracy,
heavier lenses, AF-C and video follow separately; lens optical rows and the
assumed 4.5 mm extension need validation. The zoom is excluded from these fixtures
until its actual aperture and focal setting are defined.

See [the build/test evidence](evidence/autofocus-candidate-2026-10-10.md).
