# AF reconciliation and Device workflow evidence — session begun 2026-10-10

Final packaging and records completed October 11, 2026 (America/New_York).

**AF 2.2 is prepared and host-tested, not installed. App 0.5.0 build 8 is built,
signed locally and open on Device. The adapter retains the installed,
byte-verified 50mm AF 2.1 image.** This session sent no explicit HID feature
reports, uploaded nothing and performed no fresh CHECK or flash readback.
OS descriptor discovery found one qualified adapter after the owner reconnected it.

The [design record](../af-reconciliation.md) explains the factory/upstream
differences and adopted policies. The [app guide](../macos-device-workflow.md)
documents the current workflow. A [machine-readable record](af-reconciliation-2026-10-10.json)
contains hashes, check counts and scope.

## Owner observation of installed 2.1

The owner answered the question about the installed 2.1 candidate:

> Shutdown is proper. I can't test actual focus right now because I am waiting for C/Y to M converter, but the motor does move.

Motor movement and proper A7C II shutdown are therefore **owner-reported**.
Startup/homing direction, duration and reference location remain unverified.
AF-S lock, repeatability, lens-loaded behavior and photo sharpness remain pending
the converter. No new image or timing trace accompanied this observation.
The prior [USB upload evidence](af-50-upload-2026-10-10.md) remains the installation
record; these observations do not qualify AF 2.2.

## Prepared products and compatibility

