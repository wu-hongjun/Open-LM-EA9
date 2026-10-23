# Astra55 — failure causality review, October 23, 2026

**The repeated tests proved local safety and software contracts, but did not
establish a working camera lifecycle.** AF 4.1 adds a reproducible startup
availability failure: ordinary diagnostic accumulation can prevent any later
application start. That is distinct from the still-unresolved first shutter
delay/freeze. Earlier failures also establish lost homing readiness, which can
leave focus requests unserved while protocol processing continues.

This review is entirely offline. Original stock 1.8 remains
[restored and strictly verified](../evidence/stock-18-af41-recovery-2026-10-21.md).
No enumeration, USB/HID, motor, app/updater launch, flash, or canonical host-state
access occurred. No new candidate or runtime patch is proposed. Frozen 4.1 image
`fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641`, manifest
`557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b`, and all 49 source
pins were checked before/after the executable probes. References below to source
lines mean `artifacts/private/crash41-final/src/` unless identified otherwise.

## 1. Proven: diagnostic capacity becomes application availability

`startup_trace.c:77–86` refuses append when all 16 pages are occupied.
`st_boot_record():172–187` requires a new page even for clean POR; append failure
returns1. `startup_trace_flash.c:74–85` then enters `st_halt`, with WDT disabled,
after emergency motor release. `main.c:1695–1703` puts this before board pins,
clocks, software tick and protocol setup. No corrupt record or actual crash is
required. This is intended fail-stop behavior but a concrete limitation for a
normally reusable adapter; a healthy history can exhaust its startup allowance.

The new [source-bound runner](../../firmware/upstream-hardening/followup/55-failure-causality/run.py)
executes actual trace C, production terminal/watchdog bodies and real `em_init`
against inert flash/registers. It checks the production main ordering rather
than executing the whole main. Its
[sanitized receipt](../../firmware/upstream-hardening/followup/55-failure-causality/offline-results.json)
establishes:

| Synthetic production-path schedule | Result |
| --- | --- |
|16 clean POR baseline appends, no crash/CRC damage | All return;17th boot halts with no new write |
|Initially full16 valid POR-only pages | First boot halts with zero writes |
|One clean terminal workload with32 buffered events and three footers |15 pages used; next boot consumes last page; following boot halts |
|Four baseline pages, terminal snapshot and two footers, then baseline and stage8 fault |14→15→16 pages; subsequent boot halts |
|Actual4.0 `st_init`,32 empty and 32 full-tail calls |Returns without a write; old main has no mandatory boot append |

The availability requirement deliberately fails with exit23. Removing the boot
gate in a private negative control causes the expected-halt and crash-latch
assertions to fail; bypassing the gate is not a safe remedy. The exact WDT-cause
latch remains checked. ASan/UBSan pass the intended executions. The synthetic
page shape reproduces capacity arithmetic, not camera traffic or physical resets.
The healthy terminal case exercises trace calls, not the physical shutdown path.

