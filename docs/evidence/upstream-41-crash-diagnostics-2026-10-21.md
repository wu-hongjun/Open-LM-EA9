# AF 4.1 — offline crash-persistence candidate

AF 4.1 for the original Contax Zeiss 50mm f/1.4 is prepared offline. It adds a
validated foreground checkpoint, watchdog/system-reset persistence and a crash
latch. **It has not been flashed or camera-tested.** The physical homing issue,
shutter freeze, exposure reliability, optical AF and factory parity remain
unresolved. All 151 historical release/recovery/pin artifacts and older diagnostic
registry entries, including original stock 1.8 recovery, remain unchanged.

[Sanitized acceptance receipt](upstream-41-crash-diagnostics-2026-10-21.json) ·
[Candidate](../../firmware/candidates/4.1.0/README.md) ·
[Preservation ledger](upstream-41-preserved-2026-10-21.json) ·
[Later owner-coordinated procedure](../upstream-crash-diagnostic-test.md).

## Why this candidate exists

The [4.0 camera failure](upstream-40-camera-failure-2026-10-21.md) saved two files,
then required battery removal. The owner reported AUTO; actual exposure dial,
focus mode and Pre-AF remain unverified. The subsequent authorized read-only backup
matched all pristine flash/protected data; every diagnostic byte was erased. This
is evidence of lost observability, not proof that a particular handler was never
entered or that no write was attempted. RAM events previously flushed only on
terminal shutdown/fault paths.

This milestone changes observability and fail-stop behavior rather than guessing
another capture/homing fix from an empty dump. It retains pinned upstream C
`d52ed06cc449918f938e0695fbf29a0c4141f2b2`, the 4.0 reference policy, aperture fields,
AF controller and capture/shutdown arbitration. No completion or readiness result
is fabricated. Fixed lens ID 234 and nominal AV 4352 remain; physical iris remains
unknown and runtime lens-library edits are unsupported by this image.

## Modular persistence and ownership

[Lane 52](../audits/astra-52-durable-crash-2026-10-21.md) owns a source-pinned
applicator and separate portable retained-checkpoint / target watchdog modules.
[Lane 53](../audits/astra-53-crash-hardware-2026-10-21.md) audits reset, NVM ownership,
original bootloader execution and exact ARM output.
[Lane 54](../audits/astra-54-crash-powerloss-2026-10-21.md) independently exercises
retained corruption, interrupted publication/programming and decoder semantics.
Root integrates their accepted inputs, version, registry, app and release evidence.

A 48-byte existing summary plus magic/CRC occupies 56 bytes at `0x20003fc0` in a
separate 64-byte NOLOAD region. App data/BSS/stack do not overlap it. A checkpoint
invalidates its marker, copies the summary under the existing short IRQ lock,
computes CRC after restoring IRQ state and commits its marker last. Only foreground
main/servo progress checkpoints; no ISR pets the watchdog. The checkpoint is an
earlier validated sample, not exact crash registers, PC/LR or a crash timestamp.
Motion/event arrays are not included. Live stage, frame counts/IDs, last-RX time,
capability and sticky fault can survive; UART byte/error/status, pins and
buffered/planned counts are populated at terminal flush and may be zero/stale.

The watchdog uses GCLK4 from OSCULP32K divided by 32, PER4K: nominally four seconds,
not a measured deadline. Disabled setup completes before the camera protocol;
arming follows protocol initialization and encoder-reference reads. Completed
foreground work can service it after 250 advancing SysTick ticks, skipping a busy
synchronizer. Legitimate long servo retargeting can continue servicing after bounded
iterations. There is no busy wait or flash write in health service. A naked HardFault
handler requests system reset with barriers, without trusting a damaged stack.
System reset is not unique evidence of HardFault.

At app main entry, `st_crash_boot` releases the motor GPIOs before other app
initialization. The original bootloader and app runtime initialization execute
earlier; a failure there can prevent this cutoff. WDT bus access is enabled explicitly;
ALWAYSON is rejected and startup synchronization waits are bounded. The watchdog
is disabled before one boot-time append. Exact WDT or SYST cause plus valid retained
magic/CRC permits a type 5 recovered-summary page; other causes discard retained
RAM and append a zero-payload baseline/cause-only page. A boot page consumes one of
the finite 16 slots and has a standalone append cohort. Normal terminal summaries
start their own cohort. Nothing wraps, erases, overwrites an occupied page or
retries a failed append in the same boot.

A recognized crash page or any non-erased bad-CRC page latches later boots before
normal board, motor and camera-protocol initialization. Current crash causes also
stop even if retained RAM is invalid. Full storage, failed reads or failed append
fail closed. A prior latch is consumed without another write, preventing repeated
crash re-homing or flash exhaustion. CRC-valid foreign pages occupy storage but
are not themselves the firmware's storage latch; the decoder now mirrors that
exact predicate. This distinction was found in the independent integration review
and has differential C/decoder coverage.

