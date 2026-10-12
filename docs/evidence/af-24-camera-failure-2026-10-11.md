# AF 2.4 loaded-lens failure and stock recovery

October 11, 2026. The owner reports that a half-press moves the motor but never
obtains focus or releases a photo. They also report a very dark view, no shown
f-number in P/A and no motor movement on shutdown. Replies and unverified
conditions are preserved in the [camera observation record](af-24-camera-comparison-2026-10-11.md).
AF 2.4 is **failed under this reported camera test**, despite successful exact
USB byte verification. Repeated focus attempts are suspended.

## What can be concluded

- The owner observed motor response to half-press and failure to acquire focus.
  Actual focus mode is unknown, so this is not labeled a confirmed AF-S trial.
- No movement without shutter input is not a verified ten-second idle or a
  valid homing/reference measurement. No movement on shutdown does not prove
  normal display shutdown or that the motor stopped immediately after release.
- The shutter refusal is consistent with focus-priority behavior: Sony's
  [AF-S priority guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405H_AF-S_priority_setup.html)
  says its AF setting waits for focus before releasing. The owner's actual
  priority/mode was not established, so that mechanism is an inference.
  Changing release priority would not repair failed focusing and was not advised.
- A fixed numeric lens declaration does not operate the passive iris. The dark
  view may involve physical iris, exposure/preview or failed lens communication;
  no cause is proven without the actual ring/display/settings observations.
  “No shown F stop” is not assumed to mean the exact F-- symbol or to establish
  a usable unknown-aperture encoding. No image was available for EXIF inspection.

## Concrete wrapper counterexamples

The new [offline reproducer](../../scripts/test-factory-camera-limits.py) drives
the unchanged deployed `factory_servo.c` with the existing upstream mechanical
simulator, then applies the production session-fault and completion policies.
Eight targets run under address/undefined-behavior sanitizers. Assertions confirm
two failures **without an I/O fault or simulated end-stop contact**:

| Simulated target | Result | Subsequent commands |
| --- | --- | --- |
| Four counts, one protocol unit | No movement; duty stays at 200, below the model's 210 breakaway threshold; stalls at 301 simulated ms | Session fault latches; no Move completion event; next motion rejected |
| Full 5,952-count travel | Ends at 5,762 counts on the factory-sized deadline, 378 simulated ms | Session timeout latches; no Move completion event; next motion rejected |

Intermediate targets in this simulator reach crossing and post a Move event.
The recovered factory callback stops at its deadline and sets completion; a
new target clears completion and re-arms control instead of creating a permanent
wrapper fault. These semantics were separately compared against original
instructions. The production wrapper deliberately changed that behavior; this
is now a concrete readiness gap, not merely unqualified timing.

The [counterexample report](af-24-camera-counterexamples-2026-10-11.json) includes
all eight results and source hashes. The model's mechanical coefficients come
from upstream's adapter, not the owner's lens/unit. Its clock advances with
simulated `millis()` calls; its durations are not measured hardware times. It
does not model camera wire traffic, frame/ADC pump delay, optics or exposure.
These results **do not prove** that the owner's failure hit either fault path.
They explain why matching the pure PID routine was insufficient for readiness.

Reproduce without USB:

```sh
python3 scripts/test-factory-camera-limits.py --output /new/counterexample-directory
```

The script refuses an existing output directory. A passing assertion means the
known bad 2.4 behavior was reproduced, not that autofocus was repaired. Production
source, template pins and the committed 2.4 binary are unchanged in this diagnosis.

## Next implementation requirements

Separate permanent unsafe feedback/peripheral faults from bounded motion
termination. Retain inhibition for sensor/PWM/timebase failures, wrong-direction
and runaway feedback. Reconcile healthy-progress timeouts and small corrections
with the factory's actuator-completion/next-command behavior, without falsely
claiming optical focus or adding uncontrolled retries. Check completion staging,
retained history, idle sampling and coordinate resolution together with protocol
state rather than changing gains or raising duty based on this single report.

The missing camera aperture additionally requires comparison of lens-init,
metadata/status and AF sequencing against stock. USB image equality does not
prove camera acceptance of those frames. There is no recovered live trace from
this attempt: diagnostic flash logging is disabled, and moving to the USB cap
power-cycles away runtime fault RAM. A cap read cannot reconstruct that fault.
The next candidate needs an explicit evidence/diagnostic plan; no replacement
AF firmware is built or uploaded by this diagnosis.

## Recovery and comparison

The owner confirmed return to the Mac; descriptor-only inventory detected a
new qualified, unblocked USB-cap connection. The official updater and app were
absent. The saved original same-unit stock recovery source was verified offline,
and current AF 2.4 journal/profile/qualification evidence was retained privately.
The normal native `restore-stock` path completed at 23:55:53 UTC (19:55:53 local),
exit 0. A fresh two-pass backup exactly matches the previously verified 2.4
flash; the camera session did not change persistent flash. It does not recover
the lost runtime fault state. The durable same-unit journal binds the complete
original 110,592-byte stock slot and all 58 known stock metadata bytes. Native
success establishes one acknowledged START and 1,728 acknowledged pages.
No bootloader/record write or verification exception was used. See the
[redacted recovery evidence](stock-18-af24-recovery-2026-10-11.json).

Physical reconnect and strict stock verification remain pending. Keep the
adapter off the camera until verification passes. Only then compare stock on the same
50mm lens, with actual AF-S/Pre-AF, ring and exposure settings recorded. If the
dark view/missing f-number persists on stock, record that separately before AF
testing. Do not infer that motor PID explains exposure or lens identification.
Private backups/serials/calibration contents and recovery keys remain excluded
from public Git; the frozen 2.4 candidate remains available for reproducibility.
