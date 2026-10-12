# Factory-derived autofocus baseline: AF 2.4

October 11, 2026. The owner reports substantially less hunting with stock 1.8
than custom AF 2.3 on the A7C II, with the Contax Zeiss 50mm f/1.4 and C/Y-to-M
converter. Camera focus mode, Pre-AF, scene, exposure and image sharpness were
not recorded in that comparison. This is useful qualitative evidence, not a
matched measurement. AF 2.4 implements the recovered factory motion law to
make the next comparison meaningful. Upload and strict USB verification later
passed, but **the owner's focus attempt failed** with a dark view and no shown
f-number in P/A. Further 2.4 tests are suspended. The
[failure investigation](../evidence/af-24-camera-failure-2026-10-11.md) records
reproducible wrapper counterexamples and the limits of the hardware diagnosis;
[stock recovery](../evidence/stock-18-af24-recovery-2026-10-11.md) passed normal
strict verification after reconnect and an independent audit.

Current source wrappers have subsequently been refined for [AF 2.5](../evidence/af-25-candidate-2026-10-11.md).
The 2.4 wrapper policies below are historical; its binary and diagnostic inputs
remain frozen. The pure factory math is unchanged.

## Recovered algorithm and provenance

The baseline comes from the retained original
[1.8.0 application](../../firmware/recovery/stock-1.8.0/README.md), SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
REA supplied a navigation/decompilation aid; original instruction semantics
and finite emulation comparisons establish the behavior below. The existing
[38-routine host reconstruction](../../research/stock-1.8/README.md) covers
application orchestration as well as the controller. Its
[coverage ledger](whole-firmware-reconstruction.md) states the remaining limits.

The new MIT production module is independently written from those semantics.
It does not link the research model, patch the factory application, or import
factory code/data into the new controller. The existing firmware fork retains
its upstream and Microchip notices. This does not assign a new license to the
proprietary recovery application or change the research directory's licensing.

| Factory address | Behavior now represented in `factory_af.c` |
| --- | --- |
| `0x8dd4` | Convert the protocol target with signed 16-bit narrowing; latch direction; arm PID/timeout; clear completion and timeout count. Retain PID history, accumulator, previous sample and timer divider. |
| `0x8d20` | Direction-dependent target-speed steps: 250, 100, 50, then error/2 counts per control update at signed error thresholds 600, 300 and 100; negative-direction branches mirror the thresholds. |
| `0x8bfc` | Incremental PID: `A += 500*(e-old) + 150*e + 300*(e-2*old+older)`, with modulo-32-bit arithmetic. Divide signed A by 200 with truncation toward zero; floor nonzero output to ±200 and clamp to ±1280. The accumulator itself is not clamped. |
| `0x8fc8` | Measure signed 16-bit position difference since the previous control update. PID error is target speed minus that difference. Update sample history even when PID is disabled; drive both final bridge channels with the resulting signed duty. |
| `0x8d94` | Complete when the relative position crosses the latched target in the latched direction, or when an existing completion flag is set. This does not prove optical focus. |
| `0x8e28` | Disable PID and timeout, set completion, retain PID/sample/divider history. Original register stores are modeled separately from physical coast/brake behavior. |
| `0x8a2c` | On old timeout count 300, stop: the 301st armed callback. Control runs when the old divider is 10, every 11 callbacks, including sample-history updates when disabled. |

The recovered timer configuration is TCC1, nominal 48 MHz, DIV8, PER7500.
Its overflow is **60,008 CPU cycles = 1.2501667 ms**, so the nominal controller
period is **660,088 cycles = 13.751833 ms**. Timeout is approximately
375.05–376.30 ms depending on callback phase. These are derived from configured
registers; their physical periods on this unit have not been measured. The
upstream 5 ms feedforward/boost controller is excluded from the 2.4 binary.

## Module boundaries

- [`factory_af.[ch]`](../../firmware/ea9/src/factory_af.c): pure target, speed,
  PID, completion, Stop and callback semantics. No register or device access.
- [`factory_servo.[ch]`](../../firmware/ea9/src/factory_servo.c): the hardware
  motion owner. It samples the encoder, schedules callbacks, accepts retargets,
  checks cancellation and limits, and applies motor outputs.
- [`delay.c`](../../firmware/ea9/src/delay.c): a short IRQ-preserving SysTick
  snapshot supplies nominal 48 MHz cycle coordinates, including pending rollover.
- [`af_control`](../../firmware/ea9/src/af_control.c),
  [`af_reference`](../../firmware/ea9/src/af_reference.c) and
  [`af_completion`](../../firmware/ea9/src/af_completion.c): shared command
  admission, bounded reference establishment, sticky motion faults and event
  eligibility. The protocol remains in `emount`; the lens declaration remains
  in `lens_profile`.

The motion owner accepts an absolute target. It avoids shifting that target by
encoder movement between successive reads. Retargets preserve factory PID
history and divider phase; Stop and replacement operations are checked before
target crossing. A final sensor/report failure or Stop suppresses success.
The configured count travel remains 0–5952, with four-count protocol resolution.

