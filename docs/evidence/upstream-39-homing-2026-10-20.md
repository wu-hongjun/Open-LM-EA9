# AF 3.9 — release liveness repair and failed-home observations

**Prepared offline for the original Contax Zeiss 50mm f/1.4; not flashed or
camera-qualified.** The release no longer depends on unused ADC telemetry in
startup or the communication pump. Bounded new observations distinguish failed
homing from later consumed focus requests. The physical drive-phase failure and
camera shutter-block cause remain unresolved; these changes are not a claim of
a camera cure or factory parity.

[Sanitized integrated receipt](upstream-39-homing-2026-10-20.json) ·
[Candidate/image/manifest](../../firmware/candidates/3.9.0/README.md) ·
[Reproduction](../../firmware/upstream-hardening/next39/README.md) ·
[Host receipt](upstream-39-host-2026-10-20.json) ·
[Separate future upload/test](../upstream-homing-test.md).

## Starting evidence and three Astra lanes

The [3.8 camera/log record](upstream-38-camera-failure-2026-10-20.md) reports
hunting, apparent focus for one photo, reset and no further photos. Shutdown
was normal. AUTO was the exposure mode; actual focus/Pre-AF and whether a file
was saved remain unknown. The retained phase 17 means drive-stillness did not
qualify before the cap, but supplies no homing trajectory or fault occurrence
time. The empty servo collector does not exclude homing movement. Its local
raw-readiness return near shutdown cannot be identified as the first shutter
attempt. No new hardware observation was invented during this work.

Three `gpt-6-astra` lanes continued the established campaign, with root owning
composition and commits:

- [Astra45 — homing](../audits/astra-45-home-drive-2026-10-20.md) executes exact
  foreground/home/query/tracker and UART bodies with supplied hardware/ticks.
  Moving, noisy, late-arrival and delayed-returning-UART scenarios can all
  produce phase 17 under the current conservative policy. No reproduced defect
  justified changing origin, polarity, drive duration, threshold or readiness.
- [Astra46 — shutter/readiness](../audits/astra-46-shutter-readiness-2026-10-20.md)
  confirms non-Stop focus commands can be taken after failed homing without
  entering the servo. It adds a discriminator, not a fabricated completion or
  raw-readiness status re-arm. It also integrates the explicit host route and
  independently reviews decoder interpretation.
- [Astra47 — factory origin/peripherals](../audits/astra-47-factory-origin-2026-10-20.md)
  executes bounded original-stock instructions through the pinned REA oracle.
  It closes ADC consumer/clock effects independently and reviews the final ARM
  image, callbacks, stack and flash-write gates.

The factory reader has explicit CS setup/hold busy loops omitted upstream.
Mode/packing/baud/CS configuration match, but no measured sensor timing contract
or invalid-sample reproduction establishes a violation. The conditional factory
home is a fixed 300/500-delay sequence with reference capture, not upstream's
six-count/forty-tick stillness algorithm. Its ordinary enabling writer remains
unresolved. Neither that block nor persisted factory coordinates validates a
physical origin. Blindly adding delays, forcing the factory gate or declaring a
failed home successful is unsupported. Existing raw-readiness silent/re-arm
policy remains consistent with the bounded original-instruction replay.

## Accepted production changes

The [pinned plan](../../firmware/upstream-hardening/next39/accepted-lanes.json)
applies45,46,48 to the exact frozen 3.8 materialization, then changes version
`0x38`→`0x39`. Only `main.c` and `emount.h` differ; all protocol/owner/shutdown,
servo, encoder, driver, optical-map and trace-writer module bytes stay exact.

1. [Release ADC dependency removal](../../firmware/upstream-hardening/followup/48-release-adc/README.md):
   `vdd_init` plus its ADC stage marker, per-pump sample, and home min/max
   reset/result are retained only when legacy logging is enabled. Every value
   consumer was already inside that logging guard. This is logic-supply
   telemetry, with no motor-current guard, servo or protocol consumer. The
   release stops waiting for an irrelevant peripheral; full legacy behavior is
   retained. ADC code/private state are discarded by the linker. This saves 412
   bytes before adding observations. It does not prove ADC stalled in the 3.8
   trial; real foreground cadence changes and remains unmeasured.
2. Failed-home snapshot: existing loop-condition ticks are retained locally;
   after motor inhibition detaches the drive pins,32 reserved RAM bytes record
   phase 17/18/19, drive qualification, phase/cutoff/last-entered-iteration ticks,
   pre-drive position, stillness anchor position/tick and shared polls. No hot
   clock, sensor or ADC read is added; the new tick read occurs after inhibition.
   GNU alias-safe aligned stores publish the tag last. No readiness, retry,
   cutoff, deadline, work budget, duty or controller setting changes.
3. Consumed-request counter: byte 115 increments with saturation for non-Stop
   commands actually taken while inhibited after the tagged fault. Stop remains
   separately acknowledged. It does not count arrivals, overwrites, motor
   executions, optical focus or camera shutter events; zero excludes none of
   those. It may span protocol sessions and 255 is a lower bound.

