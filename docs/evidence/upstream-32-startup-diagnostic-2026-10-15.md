# Upstream C startup/handshake candidate 3.2 — October 15, 2026

**Prepared offline; no USB reports, upload or new camera test performed.** The
owner authorized the upstream C foundation, modular startup/handshake diagnostics
and fixes, testing, documentation, commit and push, with flashing deferred.
The adapter's latest verified image remains 3.1; its missing-aperture/blocked-
shutter result with normal shutdown remains [failed and held](upstream-31-camera-failure-2026-10-14.md).

## Proven receive defect and controlled compatibility change

The direct upstream `em_init` enables RX, polls for the body's initial CS rise,
then clears RX. Bytes delivered by UART interrupts before that polling observation
are lost. The new host interleaving supplies every split of an 11-byte,
checksum-valid opener, including its complete arrival before the observed rise.
All **12 candidate cases pass**. Pinned frozen 3.1 fails all **11 early-prefix
cases** and passes the zero-early-byte/noise control. This is a demonstrated
software defect and repair, not proof the owner's camera took that interleaving.

The small helper preserves plausible partial init prefixes, validates complete
prefix checksum/terminator, and retains idle-noise clearing. A short critical
section prevents RX append/reset overlap. The ordinary window-close parser and
protocol remain upstream. All eight retained upstream host outcomes pass.

The candidate also restores **lens ID 234**, present in the unmodified stock-
derived packet table, rather than upstream's experimental 50496. This is a
controlled compatibility hypothesis, not a measured root cause. Nominal f/1.4
and the upstream `0x08` capability-controlled optional `0x28` aperture copy remain
unchanged from 3.1. No guessed exposure compensation, forced readiness or new
AF controller is introduced. The C servo, focus mapping/prediction, homing and
parking algorithms remain upstream; only peripheral wait guards affect their
driver fault paths.

## Bounded diagnostics and fault containment

The [module and design](../../firmware/upstream-diagnostic/README.md) record
startup stages, observed requests, returned transmissions, handshake flag and
faults in 48 fixed RAM events plus saturating summary counters. Persistent
records use a reserved **1 KiB application tail**, outside executable/initialized
ROM. Pages have explicit little-endian fields and CRC32. The device performs no
runtime erase, nonblank-page overwrite, same-boot retry or storage wrap; storage
is bounded to sixteen distinct pages. After power loss an all-FF slot can be
selected again, so this is not a lifetime program-attempt/endurance guarantee.

Healthy early startup and connected operation do not program flash. Persistence
is deferred to no-body/incomplete-handshake quiet paths, UART-disabled shutdown,
or a terminal guarded fault after motor detachment. RX/EIC callbacks only update
bounded RAM. Faults use finite software iteration budgets; CS waits additionally
have an eight-second firmware-tick bound. A wedged AHB/NVM device, CPU exception
or early power cut can still prevent a record, so blank logs remain inconclusive.
Persistent logging can stall CPU/IRQs; real latency, power integrity and timing
effects remain unmeasured. This is diagnostic firmware, not a production logging
or factory-parity claim.

## Image, host and checks

The [fixed 50mm image](../../firmware/candidates/3.2.0/README.md) is 20,480 bytes,
SHA-256 `e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
Initialized ROM ends at `0x9aac`, leaving **340 bytes** before diagnostics at
`0x9c00`. Static RAM is **3,332 bytes**, stack reservation **8 KiB**; high-water
and physical timing are unmeasured. Loader version is 3.2.0, camera tag BCD 0x32.
There is no runtime profile row; other or edited profiles are rejected.

App **0.15.0/build 19** and `prepare-startup` / `apply-startup` provide explicit
preparation/install paths. Held 3.0/3.1 guidance stays in place. The Device view
routes an installed 3.2 image to USB tools for later diagnostic retrieval; it
does not claim camera readiness or offer profile application. Native upload,
journal, physical reconnect, same-unit backup and strict full-image verification
are unchanged. A programmed log byte is **not** excluded from initial upload
verification. Post-camera data use a separate read-only backup/offline decoder;
ordinary image inspection keeps its exact matching policy.

Validation evidence:

- Twelve first-window cases pass with Address/UndefinedBehavior sanitizers;
  eleven frozen-3.1 failures are detected.
- All eight upstream host outcomes pass. Log tests cover gating, page bounds,
  exhaustion, occupied/torn pages, failed writes/reads and guard-budget expiry.
- Nine cases execute the compiled candidate NVM writer in Unicorn, checking
  first/last page, address/alignment, occupied-page and controller-error guards.
  The peripheral model does not prove electrical programming or cache behavior.
- Seven decoder tests pass; offline CLI checks accept the pinned code prefix and
  reject altered code/wrong version. CRC/torn/invalid/full states stay explicit.
- All 53 Swift tests pass, including 3.2 transport/backup/journal bounds,
  rejection of unexpected log bytes before camera use and fixed-profile UI flow.
- Signed app/CLI packaging and exact native preparation pass. Older firmware
  and original stock recovery are preserved; private logs and canonical device
  state are not published.

The older whole-reference collection checker encounters pre-existing archived
README checksum drift and many later private analysis files outside its original
catalog. That report remains private, with the historical public report preserved.
The new primary-source index/catalog hashes and every pinned upstream input used
for this build pass their targeted checks. This limitation is not presented as a
successful full-collection verification.

See [validation and source hashes](upstream-32-validation-2026-10-15.json),
[first-window/host results](upstream-32-host-tests-2026-10-15.json),
[compiled ARM writer checks](upstream-32-flash-arm-2026-10-15.json),
[preserved artifacts](upstream-32-preserved-2026-10-15.json),
the [manifest](../../firmware/candidates/3.2.0/contax-zeiss-50-f1-4.manifest.json)
and [later test/log runbook](../upstream-startup-diagnostic-test.md).
No physical aperture/capture fix, autofocus lock, camera acceptance or complete
factory reconstruction is claimed. Flashing and one camera cycle remain separate.