## Explicit differences from stock

| Boundary | Candidate policy and remaining evidence |
| --- | --- |
| Scheduling | Foreground sampling uses the exact configured cycle ratio, rather than the original TCC1 ISR. Up to ten elapsed callbacks may be coalesced with one latest sample and at most one PID update. A longer active gap latches a timebase fault; there is no burst of catch-up PID updates. Polling latency and loaded bus behavior need hardware measurement. Disabled long gaps rebase sample history without energizing the motor. |
| Origin/homing | Retain bounded physical homing and the existing unwrapped tracker. Mechanical zero is bridged to 192 reference counts, giving protocol 4144; target and position use the same offset. Stock's saved raw reference and asymmetric 16383 seam arithmetic remain reconstructed in the research model, but are not loaded into this unrelated tracker. Ordinary factory homing has no recovered enabling writer. Physical offset, stop direction and homing remain unqualified. |
| Completion | The pure module matches target crossing. The wrapper brakes at crossing and disables PID immediately; stock leaves PID armed until its later protocol Stop stage. No legacy velocity/dwell arrival test is mixed into the factory baseline. Braking, overshoot and subsequent camera commands need comparison. |
| Timeout/faults | Preserve the factory callback deadline, but report timeout as a distinct sticky motion fault instead of stock's success-like completion flag. Retain 300 ms no-progress detection, travel/runaway/wrong-direction limits, finite polling, sensor/PWM waits, a five-second total retarget budget and at most 16 in-place retargets. |
| Scan/Drive | Existing guarded protocol sequencing remains. The factory speed staircase is used; the upstream invented speed-code mapping is excluded. Complete factory scan/drive sequencing and all wire fields have not been replaced or camera-qualified. |
| Optics/status | Existing profile metadata, distance approximation, prediction and frame-paced reporting remain. The donor optical rows are not a calibration for the actual Contax lens. Camera-owned focus estimation can hunt because of response timing, inaccurate optical declarations or mechanics; matching PID alone does not establish factory performance. |
| Aperture | Report one fixed numeric aperture range and current value, and ignore conflicting body iris requests. The actual passive iris is always unknown to USB. This removes the stock aperture-as-configuration menu; it does not physically lock the ring or establish camera F-- support. |

## Validation and next comparison

[`test-factory-af-oracle.py`](../../scripts/test-factory-af-oracle.py) compares
the **production** pure module directly against the pinned original instructions.
It compares 13 relevant controller fields, defined return values and final motor
driver calls across 7,323 cases, with threshold/overflow/random states and
composed retarget/Stop/timeout sequences. An altered integral gain is rejected.
The emulator's Cortex-M0 selection is a behavioral aid, not an architecture
legality proof; final motor drivers are stubbed and Stop stores use dummy RAM.

The wrapper is checked separately with scripted feedback and clocks under
address/undefined-behavior sanitizers. The production main's lifecycle and
command regressions also run with this backend. These checks validate software
behavior under the injected conditions, not physical motor stability or optics.
See the [build/validation record](../evidence/factory-af-baseline-2026-10-11.md).

The later [mechanical counterexample probe](../../scripts/test-factory-camera-limits.py)
reproduces permanent session faults for a four-count correction and full travel
with the unchanged 2.4 wrapper and inherited simulator. Neither test has an I/O
fault or simulated stop contact. Factory timeout/next-command completion differs
from this wrapper. Passing the pure oracle did not establish usable control
across these mechanics. The owner's camera failure is not traced to either path.

Further 2.4 trials are suspended. The latest stock recovery has passed normal
strict verification after physical reconnect. Start a stock display/lifecycle check to distinguish
the dark view and missing f-number from autofocus behavior. A new version must
reconcile small corrections, healthy-progress deadline termination, completion
and subsequent-command eligibility while retaining inhibition for unsafe sensor,
PWM, timebase and runaway conditions. Lens-init/status and AF sequencing also
require investigation. Leave the deployed 2.4 image and pins unchanged.

Stock comparison also failed exposure at owner-reported physical f/1.4 / body
f/2. Accept that failure without requiring an unavailable original photo.
Follow the [next aperture acceptance criteria](../manual-aperture-policy.md#next-firmware-acceptance)
for coherent initialization/request/status reporting and saved exposure.
Exposure investigation and the known AF wrapper counterexamples can proceed
independently; neither justifies silently changing the frozen 2.4 image.

For a later candidate, record matched stock/custom trials: still-photo P,
explicitly AF-S, Pre-AF Off, same static textured target, lighting, distance,
focus area, aperture ring and lens starting position. Record acquisition time,
reversals, lock failures, photograph sharpness, startup and shutdown for each.
Manual f/4 trials follow only after stable f/1.4 operation; inspect display and
EXIF separately. Use the [camera runbook](../af-s-test.md) for stop conditions.
No improvement, factory parity, AF-C/video capability or usable unknown-aperture
camera encoding is established.
