# Astra 57 — why passing firmware tests did not establish camera reliability

Audit date: 2026-10-23. Reference checkout: `bd2ad4a`. Frozen source:
`artifacts/private/crash41-final`; image SHA256
`fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641`.
Hardware remained offline. No enumeration, HID, flash, motors, app/updater launch,
or canonical Application Support access. Original stock 1.8 remains restored and
verified. No new camera trial is proposed by this audit.

The test results are mostly true statements about narrower questions than the
user's requirement. They establish image identity, memory safety under supplied
inputs, selected protocol transitions, and diagnostic integrity. They do not
establish that this A7C II can repeatedly capture and shut down. More tests of
those narrow questions cannot compensate for a missing lifecycle oracle. The
release receipt itself is candid: `cameraQualified=false`,
`physicalHomingFailureFixed=false`, `cameraFreezeFixEstablished=false`
(`scripts/test-upstream-crash.py:185`). The process failure was continuing to
accumulate component confidence while the device-level success condition remained
unproven; it is not evidence that all existing tests are worthless or fabricated.

## 1. Proven test defect: the composed replay opens a gate independently of production

**Priority: P1 for the prospective validation gate.**
`firmware/upstream-hardening/followup/50-readiness-capture/run.py:32` extracts
constants and then unconditionally emits `#define HOME_GATE_OPEN() 1`. The real
conditional block is at frozen `src/main.c:286`, and the real foreground checks
that gate at `src/main.c:1889`. The extractor therefore tests a different startup
condition, despite using the real foreground/home/servo functions elsewhere.

A private mutation-sensitivity experiment changed only the production zero-delay
branch from gate `1` to gate `0`. The historical composed runner still exited 0,
including its existing negative controls. The production foreground with this
mutation could never start home service. Preserving the closed gate in the host
fixture instead failed the intended `g_homed && g_home_state==HOME_READY &&
!inhibited` assertion (`test_composed.c:113`, process exit -6). This demonstrates
an actual sensitivity gap, not a hand-written simulation of the desired answer.

The original experiment remains private. The checked-in regression now also
reproduces the historical false green and the corrected rejection:

```sh
python3 firmware/upstream-hardening/followup/57-validation-gap/test.py \
  --output artifacts/private/astra57-fresh-validation
```

The script uses an explicitly modified private source manifest so the component
runner accepts the mutated source tree. Its binary is **not rebuilt**. It neither
passes nor attempts the final 4.1 master: that master's exact image/source pins
would reject the mutant. This distinction matters: pins prevent accidental
substitution of a released artifact, but they do not establish that a behavioral
test can reject an intentionally wrong implementation.

A prospective correction is in
[`followup/57-validation-gap/run.py`](../../firmware/upstream-hardening/followup/57-validation-gap/run.py).
It hash-binds the historical runner and compatibility inputs, replaces only the
constants extraction, and retains the entire source `HOME_DELAY_MS` / `#if` /
multiline `HOME_GATE_OPEN` / `#else` block. The frozen runner, 4.1 master, pins and
image remain unchanged. Its regression requires the exact 4.1 baseline to pass,
the closed-gate source mutant to fail readiness, and compiled/preprocessed delay
0 and delay 25 behavior to respect thresholds and unsigned wraparound. The
[sanitized receipt](../../firmware/upstream-hardening/followup/57-validation-gap/results.json)
contains script/source hashes. Adoption into a future master is still required;
it does not retroactively strengthen historical receipts.

## 2. Proven composition gap: “shutdown live” stops at a local send

**Priority: P1.** The most relevant composed fixture does exercise actual home,
focus-entry, servo, ownership, and protocol C together. It is not merely a set of
unrelated unit tests. But `50-readiness-capture/test_composed.c:89` calls protocol
initialization directly, and line 90 registers only the motion-inhibit callback.
It never registers the production `powerdown_signal`. Its shutdown assertions
at lines 101, 111 and 126 inspect `wire_shutdown`/local acknowledgment. Thus that
“shutdown” path can pass without UART disable, flash, VD wait, PA23, or physical
power removal having happened.

The separate terminal test extracts `powerdown_signal`
(`44-shutdown-liveness/run.py:41`) but replaces `st_flush` and `st_terminal` with
zero-time assertions (`35-targeted-trace/test_tail.inc:28`). It supplies its own
clock, pins and delay (`:21`). Actual production flush is before the VD timer
starts, and a footer append is before PA23 (`src/main.c:964`, `:969`, `:978`). The
500-tick loop bound therefore is not a measured bound from shutdown request to
PA23 or power loss. Actual NVM wait/write logic lives in
`src/startup_trace_flash.c:16`; it is not running in that tail test.

The watchdog suite separately uses inert registers and mocked `st_init`,
`st_boot_record`, and `st_checkpoint`
(`52-durable-crash/test_watchdog.c:30`). It tests clear guards at selected times
(`:57`), not an autonomous clock expiring during the real shutdown callback.
Historical replays additionally receive weak no-op `st_health`
(`next41/trace_compat.c:27`). These are legitimate local boundaries, but separate
passes cannot establish their timed composition.

