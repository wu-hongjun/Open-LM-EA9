# AF4.0 guarded home reference qualification — offline audit

The proposed change repairs a demonstrated software readiness dead end: AF3.9 requires 40 ticks of driven stillness before the 300-tick active-drive budget expires. An anchor established at tick 280 can therefore never qualify, even when it remains stationary at cutoff. The pinned upstream `src/main.c` proceeds from bounded drive to bounded settle without that added failure branch. Removing the branch unconditionally would be too permissive; this overlay admits a narrower, experimental released-settle path.

This is **software reference qualification, not proof of a physical infinity endpoint**. Travel followed by mid-travel stiction can produce the same observations. An initially stationary jam also remains indistinguishable from the already-parked condition accepted by the existing early-success path. No claim is made that the observed camera run followed any synthetic trajectory below, that AF-S worked, that reported photos became files, or that AF4.0 is camera-qualified.

## Source and scope

Frozen AF3.9 image SHA256: `87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44`.

Published manifest SHA256: `9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a`.

`firmware/upstream-hardening/followup/49-home-qualification/apply.py` pins `motor_home` and `home_command` individually and pins the complete encoder/motor C files and headers. Other main-function overlays can compose without weakening these pins. `run.py` verifies all 49 frozen source hashes, image, manifest, and host shim before and after testing; optional `--candidate` additionally verifies every integrated AF4.0 manifest source and image hash before and after extraction. Published files are never modified.

The scope is the homing path, a detached PWM-clear helper, a final validated encoder-reference helper, and the AF4.0 failed-home-tail tag (`0x40`). No drive duty, 300-tick drive bound, 500-tick settle bound, 40-tick stillness threshold, six-count tolerance, shared million-iteration work bound, attempt policy, cancellation/session/shutdown gate, encoder overflow invariant, or stock recovery path is relaxed.

## Qualification policy

The existing early path still requires 40 driven-still ticks and then a bounded braked settle. On expiration without that qualification:

1. Snapshot elapsed drive time and immediately detach all motor pins using the existing GPIO emergency-release path. Clear all four PWM compares **while detached**, using the existing bounded synchronization waits. Never remux during this operation. Clearing prevents the servo's later initial attach from reapplying stale reverse homing duty.
2. Reject elapsed time other than exactly 300 ticks, a last iteration that does not corroborate an earlier stationary anchor, nonnegative/noise-only net displacement, or net displacement beyond advertised travel plus six counts. Wide differences prevent arithmetic overflow. This is a net-displacement guard, not proof of monotonic motion or calibrated physical travel.
3. Preserve the driven anchor. Require 40 further ticks with every observed released-settle sample within six counts of that fixed anchor, inside the existing 500-tick phase deadline and shared iteration budget. Any observed escape is terminal; the timer and anchor cannot restart to turn drifting into success. Release avoids mistaking brake-imposed stillness alone for evidence and follows the conditional factory release/settle shape; it differs deliberately from upstream's early-path brake.
4. Validate the extra final `after` sample as well. A new encoder helper reads the final coordinate, checks inhibition and tolerance, and resets the software accumulator using that same validated sample's already-updated raw reference. It does not take a second unvalidated raw reset sample. Existing final cancellation checks still guard readiness commit.

The repeated driven observation is corroboration only. It introduces no invented 20-tick calibration threshold, and does not claim equivalence to 40 ticks under active drive. The stricter fallback rejects continuous movement/noise at cutoff and late UART deadline crossings rather than allowing a later released stop to qualify them. The bounded waits are not hard-real-time guarantees that an already-blocking operation cannot delay physical cutoff; no such claim is made.

The failed-home tail keeps its eight-word shape. AF4.0 uses tag `0x40`; a released-settle failure can legitimately have settle phase with `driveQualified=false`. That flag continues to mean the original driven-stillness qualification, not entry into the new fallback. AF3.9 remains byte-for-byte unchanged with tag `0x39`.

## Regression evidence

Run from the repository root:

```sh
python3 firmware/upstream-hardening/followup/49-home-qualification/run.py --output artifacts/private/astra49-review
```

The harness compiles source-extracted production home, foreground, query worker, pump, tracker, UART send, and relevant motor functions with production protocol/owner/shutdown/trace/map units. MMIO, raw encoder samples, wire input, and time are synthetic boundaries. ASan and UBSan are enabled. The motor harness executes actual detach, compare writes, attach, drive, brake, and inhibit bodies; it checks stale compare removal. It does not emulate analogue motor dynamics, USB, or a camera.

The finite log-constrained case moves toward minus until tick 280 and then remains at software displacement -2902. It reproduces AF3.9 phase 17, anchor age 20, last iteration 299, cutoff 300, no readiness/reset; the proposed overlay cuts off at 300 and reaches software readiness at 340 with zeroed PWM compares. **The trajectory between samples is invented for regression.** The observed 7099 polls are not replayed or represented as measured physical timing; the finite model uses one tick per pump. Only the stated aggregate constraints are matched.

The current local run (`artifacts/private/astra49-final-candidate/result.json`) contains 66 successful baseline/proposed executions and five expected assertion failures that kill causal mutants: removed polarity evidence, removed fixed-anchor enforcement, unvalidated raw reset, stale PWM retained across released settle, and removal of the exact cutoff guard. Cases cover early/late arrival, tick wrap, moving cutoff, wrong polarity, excessive net travel, six/seven-count noise, post-release drift, final-reset drift, a one-sample final-after escape followed by return, query storm, ordinary/deadline-crossing UART, frozen clocks, shared work exhaustion, actual Stop record, session reset, shutdown during both drive and released settle, and corrupt tracker coordinates. Failure/cancellation does not grant an unsolicited second attempt. The stationary `stuck` case explicitly demonstrates the retained observability limitation; it is not falsely reported as a rejected jam.

Tests carry no raw camera frames, identifiers, or captured operands. Detailed generated outputs remain under private artifacts. This lane performed no device discovery/open, USB/HID operation, flash, motor drive, app/updater launch, or canonical Application Support access. Integrated flash size, manifest, release eligibility, and later camera qualification are separate root-owned decisions.

## Integrated candidate receipt

The same suite passed against root-built AF4.0 at `artifacts/private/reference40d`: image SHA256 `06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae`, manifest SHA256 `8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`. All candidate source pins were checked before and after extraction. Applicator SHA256 is `4df3db15d803c609fcf4d49e9fe705444a58e263712641fd47ad17d9c894cb5e`. The candidate remains unqualified for camera use; these are offline software regressions.

## Independent host integration review

Read-only review covered the AF4.0 enum/resource pin, CLI prepare/apply routing, fixed-profile builder, workflow/UI gates, published diagnostic registry, decoder version handling, and the existing stock-restoration path. AF3.9 remains held in the app. AF4.0 is explicit, fixed to the original 50 mm f/1.4 setting, and presented as camera-unqualified. Offline `prepare-reference-upstream` returns before device inventory; constructing `DeviceService` only stores URLs and a safety structure and does not read canonical safety state. The unchanged strict template hash/vector checks and exact setting equality still apply. Published AF3.9 and AF4.0 registry resolution passed; the new bundled resource equals the published AF4.0 image, and the frozen source defines camera BCD `0x40`. Independently rerunning the root decoder suite passed 373 checks (`artifacts/private/astra49-host-decoder-review.json`). No app/CLI was launched and no hardware API was called during this review.

One concrete decoder wording finding was sent to root: the released fallback preserves the driven anchor position but sets `still.t` to the released stability window's start. Therefore AF4.0 `stillnessAnchorMS` during released settle is not the timestamp of the last threshold-crossing movement. The initial shared decoder description claimed that interpretation. Version-specific wording must explain this distinction; a budget-phase record with `driveQualified=false` cannot determine whether its timestamp arose in drive or released settle. AF3.9's original interpretation must remain intact. This finding concerns diagnostic interpretation, not image bytes or the qualification policy.
