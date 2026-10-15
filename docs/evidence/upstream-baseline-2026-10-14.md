# Direct upstream baseline — October 14, 2026

Subsequent hardware update: the authorized 3.1 upload completed; physical
reconnect and strict verification are pending. See [the installation record](upstream-31-upload-2026-10-14.md).
The preparation evidence below describes the earlier offline build only.

**Prepared offline; not flashed or camera-qualified.** After the byte-verified
AF 3.0 image again froze the A7C II on full press and required battery removal,
the owner requested trying the upstream work directly. The [failure and finite
interruption comparison](af-30-camera-failure-2026-10-14.md) were committed and
pushed first as `010ee31`. No post-failure hardware report or restoration was
sent during preparation. The adapter's latest reported location is the camera;
a USB-cap connection confirmation is pending.

The repository's current remote HEAD matches our retained upstream commit
`d52ed06cc449918f938e0695fbf29a0c4141f2b2`. Its README documents a Sony a9 II
platform, working AF and a release configuration with logging compiled out.
That is a useful baseline, not an A7C II qualification. Its current header
labels native lens ID 50496 as experimental; we preserve it for comparison.

## Why this differs from the previous candidates

Recent candidates combined our factory-derived controller, aperture/metadata
layer and reconstructed protocol arbitration. Successful motor focus with failed
capture does not isolate which of those paths differs from the camera's needs.
A complete upstream baseline gives a concrete comparison before introducing more
factory scheduler work or optimization. It does not assume that our newly
reproduced interlock gap is the physical cause of the freeze.

| Boundary | AF 3.0 | Direct upstream 3.1 baseline |
| --- | --- | --- |
| AF controller | Our stock-derived PID/backend | Upstream servo unchanged |
| Protocol/capture | Our arbitration and responder | Upstream `emount.c` unchanged |
| Main/homing/park | Our readiness/service policy | Upstream main unchanged |
| Sensor, voltage, motor, UART/EIC | Our guarded fork | Upstream driver C files unchanged |
| Lens ID | Legacy 234 | Upstream 50496 |
| Optical rows | Previous fork declarations | Upstream rows; pupil-size row rescaled with declared aperture |
| Metadata | Runtime profile row | Fixed original 50mm f/1.4 configuration |
| Hardware logging | None | Upstream release configuration; none |

All 15 compiled protocol/AF/driver/main behavior C units are byte-identical to
the pinned upstream source. Startup and system C change only DFP header/vector
spellings. The linker caps ROM at `[0x5000,0xa000)`, protecting the retained
factory prefix/copy/upper flash. `emount.h` changes the version tag to 0x31,
three documented aperture constants to 0x1100 and rescales the pupil-size row
by the encoded f-number ratio `2^0.375`, yielding `d2 5a c8 e1 e2 ea`.
Focal length stays upstream's 500 (50mm × 10), other optical rows and lens ID
stay upstream. [The complete patch](../../firmware/upstream-baseline/50mm-f1.4.patch)
contains the build/config changes and one test-only default descriptor update.
No speculative capture fix is mixed into this baseline.

The inherited pupil curves are not measurements of the owner's Contax lens.
The original waits, homing direction/timing, park and servo guards are preserved;
this does not import all our fork's bounded-I/O and fault-service improvements.
Both images use upstream's release `-O2 -DNDEBUG -DEA9_NO_LOG`; upstream's
recorded camera sessions used debug `-O1`, so those sessions do not qualify
this release build. The phase-driven factory interruption gap remains open
research; this comparison is intentionally the upstream implementation.

## Native host support and validation

App 0.14.0/build 17 offers explicit upstream installation for the original 50mm
profile. `prepare-upstream` and `apply-upstream` select 3.1; historical
`prepare-af`/`apply-af` retain held 3.0. All old versions remain recognizable for
backup/recovery. The app prominently marks installed AF 3.0 as held and routes
its primary action to USB tools instead of suggesting camera use.

The upstream image contains no runtime profile row. Native planning, crash
journal validation, inspection and reconnect verification recognize its full
pinned bytes, then publish its fixed known lens configuration. Wrong/edited
profiles are rejected before USB. The main dropdown keeps edits local and
explains that another lens requires another build; it cannot pretend a row
write changed upstream's compiled constants. Backup, same-unit/bootloader
qualification, exclusive access, updater-process checks, durable journals,
physical reconnect and all protected-region rules are unchanged.

[Validation](upstream-baseline-validation-2026-10-14.json) records:

- Eight passing upstream host outcomes for each of the as-configured f/1.8 and
  configured f/1.4 builds. No test was removed; one configurable-lens test row
  changes its duplicated f/1.8 descriptor literal to the f/1.4 descriptor.
- 53 passing Swift tests: 7 LensCore, 35 DeviceKit, 11 AppWorkflow. The new full
  immutable-image variant participates in the upload-bound, lost-ack/cancel,
  journal-tamper, same-connection/wrong-image/factory-data verification checks.
  A fixed-settings test rejects other lenses, edits and altered padding; the
  workflow test covers the held 3.0 state and fixed-baseline dropdown behavior.
- Signed app/CLI packaging and exact native image equality from isolated seeds
  and the owner's existing 50mm profile. Canonical preparation changed no owner
  state. Twenty-three previous release/recovery artifacts remain byte-identical.

Both raw binaries are 15,588 bytes, padded with FF to 20,480 for bounded upload.
Initialized flash ends at `0x8ce4`, leaving 4,892 bytes before `0xa000`; static RAM
is 2,728 bytes with 8,192 reserved stack bytes. Stack high-water and physical
IRQ/sensor latency are unmeasured. No logging, custom factory servo or arbitration
symbols are linked. No firmware/hardware report is sent by the build.
[Build/source evidence](upstream-baseline-build-2026-10-14.json) and
[preserved artifacts](upstream-baseline-preserved-2026-10-14.json) retain hashes.
MIT/Apache notices are copied into the repository and packaged resources.

## Next hardware step

The owner already authorized trying the upstream baseline. Move the unpowered
adapter to its USB cap and confirm the updater is closed; then run the reviewed
native upload with a fresh backup. Require owner-confirmed physical reconnect,
strict full-image/protected-data verification and a separate offline audit.
Then use [the dedicated camera procedure](../upstream-baseline-test.md): preview,
confirmed-MF saved capture and shutdown before one bounded AF-S attempt. Stop
on freeze or abnormal drive; do not repeat failed AF 3.0 to obtain missing data.
If upstream works, subsequent development can add one modular change per
comparison. No claim of a cured freeze or factory parity is made before that
hardware evidence exists.
