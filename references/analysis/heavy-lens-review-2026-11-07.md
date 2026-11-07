# Heavy-lens review after the 4.6 trial

## Evidence boundary

The owner initially reported more AF hunting, then said 4.6 worked better and
disclosed trying a heavier Contax Zeiss Distagon 35mm f/1.4. The exact settings,
orientation, time of each lens change and lens used at the improvement are unknown.
This is neither a controlled 4.5/4.6 Biotar comparison nor proof that weight caused
the hunting. It does identify a useful future optimization target.

The current image is still pinned Biotar 58mm/f/2 with a virtual f/1.2–f/22 range.
`firmware/core/emount.c:put_focal` publishes the compiled focal length in the
0x05/0x28/0x35 fields and 0x08 BCD fields. In the LM-EA9 `main.c`, subject-distance
reporting and `EM_OP_MOVE_DIST` conversion use `em_focal_mm10`; ordinary position,
relative, Scan and Drive operands do not all use that distance conversion. A
35mm lens with the 58mm build is a separate confound from mechanical load.

## Primary references

- [ZEISS C/Y Distagon 1.4/35 data sheet](https://www.zeiss.com/content/dam/consumer-products/downloads/historical-products/photography/contax-yashica/en/datasheet-zeiss-distagon-1435-en.pdf):
  lists approximately 600g for that model, before the extra mount converter.
  The owner's particular assembly has not been weighed. The sheet also describes
  a floating group, so translating the whole lens does not reproduce internal
  close-focus group movement. We have not calibrated those optical effects.
- [Techart LM-EA9 limitations](https://techartpro.com/?page_id=5430): explains
  that the adapter focuses by moving the whole lens, unlike a native lens moving
  a smaller internal group. It does not establish the load on this particular unit.
- [Official LM-EA9 manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf):
  describes normal and slower focusing modes for fast lenses and advises supporting
  camera and lens together. The stock f/51/f/57 control mechanism is not implemented
  by this project's camera-aperture reporting system; do not use those selections
  as custom-firmware commands.

## Current implementation, checked against initializers

`firmware/targets/lm-ea9/src/main.c` owns fixed `STOCK` and `PARK` servo
configurations and makes live copies for Scan/Drive. The focus initializer has:

| Parameter | Current value |
| --- | --- |
| `stop_ms` | 30 ms |
| `v_cruise` | 25000 encoder counts/s |
| `tau_ms` | 26 ms feedforward model |
| `ff_div`, `ff_offset`, `kp_div` | 40, 134, 50 |
| `boost_up`, `boost_down`, `boost_max` | 12, 8, 800 |
| `duty_floor`, `duty_max` | 200, 1280 |
| `tolerance`, `settle_counts` | 12, 40 counts |
| `v_arrive`, `arrive_steps` | 500 counts/s, 2 control steps |
| `stall_ms`, `timeout_ms`, `total_ms` | 300, 3000, 5000 ms |
| `reverse_brake_ms`, `reverse_brake_above` | 100 ms, 5000 counts/s |

The loop in `servo.c` already measures velocity, applies feedforward/feedback and
boost while lagging, brakes before fast reversals, requires a low-speed arrival
and enforces stall, timeout, wrong-way, overshoot and travel guards. This is not
a calibrated lens-mass model. Historical comments describe other measurements
and experimental values; the actual initializers above govern this release.
Those upstream measurements were not made on the owner's Distagon/A7C II.

## Recommended next milestone, not implemented or flashed

1. Prepare a correctly labeled 35mm Distagon configuration with unchanged motor
   behavior, as a separate new version. First establish a matched-lens baseline;
   keep the published 58mm images and defaults byte-identical. A focal metadata
   correction does not fully calibrate defocus scaling, optical tables or the
   floating-group geometry.
2. Separate optical identity from mechanical motion presets. A target-specific
   motion-profile module can supply Move/Scan/Drive tuning, while hardware-wide
   force/travel limits and shutdown/homing policy remain independent. The first
   preset must reproduce the existing constants exactly. Do not expose arbitrary
   duty/gain sliders as an ordinary app lens-edit action.
3. Measure breakaway delay, speed tracking, peak overshoot, settling and reversals
   with the actual load and lens orientation. Idle USB backups cannot provide
   those measurements: this release has runtime diagnostics compiled out. Any
   telemetry candidate needs a separate reviewed design, with no added flash
   writes or blocking work in the timing-critical camera/servo path.
4. Evaluate a slower load-specific profile: bounded acceleration/velocity,
   earlier deceleration and measured settling. Keep Scan/Drive speed conventions
   coherent; slowing one phase independently can disrupt the body's focus search.
   Increasing boost, duty or arrival tolerance is not justified by the current
   observation. Preserve guards and truthful completion rather than masking stalls.
5. Use the existing `sim_motor.c` stiction, driven-response, coast, brake and
   feedback controls to reject candidates that worsen bounds/overshoot. Add controls
   that fail for premature arrival or unsafe reversal. Simulation can reject a
   bad controller; it cannot qualify a 600g lens. Hardware comparison should hold
   scene, light, exposure/AF mode, physical iris, support and orientation constant.

Lens mass, overhang and orientation are separate variables. Physical support
must allow the mount's focusing travel; a support that restrains translation
changes the mechanism being tested. Firmware tuning cannot establish a higher
mechanical load rating. No load-rating increase is proposed by this review.
