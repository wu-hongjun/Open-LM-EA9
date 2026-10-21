# AF 4.0 — bounded reference qualification and capture handoff

Subsequent interactive [upload and strict verification](upstream-40-upload-2026-10-20.md)
passed after physical reconnect. [Camera acceptance subsequently failed](upstream-40-camera-failure-2026-10-21.md);
further 4.0 trials are held. Read-only retrieval is complete: full flash/protected
data unchanged, all 16 diagnostic pages erased, crash location unresolved. The offline evidence below
remains a historical preparation milestone, not an installation or camera result.

**Prepared offline for the original Contax Zeiss 50mm f/1.4; not flashed or camera-qualified.**
The owner authorized Astra audits, modular fixes, tests, documentation and publication,
with flashing separate. No adapter enumeration/open, USB/HID report, motor operation,
updater/app launch or canonical Application Support access occurred in this work.
The native preparation commands used new private state and returned before inventory.
Dates use the owner's October 20 America/New_York day; the host UTC clock is October 21.

## Evidence and causal scope

The [3.9 camera/log record](upstream-39-camera-failure-2026-10-20.md) remains a failed
camera milestone: two reported photos then blocked further capture, normal shutdown,
unknown saved-file status and uncertain focus mode. Its14 valid diagnostic pages
have no initialized normal-servo snapshot. Home failed at the300-tick drive cap;
anchor age20 versus40 required, software displacement−2902, last entered iteration299,
shared polls7099/1000000, then 17 consumed non-Stop requests while inhibited. These
are software observations, not physical travel/duration, focus acquisition or shutter
attempt counts. Retained capture exchanges cannot be mapped to the blocked attempt.

[Astra49](../audits/astra-49-home-qualification-2026-10-20.md) reproduces the exact
aggregate late-anchor schedule with production home/pump/tracker/UART/motor paths:
3.9 fails drive qualification;4.0 detaches at 300 and qualifies after 40 released ticks.
The trajectory between observations is supplied, not a recovered real encoder stream.
[Astra51](../audits/astra-51-factory-qualification-2026-10-20.md) independently confirms
that original upstream permits settling after the bounded drive loop. Our earlier
hardening introduced a stricter drive-qualified gate. Recovered stock conditional
homing also separates its 300 drive budget and 500 release/delay/reference sequence;
it does not validate stillness. Its ordinary enabling gate remains unresolved.
Factory persisted calibration is per-unit and is not copied into new readiness.

This repairs a reproduced software readiness rejection. It does not establish the
physical endpoint, cause of late arrival, sensor timing/polarity, or the body's shutter
decision. A stalled mechanism remains indistinguishable from a stationary endpoint.
The new fallback has weaker driven corroboration than 40 driven stillness ticks;
this is explicit experimental software-reference qualification, not a stronger
physical-homing claim. Stock AF has only been partially reconstructed, not fully
reverse engineered or reproduced. Factory parity remains unestablished.

## Modular change

The early 40-tick driven path,300-tick active drive cap, duty 800,6-count stillness
threshold,500-tick settle deadline, shared1000000 poll cap, cancellation/session
checks, sticky inhibition and existing servo guards remain. The late fallback:

1. Observes the cap, immediately detaches GPIO, then clears both PWM pairs using
   bounded synchronization while detached. It never remuxes the pins at cutoff.
2. Requires exact300-tick cutoff, a repeated pre-cutoff anchor and negative net travel
   above 6 but at most configured travel+6. Overshooting/stale pump returns fail closed.
3. Keeps the cutoff coordinate fixed and requires 40 released stable ticks. Drift
   beyond 6 fails immediately; movement cannot reset the anchor into later success.
4. Checks the post-settle sample and final commit sample. The encoder helper commits
   zero from its already validated last raw sample, with no second unchecked raw read.
   Readiness is published only after the existing serialized cancellation recheck.

The detached PWM clearing fixes a discovered handoff hazard: the servo attaches pins
before issuing its first new duty, so leaving old home compares could restore home
drive briefly. The final sample checks close a second-read/bouncing-sample gap.
[Astra50](../audits/astra-50-readiness-capture-2026-10-20.md) composes successful home,
origin reset, actual servo/mapping and protocol capture/shutdown owners. No separate
production capture-owner fault was reproduced; raw completion still silences periodic
status until successful ordinary re-arm. Failed home remains closed while queries and
shutdown remain live. No synthetic completion, forced readiness or raw-status re-arm
is introduced.