The optional full-domain unsigned stillness arithmetic optimization reviewed by
Astra47 is **not included**: ADC removal provides sufficient space without this
extra production change. No runtime profile row, iris sensor/control or aperture
policy change is introduced. LensID234 and nominal AV 4352 remain; actual iris is
Unknown in the app.

## Identity, footprint and evidence

Image SHA-256: `87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44`.
Manifest SHA-256: `9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a`.
Independent fresh builds have identical20,480-byte image, raw bytes, source
manifest and patch. Code/data end 39304 (`0x9988`) leaves 632 bytes before the
1 KiB diagnostic region, above the unchanged 256-byte minimum margin. Static
RAM 3040; stack reserve 8192.

Final offline acceptance runs 33 suites: fourteen pinned historical regressions;
exact composed home/request/ADC paths; retained capture/shutdown and factory
re-arm; trace/compaction; ARM reset/writer; legacy/v3/phase/home decoders;
registry37/38/39; and compiled composition. All 49 source hashes and test-input
pins are checked before/after. All 141 inventoried historical release/recovery
artifacts and prior registry entries remain exact. Original stock 1.8 recovery,
all old images/manifests/patches/resources and trusted pins are preserved.

The home suite has 42 executions:34 positive outcomes and eight designated
negative controls, including sensor-read parity. Request tests retain six
frozen contracts and their missing-counter failure, then pass ten composed
cases and reject seven precise mutants. ADC tests have twelve executions:
six expected passes and six specific failures, using the real conversion/wait
body and supplied completion/stall boundaries. No arbitrary crash is accepted
as a successful control. The final candidate's extracted startup/pump bodies
must equal the tested ADC proposal.

Historical fixtures advanced their synthetic clocks, RX or pump depth inside
ADC stubs. Initial integration exposed that coupling after release ADC removal.
Explicit private adapters move the same scheduler bodies to pump exit for both
controls and candidate; assertions, wire values, cutoffs and negative controls
remain. No production change was made to satisfy those fixture assumptions.
Historical source/receipts stay frozen; private adapters suppress duplicate
public receipt writes. These controlled schedules are not physical cadence
measurements.

The [compiled audit](../audits/astra-af39-compiled-acceptance-2026-10-20.md)
checks 148 emitted functions,504 call sites and 12 indirects with no unknown
edges or recursion. Its conditional all-vector stack envelope is 1532/8192
bytes, 16 more than 3.8's estimate. Exact callbacks, vectors, library stack
operations, cutoff-before-snapshot stores and unchanged NVM callers are checked.
Only two reviewed RAM constants adapt the frozen analyzer; repeat-build ELF/map
hashes may change only after normalized instructions/symbols/program headers
match. Four internal and three external bad-image/policy controls reject.
Physical stack high-water, inherited boot/IRQ state and peripheral/NVM latency
remain outside the conditional guarantee.

## Decoder and host

The 3.9 decoder requires a complete associated three-chunk snapshot and checks
the new failure tag, phase/drive flags, exact poll-budget invariant and zero
first 112 servo bytes. Legacy3.7/3.8 retain reserved-zero rules and reject the
new tail. The stillness anchor may be its initial sample or a later threshold
crossing; it is not a final sample. Last-iteration interval includes all pump
and check work, not UART alone; ticks can wrap or be lost. Independent review
closed poll-budget strictness and anchor-label issues;307 synthetic checks pass,
including malformed fields, old-version isolation, missing/torn/cross-cohort
chunks and wrap/saturation. CRC consistency is not authentication.

App 0.22.0/build 29 adds the pinned fixed 50mm resource, separate guarded install
and explicit `prepare-homing-upstream`/`apply-homing-upstream` routes. Prior
holds and command/image meanings remain.53 named Swift tests across 20 variants
pass, as do nine isolated native upstream prepare routes and wrong-lens/overwrite
controls. Packaging and signature verification pass without launching the app.
Actual aperture remains Unknown and library edits cannot change this fixed image.
The prior signed package is retained privately. No visual/runtime UI validation
was performed because opening the app would enumerate USB.

## Remaining work

No device was enumerated/opened; no USB/HID report, flash, motor command, updater
or app launch occurred. Canonical Application Support state was not accessed.
No upload journal/reconnect marker was modified. Private dumps, keys, identifiers
and real frames remain private.

AF 3.9 is ready for a separate guarded flash and strict reconnect verification,
then one owner-coordinated lifecycle test and read-only log review. It cannot
be called stable, a shutter repair, a physical homing fix or factory parity from
these simulations. The new discriminator should first establish whether a
failed phase reflects continuing/noisy feedback, late arrival or a delayed
returning iteration, and whether later commands are consumed while inhibited.
Physical/electrical measurements may still be needed if USB-retained evidence
cannot distinguish them. No further camera attempt or restoration is requested
in this offline task.