This was already accepted as a safety contract: [Astra52](astra-52-durable-crash-2026-10-21.md)
and [Astra53](astra-53-crash-hardware-2026-10-21.md) explicitly require full-tail
fail-stop; [lane54's test](../../firmware/upstream-hardening/followup/54-crash-powerloss/test_powerloss.c):40–42
checks the occupied frontier/full storage. Passing those tests cannot establish
indefinite healthy restart. The missing acceptance criterion was availability
over complete multi-start use, while retaining crash/torn-write fail-stop.

The [real 4.1 record](../evidence/upstream-41-camera-failure-2026-10-21.md) contains
16 valid pages, including five POR baseline records and a final summary.
Therefore a later application entry with that unchanged tail cannot pass the
boot gate. It does **not** establish that exhaustion caused the first reported
minute-long delay. The record does not map all app entries to owner power cycles
or to the camera rather than another boot context.

**Smallest next discriminator:** no hardware measurement is needed to confirm
this availability limit. Establish an explicit lifetime/capacity requirement and
evaluate it with this full production persistence path before any new candidate;
retain the crash/torn-write safety contracts.

## 2. Proven startup failure; unproven relationship to shutter freeze

Final slot 15 records stage 8/`cs-rise-wait` at 8000 software ticks, zero RX/TX
frames and no handshake. `emount.c:1512–1529` initializes UART, then polls body
CS until its finite work budget or 8000-tick deadline. In the runner, the real
initializer with synthetic CS held low reaches real `st_fail` at 8000 ticks.
It releases motor GPIOs, logs and sleeps with interrupts masked
(`startup_trace_flash.c:43–56`).

WDT preparation at `main.c:1702` only configures its clock/period. Arming is at
1750, **after** `em_init()` and initial encoder reference reads. Thus this
recorded startup failure occurs before WDT arming and before foreground retained
checkpoints; missing recovered-WDT evidence is expected on that path. It says
nothing conclusive about whether the watchdog worked during an earlier session.
After tail exhaustion, another fault could not append either.

CS remaining low at the polling points does not identify the cause: absent/late
body signaling, a missed earlier startup pulse, electrical state or a different
boot context remain possible. The single UART error does not distinguish them.
Software times reset per boot and cannot be summed into the owner's approximate
60 seconds or attached to a particular shutter press.

**Smallest next measurement, if separately authorized later:** one synchronized
startup trace of power/reset, body CS/VD, lens CS and UART, aligned to application
entry and shutter action. The useful distinction is whether the body pulse
arrives before the firmware listens, never arrives, or is present but unreadable.
No camera retry is requested by this review.

## 3. Proven timing perturbation; magnitude and physical effect unmeasured

AF 4.1 runs the 16-page scan, per-page CRC calculation and baseline program before
`board_init_pins` and `delay_init`. `board.c:18–36` is what establishes lens-CS
and PA23 outputs; the added startup work precedes those writes. This changes
startup timing versus 4.0. Its time is absent from the application's initial
software milliseconds. No measured deadline or latency budget establishes that
the added work fits the body's startup window.

At termination, `st_flush():88–115` masks interrupts across the summary, motion
and event page writes. The timestamp is sampled before that programming.
`main.c:962–984` places it after UART disable but before VD waiting and PA23;
terminal footers add more writes. [Astra53](astra-53-crash-hardware-2026-10-21.md)
already documents flash-fetch/AHB stalls and why finite software READY polling
is not a physical latency bound. Consequently a logged2355→2856 tick interval
is not a measured 501 ms wall interval across this path.

This is a concrete observability/scheduling interaction, **not proof** that NVM
latency caused the freeze. The smallest useful timing result is a bound for
reset→first pin drive→UART-ready and terminal admission→PA23, including actual
flash programming. A zero-duration flash mock cannot supply it.

## 4. Earlier home faults explain focus unavailability, not all capture failures

The version history does not contain one demonstrated repeating root cause:

| Version | Established evidence |
| --- | --- |
|[3.6](../evidence/upstream-36-camera-failure-2026-10-15.md) |Sticky servo wrong-way inhibit; capture/shutdown failure reported; fault-time motion missing |
|[3.7 repeat](../evidence/upstream-37-repeat-camera-failure-2026-10-19.md) |AF confirmed; two files saved, battery-required freeze; home-failed, later event detail omitted for capacity |
|[3.8](../evidence/upstream-38-camera-failure-2026-10-20.md) |Home drive-phase failure; further photos blocked, normal shutdown |
|[3.9](../evidence/upstream-39-camera-failure-2026-10-20.md) |Home drive cap at 300 ticks, stillness age 20 versus required 40;17 later non-Stop requests consumed while inhibited; normal shutdown |
|[4.0](../evidence/upstream-40-camera-failure-2026-10-21.md) |Two files saved, battery-required crash; all 16 diagnostic pages erased |
|[4.1](../evidence/upstream-41-camera-failure-2026-10-21.md) |Delayed saved photo/freeze, shutdown worked; one shutdown cohort and later startup failure; tail full |

In current source, `main.c:830–854` leaves failed homing unready and motor
inhibition sticky. `home_service():859–870` refuses another failed-home attempt
but calls `home_command()` first, consuming later requests; readiness never
advances the main `step` to normal execution (`1888–1893`). `focus_exec():1567–1569`
also returns immediately when unready/inhibited. This supplies a source-level
explanation for AF commands ceasing to produce motion. It leaves a body-facing
failure/completion contract to establish: local safety requires no unsafe drive,
but successful local packet echoes do not prove the camera can finish its AF or
shutter decision. No invented success or error response is justified here.

AF-priority shutter blocking is a conditional hypothesis; focus mode/priority
were not confirmed for 3.8–4.1. A motion collector with no initialized servo move
does not prove absence of direct homing. Raw capture echo and shutdown TX return
prove local software progress, not saved-file attribution or body acceptance.

**Smallest next discriminator:** an original-stock instruction/caller probe for
the body-visible status and completion contract when reference acquisition
fails, alongside the actual custom main/home/protocol path. Only subsequently
matched external traffic can connect that contract to a particular shutter.

The [factory reconstruction status](../reverse-engineering/status-2026-10-15.md)
explicitly distinguishes selected original-instruction equivalence from complete
factory behavior and physical reference qualification. Tests of framing,
ownership, safety guards, CRC, recovery and mocked control trajectories can all
pass while those missing lifecycle/timing contracts remain wrong. AF 4.1 chiefly
improved crash observability; it did not implement an established capture-freeze
repair. Further firmware iteration needs a causal discriminator, not another
successful count of tests that exercise the same assumptions.