The fixed 50mm metadata, nominal AV 4352, unknown actual iris, stock 0x34 behavior and
upstream controller remain. Version4.0/BCD 0x40 avoids an unrepresentable one-byte
BCD 3.10; it is not a maturity claim. Failed-home tag 0x40 is admitted only by 4.0;
3.9 and older decoder rules remain strict. Released settling resets anchor time to
the released-window start while keeping its coordinate; phase 19 with false driven
qualification cannot distinguish drive versus released-phase work exhaustion.

## Exact artifact and build

[Candidate](../../firmware/candidates/4.0.0/README.md), [manifest](../../firmware/candidates/4.0.0/contax-zeiss-50-f1-4.manifest.json),
and [delta](../../firmware/candidates/4.0.0/from-39.patch) build on original pinned C
`d52ed06cc449918f938e0695fbf29a0c4141f2b2` and frozen 3.9. Image SHA256:
`06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae`;
manifest SHA256:
`8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`.

Two fresh builds match image, manifest, patch, all 49 source files and host shim.
Main, motor, encoder helpers/headers and version differ from3.9; no new translation
unit. The initial inherited flags left only108 bytes, below the unchanged256 floor,
and were rejected before publication. Applying existing `-Os` to encoder and motor
recovers room: code/data end 38956 (`0x982c`),980-byte margin, static RAM 3040,
stack reserve 8192. No diagnostic capacity or safety reserve was reduced. Compiler
and dependencies remain pinned. No lane47 arithmetic optimization was needed.

## Validation and limits

The [acceptance workbench](../../firmware/upstream-hardening/next40/README.md) binds
actual candidate sources, tests, fixture adapters and before/after pins. Lane49 has
71 executions:66 baseline/candidate scenarios and five assertion-killed causal
mutants. These include exact late cutoff, boundaries/wrap, moving/noisy/wrong-way/
implausible travel, release/final/after drift, stale UART crossings, shared/frozen
work budgets, corrupt coordinates, Stop/session/shutdown and no unsolicited retry.
Already-stationary stiction remains an explicit accepted ambiguity of the early path.

Lane50 exercises seven composed candidate cases, six named mutants and the frozen
3.9 failing late-home control. It asserts one origin commit, zero-relative servo
entry, resolved target, one normal completion, pending/session ownership, position/
forecast/status wire fields, three capture raw/re-arm cycles, live queries and shutdown.
ASan/UBSan and finite process limits apply. Synthetic I/O and scheduling do not model
optics, electrical drive or camera behavior.

The final compiled audit binds exact image/source/SU/ELF/raw and normalized disassembly,
symbols and sections. It reviews 12 indirect calls, 153 functions and 536 call sites;
no unresolved edges or recursion. Conditional all-vector stack 1588/8192, including
foreground 1172, EIC 168 and UART 32. It verifies detached cutoff before zero compares,
final-sample/readiness ordering, callbacks, vector/handoff and unchanged NVM caller
gates. Four internal and three external rejection controls pass. Stack bounds depend
on the documented IRQ/library/callback assumptions and are not measured high water.

The new decoder passes 373 synthetic checks alongside all 307 old 3.9 checks. All 36 final firmware suite groups pass. Full
acceptance also retains source-bound historical coordinate, query, capture, timeout,
startup, tracing, writer/initializer, original-stock re-arm and decoder regressions;
exact counts and input digests are in the [machine-readable receipt](upstream-40-reference-2026-10-20.json).
No synthetic or compiled result establishes sustained camera capture/shutdown.

## Host, preservation and next step

App 0.23.0/build 31 adds explicit 4.0 resource/hash/version routing and native
`prepare-reference-upstream`/`apply-reference-upstream`. Historical commands retain
their original image pins. The 53 named Swift tests pass, including fixed-image
variant coverage and consent/profile/installed 4.0 workflow checks. Packaging and
ad-hoc signatures verify without launch. Isolated native preparation produces exact
4.0 and historical 3.9 images; the CLI hash is
`44d9b94f9338037978575fa6a61d2c495383eb8749e3b11bc95c93de63f89b1c`.

The [preservation ledger](upstream-40-preserved-2026-10-20.json) checks 146 historical
release/recovery/pin artifacts and every older registry entry. Original stock 1.8
recovery and all published candidates remain byte-identical. The prior signed
app 0.22.1/build 30, CLI and bundles are preserved privately. Raw backups, keys, unit
identifiers and real camera traffic remain private; only derived/synthetic evidence
is published. 3.9 remains held and no pending USB transaction or safety marker was
changed.

Next is a separately authorized upload, physical reconnect, strict complete-image/
protected-data verification, one initial MF cycle and read-only logs under the
[coordinated procedure](../upstream-reference-test.md). AF-S testing follows only
after that review. No hardware action or further owner observation is required to
complete this offline milestone.