Existing `powerdown_signal`/`st_fail` terminal flash paths remain. New crash records
write only before protocol activation; health, checkpoint, interrupts and HardFault
cannot reach NVM. Single-bank flash stalls make unreviewed active-session writes
unsuitable. Once a page reaches flash it survives battery removal; durability of
an interrupted hardware write remains unqualified.

## Original factory boot findings and limits

The stock bootloader receives hardware resets before the app. A NOLOAD section
alone would not protect SRAM from its CRT or stack. Lane 53 replays the original
instructions through the normal PA23-low handoff using two synthetic calibration
fixtures. Each makes 1,170 SRAM writes below exclusive address `0x20001690`, leaving
the top 128-byte sentinel and supplied WDT RCAUSE untouched; APBA/APBB masks remain
`0x7f`. This bounded path supports the chosen retained region. It does not cover
all USB branches, interrupts, DMA, power, timing or failed readiness paths. PA23-high
can stay in the USB bootloader and never reach app persistence.

Physical SRAM retention across reset, oscillator timing and power-fail NVM behavior
remain untested. Removing the battery before reset/append can lose the checkpoint.
A failed append that leaves a fully erased page leaves no durable latch. A body-only
protocol stall while the firmware health loop continues will not trip this watchdog.
A baseline proves boot reached its append, not that capture, focus or shutdown worked.
A post-shutdown terminal loop that stays powered may also trigger WDT; interpreting
that reset requires the earlier terminal breadcrumbs. These are explicit coverage
limits, not a promise that the next physical freeze will always leave a checkpoint.

## Exact build, tests and host integration

The [builder](../../scripts/build-upstream-crash.py) verifies the frozen 4.0 full
image/manifest, 49 sources, shim and prior patch, then accepted applicator/input
pins. Version advances to 4.1, including camera BCD `0x41`. Two fresh builds match
image, complete manifest, all sources, patch and shim byte for byte. Code/data end
is 39,412 (`0x99f4`), with 524 bytes before the unchanged 1K tail, exceeding the 256-byte
floor. Ordinary static RAM is 3,048 plus 56 retained; stack reserve remains 8,192.
The only new optimization flag is `servo -Os`; target source and ordering remain
bound by exact disassembly and production-path regression checks.

The compiled audit binds the image, source, stack-use files, all 12 indirect call
sites and reviewed library frames. Its conservative all-vector stack estimate is
1,588 bytes under the stated architectural/ABI assumptions, not a measured high-water
mark. There are no unresolved compiled edges or recursive components. It checks
the exact HardFault vector/stackless handler, NOBITS reservation, motor-first reset
sequence, foreground-only health, inherited callback offsets and NVM callers; four
negative policies are rejected. Repeat-build container rebinding accepts only
identical normalized instructions/symbols/sections and the exact noncontainer pins.

The final acceptance master passes **40 suite groups**, including **681 new decoder
checks**, six power-loss mutants, three watchdog mutants and three acceptance
identity guards. It retains historical parser, ownership, timing, homing,
readiness, ADC-independence, capture/shutdown, trace, packet-reset, factory-instruction,
compiled-writer and decoder suites alongside new crash/health/power-loss checks.
Historical host peripheral/health mocks are explicitly test-only; actual watchdog C
runs separately against inert registers and exact target instructions are audited.
Original runners/pins and historical receipts remain unchanged. New decoder records
are version-gated; earlier decoders reject type 5. Recovered records cannot assemble
ordinary event/motion snapshots or manufacture shutdown evidence. See the JSON
receipt for final suite counts and bound private receipt digests.

App 0.24.0/build 33 adds `autofocusCrashDiagnostic`, explicit
`prepare-crash-upstream` / `apply-crash-upstream`, resource/trust pins and installed 4.1
USB-tool routing. Ordinary4.0 installation stays held, including from other versions.
All 53 named Swift tests pass; existing full-image, profile-rejection, backup/journal,
physical-reconnect and strict tail verification checks include the new variant.
The signed app/CLI package verifies without launch. Native preparation with fresh
private state/output returns before inventory and matches the published 20,480-byte
image. The prior signed 0.23.1/build 32 app, CLI and bundles are preserved privately.

No adapter enumeration/open, USB/HID exchange, flash, motor drive, updater/app launch,
canonical Application Support access or new camera trial occurred during this task.
Raw backups, keys, unit identifiers and real camera frames stay private. The adapter's
last verified installed image remains held 4.0. A later separately authorized upload,
physical reconnect, strict full-image/protected-data verification and one controlled
camera cycle remain required. No stock restoration was performed.