Required next test: execute the production initialization/callback registration,
owner dispatch, terminal callback, trace writer and watchdog under one explicit
event schedule. Include no-power-cut after PA23, finite flash latency, unavailable
flash, delayed VD transitions, reset during append, and a full tail. Assert the
externally required state as well as local TX. Keep latency assumptions visible;
without measured hardware bounds, report schedule coverage rather than a proven
real-time guarantee. A missing callback registration, zeroed watchdog service,
and deliberately delayed append should each have an appropriate failing control.

## 3. Supplied scheduling can hide the interaction being investigated

**Priority: P1 for timing claims.** Lane50 adds a clock increment inside the
extracted `pump` (`run.py:39`), drives asynchronous input from calls to `millis`
(`:53`), and supplies an idealized encoder trajectory
(`test_composed.c:51`). The frozen host shim makes UART send a memory copy that
returns success (`tools/hosttest/shim.c:96`), normally supplies CS levels `{1,0}`
(`:128`), and advances startup time when a pin is polled (`:160`). It does not
produce a body acknowledgment, UART bit time, or independent IRQ schedule.

The contract adapters also inject the historical scheduler at pump exit
(`next41/contract_adapters.py:63`). Some assertions change with the intended
query contract (`:27`, `:46`), including removal of intermediate query-count
assertions and addition of a later explicit pump/VD check. Those edits are
reviewable and often justified; a historical fixture hash alone does not mean
the old behavioral contract still ran unchanged. Packet initialization is supplied
by a host initializer because these tests skip Reset_Handler
(`next41/compiler_compat.py:22`).

Required correction: produce a machine-readable list of substituted functions,
inserted scheduling points and changed assertions for every suite. Add event
schedules independent of `millis`/pin reads and cover preemption at the state
publication boundaries. Preserve a minimal whole-startup replay so boot, packet
initialization, CS/VD timing, home gate and callback registration cannot disappear
through extraction. Exact compiled instruction checks remain useful, but they do
not supply the missing external schedule.

## 4. Diagnostics changed the operating lifecycle, not only observability

**Priority: P1.** 4.0 could lose all RAM evidence on battery removal because only
terminal paths flushed. 4.1 adds pre-protocol boot appends, watchdog/reset behavior
and a persistent storage/crash latch. In production, `st_crash_boot` halts when
`st_boot_record` returns true (`src/startup_trace_flash.c:74`). A full diagnostic
tail is therefore an availability condition. The recorded 4.1 tail is full.
Astra55's independent exact-C experiment proves that even clean POR records
consume the capacity and eventually inhibit startup; see
[the causality audit](astra-55-failure-causality-2026-10-23.md).

The powerloss suite deliberately expects full-storage fail-stop
(`54-crash-powerloss/test_powerloss.c`, full-tail/frontier cases). That test can
pass while the product becomes unusable after storage fills. The unresolved
question is the product policy, not whether this implementation follows it.
A future gate must specify clean-cycle availability separately from durable crash
latching, including USB-cap boots and initialization failures. Do not conflate a
successful safety stop with a successful capture lifecycle. These facts do not
identify exhaustion as the cause of the first reported one-minute shutter delay.

## 5. There is still no controlled end-to-end A7C II baseline in this evidence

**Priority: P1 for another release claim.** The failures differ: 3.1 reported no
shutter/motor and missing aperture with normal shutdown; 3.8 reported a reset and
blocked later photos with normal shutdown; 4.0 saved two photos then required
battery removal; 4.1 saved a delayed photo and subsequently shut down. Collapsing
these into one repeated crash mechanism discards evidence. The 4.1 final startup
CS-rise timeout is real, but belongs to a boot cohort that cannot be assigned to
the earlier shutter press.

The receipts consistently distinguish requested MF/Pre-AF/exposure settings from
observed settings. The current two-step procedure already requires actual MF and
preview confirmation before asking for the photo
(`docs/upstream-crash-diagnostic-test.md:42`). Yet the resulting 4.1 trial happened
before those settings were confirmed. Repeating that written instruction alone
would not improve the evidentiary gate. This is a workflow design issue, not a
reason to blame the owner or relabel unknown settings as known.

Before any separately authorized future trial, prepare one short observation
record: exact firmware identity, confirmed focus/exposure/Pre-AF state, preview and
aperture, shutter action and elapsed wall time, saved-file status, shutdown and
restart outcome, and diagnostic capacity. Record unknowns as unknown and stop the
comparison there. Establish a known-good same-body configuration or explicitly
state that none exists. Do not reuse upstream a9 II success or original-stock
instruction replays as A7C II qualification. The present audit authorizes no trial.

## Release decision correction

Keep existing integrity/recovery checks, but give their receipts their actual
scope. “40 groups / 681 decoder checks / 53 Swift tests” is not a reliability
percentage or 734 camera scenarios. The decoder bit/corruption matrices and app
installation tests protect different properties. Require separate outcomes for
artifact integrity, substituted host behavior, timed composition, diagnostic
availability, and observed camera lifecycle. A diagnostic experiment must declare
what it can discriminate and its storage budget; it must not inherit “fix” status
from a larger green count. Ordinary release remains blocked by the failed camera
outcomes. Nothing here proves a new hardware root cause or makes 4.1 safe to retry.
