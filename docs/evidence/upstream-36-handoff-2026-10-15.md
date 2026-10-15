# Upstream C 3.6 — startup ownership and diagnostic interpretation

**Prepared offline; not uploaded or camera-qualified.** The new candidate fixes
a reproduced startup producer race. A separate host-only decoder change stops
CRC-valid, writer-impossible page layouts from falsely completing a diagnostic
snapshot. [Machine-readable evidence](upstream-36-handoff-2026-10-15.json) binds
the image, sources, tests and host integration. [Campaign](../audits/astra-hardening-campaign-2026-10-15.md).

## Startup finding and accepted design

Frozen 3.5 enables EIC delivery before calling its falling-edge receive path
directly in foreground to rescue the first window. The real EIC producer can
interrupt that synthetic producer. Root reproduces a mixed checksum-invalid
request and double session advancement; independent review reproduces buffer
corruption with a **single rising EIC interrupt** using actual UART reset/ISR
and EIC handler source.

The initial global interrupt mask is **rejected**. It serializes the producer
but can postpone a final UART byte until after rescue has rejected the frame.
The accepted modular boundary prepares EIC with only its NVIC delivery disabled,
rescues/resets the first window, then calls `em_eic_start`. UART/SysTick remain
live, PRIMASK is unchanged and pending EIC state is not cleared at start.
[Root reproduction and fitting](../audits/root-26-startup-handoff-2026-10-15.md) ·
[Independent review](../audits/astra-28-startup-handoff-review-2026-10-15.md).

Review 28 passes **287 asserted sanitizer cases**, including **41 against exact
final 3.6 source**, frozen failures, the late-byte counterexample and three
placement controls. Root's 20 variant/cut outcomes and complete trace/wire
comparisons independently support producer serialization and the fitting change.
The interrupted Astra26 turn is not counted as a completed Astra audit; root
continued it and Astra28 reviewed the result.

## Frozen image and exact verification

[3.6](../../firmware/candidates/3.6.0/README.md), SHA-256
`d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`,
is 20,480 bytes. Its manifest SHA-256 is
`ea2511bbdd7a833095df5b613579d0b69083efe3a44d26078d07efa8d51eccae`.
Two fresh builds reproduce image, manifest and full delta patch exactly.
Only EIC C/header and protocol C/version header change from 3.5. Controller,
gains, maps, sensor/motor drivers, wait budgets and aperture policy stay intact.

To retain the 256-byte release floor, two RAM snapshots of the RX counter are
omitted under `EA9_NO_LOG`. Their only readers are excluded legacy logging pages.
The live counter, MMIO and current diagnostics remain. ARM preprocessing checks
all 22 release units; logging-enabled tokens are identical and release tokens
change only by removing those assignments. Exact synthetic trace/wire bytes
match with and without the omissions. The final code/data end is **0x9af4**:
**268 bytes before unchanged logs**, **3,064 static RAM bytes**, **8,192 stack
bytes**. The scoped composition with only one omission leaves 252 and is rejected.

The [compiled audit](../audits/astra-29-stack36-2026-10-15.md) validates 46 sources,
134 compiler records, 139 linked functions, 463 call sites and 14 indirect sites.
All 133 prior compiler frame sizes remain; new `em_eic_start` has a zero-byte
frame. The conditional all-vector envelope is **1,560 bytes**. Twenty-nine
negative evidence controls reject and the exact-budget positive passes.
Compiled ordering guards enforce IRQ4 disable/barriers before callback setup,
rescue/reset before enable, and no new global mask. The fresh-build check rebinds
only ELF/map containers after exact executable and normalized compiled-metadata
equality; callback, library, vector and physical-entry conditions remain enforced.

The [unified runner](../../scripts/test-upstream-handoff.py) passes on the fresh
repeat build: retained capture/shutdown/query/home/numeric/target/time and caller
regressions, exact startup review, snapshot consumers, stack/order guards, nine
compiled ARM writer cases, 49 decoder boundary cases and actual 3.2–3.6 prefix
acceptance/rejection. Seven regression templates are reused with hash-bound
private metadata/host-ABI adaptations; cases and expected outcomes are unchanged.
The [workbench](../../firmware/upstream-hardening/next36/README.md) records reproduction.

All **53 Swift tests** pass. Signed **app 0.19/build 23** and CLI package; isolated
native preparation matches 3.6 and all six earlier explicit command images, and
rejects the incompatible 85mm profile without output. Full-image blank-tail and
protected-data verification/reconnect guards are unchanged. All
[60 earlier release/recovery/pin artifacts](upstream-36-preserved-2026-10-15.json)
and historical diagnostic registry entries remain exact.

## Decoder, boot and peripheral evidence

[Audit 25](../audits/astra-25-diagnostic-cohorts-2026-10-15.md) reproduces false
completeness when event pages are moved outside their summary's serialized slots
or borrowed across boot cohorts, with CRCs recomputed. The host-only semantic
module checks writer invariants and distinguishes complete, partial, inconsistent
and unassociated evidence. Valid partial summaries and v1 repeated flushes remain
usable. CRC is not authentication; structural `state: valid` is distinct from
`recordTrust`. Installation verification and camera acceptance remain false.

Root reproduces 448 production-serializer histories, 896 version decodes,
19 frozen semantic controls, 1,827 mutation decodes, six repeated v1 summaries,
two source-pin controls and the existing 25+37 decoder suites. The shared module
is byte-identical to the audited proposal; the final registry additionally
supports independently pinned 3.6. Staged test dependency lists tolerate replay
after integration, and their unknown-version control advances to 3.7. No firmware
image is changed by the decoder fix.

[Audit 24](../audits/astra-24-boot-entry-2026-10-15.md) executes the original
reset-to-application path with explicit inert MMIO and no asynchronous exceptions.
It preserves CONTROL/PRIMASK/priorities, leaves NVM IRQ5 enabled with modeled
reset peripheral INTEN zero, and starts SysTick without TICKINT. Eight path/state
cases, two initializer fixtures and nine negative controls pass. This refines
ordinary-reset assumptions; it justifies no speculative boot rewrite or physical
handoff claim. [Root audit 27](../audits/root-27-peripheral-bounds-2026-10-15.md)
separately verifies eight compiled stuck-peripheral paths and three ready paths
on **3.5**, including emergency GPIO before logging, plus a guard-removed control.
Those iteration bounds are not measured electrical deadlines.

## Remaining gates

EIC edges may coalesce, and receive-boundary loss/duplicate parsing remains
conditional on peripheral ordering. The handoff gate is not a complete UART/EIC
or factory scheduler reconstruction. Source tests do not establish the cause of
past A7C II freezes. Physical timing, stack high-water, infinity calibration,
exposure, capture/shutdown and optical AF remain unverified. Factory reconstruction
is [partial](../reverse-engineering/status-2026-10-15.md); current control is upstream
C. Actual iris remains Unknown, with the original fixed nominal 50mm f/1.4 profile.

No hardware enumeration/open/report/updater/flash/motor action, app launch or
canonical state mutation occurred. Uploaded 3.2 still awaits owner-confirmed
physical reconnect and strict verification. The pending journal is unchanged;
3.6 is offline only. Resolve the existing transaction normally before any separate
authorized installation using the [future procedure](../upstream-handoff-test.md).