| Product | Identity/result |
| --- | --- |
| 2.2 zero-profile template | 20,480 bytes; `e3614dfb8482644ba5b6114b591352669187e8ebd01a1344718f580ca12c3b36` |
| Personalized 50mm f/1.4 2.2 image | `c963e7970f7b69aaa1115afb6a1aee95644f5a243352299689452d7c1f0c6d98` |
| Lens profile | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340`; unchanged from installed 2.1 |
| Frozen 2.1 template | `6e48fcdd48df13ec529badd4626ee99120e005e4cd011ad664c683720b006552`; unchanged |
| Metadata 2.0 template | `d7f85bb53897d6b83f30c528d7790ec37e7164090d882251b917060cc300f293`; rebuild reproduced the original hash |
| App | `dist/Open LM-EA9.app`, 0.5.0 build 8; release build and strict ad-hoc signature verification passed |
| CLI | `dist/ea9ctl`; release build/signature passed; `prepare-af` now selects 2.2 |

The prepared image/manifest are under
`artifacts/firmware-milestone/af-reconcile-2026-10-10/contax-zeiss-50-f1-4.bin`.
The new reserved profile is at `0x9f00`; the application occupies
`[0x5000,0xa000)`, 20,480 bytes. It stops before the retained factory prefix/copy. Camera version BCD is `0x22`, loader metadata version 2.2.0.
The zeroed template profile remains intentionally invalid.

The [source/dependency build manifest](af-reconcile-build-manifest-2026-10-10.json)
matches current source hashes. GNU size reports text 18,460, data 1,280 and bss
9,680 bytes; bss includes the reserved 8 KiB stack. Linker RAM/application/profile
bounds passed, AF symbols were present, and no diagnostic flash writers survived
the release link. Existing unused nosys I/O stub warnings remain nonfatal.

Before modifying firmware, the entire previous `src` tree, Makefile and build,
profile preparation and test scripts were preserved with a SHA-256 manifest in
the local milestone's `baseline-source` directory. The exact 2.1 resource/pin
is preserved so the installed image, past backup/journal and reconnect
verification remain readable. The current source receives a distinct 2.2 version
and resource, rather than changing the meaning of the old 2.1 digest.

The updated app loaded the actual completed 2.1 journal and applied-lens history
without error. An additional offline check matched their image hash, canonical
profile and the frozen resource. This validates saved evidence compatibility;
it is **not a fresh device read**.

## Firmware verification

`python3 scripts/test-firmware.py --af` passed:

- Real E-mount parser/frame, handshake, no-body/slow-body and shutdown fixtures;
  inherited servo, focus map, distance and predictor checks.
- 65,927 bounded command cases, sentinel rejection and latched motion ownership/
  fault behavior, plus the existing bounded register/delay fixtures.
- New reconciliation counterexamples: all 65,536 protocol values; every admitted
  encoder count; 192-count bridge; extreme signed inputs; homing drift, direction,
  drive/settle deadlines, clock rollover, frozen-clock ceiling and cancellation;
  Move/Scan/Drive failure suppression and explicit Stop eligibility.
- Thirteen actual `main.c` integration cases: successful home; ADC/encoder failures
  during home; shutdown during home; missing-end-stop timeout; ADC failure during
  focus; final-report encoder fault; settling drift; wrong-way feedback; a real
  parsed Stop record during home; a delayed control update; equal-target arrival
  checks; and final encoder displacement outside the acceptance band.
- Fourteen cross-language profile/packet cases: metadata and 2.2 for seven prime/
  macro profiles. The C decoder checks corruption rejection and transmitted
  focal/aperture/name, version and checksums. The uncontrolled zoom is excluded.

The new pure reconciliation suite also passed AddressSanitizer and
UndefinedBehaviorSanitizer with `-Wall -Wextra -Werror`. These results qualify
software policies and simulated/register-shaped paths, not physical end stops,
sensor wiring, actuator timing or optical focus.

The first settling-drift test failed: the simulated mechanism could drift to the
other stop, then appear stationary. The added ±120-count settle displacement
bound makes that fail and prevents a false reference commit. Its value is an
experimental guard, not recovered factory calibration.

Logs: [firmware build](af-reconcile-firmware-build-2026-10-10.txt),
[firmware suite](af-reconcile-firmware-tests-2026-10-10.txt),
[sanitizers](af-reconcile-sanitizers-2026-10-10.txt),
[metadata rebuild](af-reconcile-metadata-preservation-build-2026-10-10.txt).

## App verification and manual inspection

`./scripts/swift-local.sh test` passed 40 named tests: seven LensCore, 29 DeviceKit
and four AppWorkflow tests. Upload, failure/no-retry, journal integrity and
reconnect verification tests exercise metadata 2.0, frozen AF 2.1 and AF 2.2.
New workflow tests verify connection transitions reset consent, blocked sessions
stay blocked, discovery does not run during an operation, profile selection is
local, unsaved edits are retained, the zoom is rejected until configured, local
CLI-published history refreshes, AF variants are preserved, the two-second
monitor refreshes and cancels, and the new bounded image retains the synthetic
upper factory prefix/copy while inspection uses the new profile address.

Native UI inspection with the connected adapter confirmed:

- The Device page displays **Connected**, dated **2.1.0**, and USB-verified
  **Contax Zeiss 50mm f/1.4**, 50 mm, reported f/1.4.
- The dropdown lists all eight profiles, including Biotar 58mm f/2. Selecting
  85mm changed the preparation and Apply label while retaining the verified 50mm
  on-adapter card. The local selection was restored to 50mm, showing Up to date.
- The compact final layout exposes the dropdown, primary action and connection
  acknowledgement together at the default window size. Photos remain bundled.
- USB tools contains a separate **Install Experimental AF 2.2.0** action. It
  remained disabled without connection acknowledgement and was never invoked.
  The app was left on Device with 50mm selected.

Physical unplug detection was covered by injected inventory transitions and the
automatic timer test; no extra physical disconnect was requested in this session.
Actual launch/foreground discovery and same-unit cached history were inspected
on the connected adapter. Discovery only opens the shared HID manager to inspect
descriptors; automatic refresh never calls the report exchange transport.

Logs: [native tests](af-reconcile-app-tests-2026-10-10.txt),
[release packaging](af-reconcile-app-build-2026-10-10.txt).
Unit identity/inventory and older recovery evidence remain private.

## Remaining qualification

The [completed broader REA ledger](../reverse-engineering/whole-firmware-reconstruction.md)
was reviewed before closing this milestone. Its main-state models retain the
same unresolved ordinary homing gate and nominal timing boundaries. It also
identifies the original second factory application at `0xa080`, preceded by an
unknown 128-byte prefix. Legacy 2.0/2.1's profile at `0xa000` replaces that prefix
and the first 128 duplicate bytes. Prior tail checks from `0xa100` remain true
but do not establish preservation of a complete factory recovery image.

The final 2.2 candidate therefore moves its profile to `0x9f00` and stops all
upload pages before `0xa000`. Native bounds and inspection are version-specific.
A synthetic non-FF upper-prefix/copy test verifies the whole region remains
unchanged, and separately checks that inspection ignores an old profile at
`0xa000`. The original full backup retains the factory prefix/copy; stock
restoration includes it. Upgrading from 2.1 preserves its already changed row
rather than repairing it. The superseded uninstalled 2.2 draft is retained locally
but is rejected by the final template pin. See [the layout assessment](../af-reconciliation.md).

2.2 still needs explicit installation, physical reconnect and byte verification.
With the converter available, the first loaded-lens test remains 50mm f/1.4
still-image AF-S: verify startup/reference, Stop and shutdown before near/far
focus and original-photo sharpness. Actual timing/travel, stock restoration from
AF, other lenses, AF-C and video remain unqualified. No new USB management service,
factory reference write or factory PID port is claimed by this milestone.

## Subsequent AF 2.2 installation

The later, explicitly authorized AF 2.2 USB installation is recorded in
[the October 11 upload/reconnect evidence](af-22-upload-2026-10-11.md).
This earlier record retains its original session scope and measurements.
