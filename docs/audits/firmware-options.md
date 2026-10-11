# LM-EA9 embedded firmware options audit

Research date: October 10, 2026. This is an independent recommendation, not an
approved stack selection. The [product direction](../product-direction.md)
requires a modular firmware, a documented management protocol, and a polished
macOS app. Language uniformity is not a product requirement.

## Recommendation

**Shortlist Rust `no_std` and disciplined C for the production firmware. Give
Rust the first feasibility prototype, with C as an explicit fallback.** In
either language, use a small interrupt-driven system with bounded state-machine
steps and static storage. Preserve the original bootloader during initial
development. Do not begin by introducing a general-purpose RTOS or replacing
the bootloader.

Rust is attractive for a comprehensive firmware because ownership, bounded
slices, enums, and explicit error handling can make the parser, configuration,
and motion-state boundaries easier to maintain. It does not improve autofocus
by itself. Its cost is rebuilding the adapter-specific hardware layer and
proving its timing. C has the strongest existing hardware evidence: the
only collected implementation tested on an actual EA9 is C, reportedly with
an a9 II. That is a decisive fallback advantage, not evidence of A7C II support.

Use the C reference as a behavioral oracle and bench baseline. A Rust candidate
should initially replace one concern at a time in experiments or reproduce
the same bounded interfaces. Long-term production need not retain C solely
because the reference uses it. Firmware, desktop UI, and research tooling can
choose their own languages.

This ranking is engineering judgment from the evidence below. No ARM build,
adapter flashing, runtime timing measurement, board inspection, or A7C II test
was performed for this audit. Driver documentation establishes feasibility,
not a validated working adapter.

## Actual constraints and corrections

The pinned implementation targets SAMD21E17A, 48 MHz Cortex-M0+, 128 KiB flash,
16 KiB SRAM, with an application linked at `0x5000`. That leaves **108 KiB**
above the 20 KiB bootloader before reserving configuration and diagnostics.
Do not copy a common SAMD21E18 development-board memory map. The local image
and vectors are consistent with this target, but this user's physical board,
fuses, and bootloader remain to be independently verified. See the
[pinned linker](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/ea9.ld)
and [Microchip device documentation](https://www.microchip.com/en-us/product/ATSAMD21E17).

The original application snapshot is 20,172 bytes. Its size is encouraging
but does not predict the size of a comprehensive replacement containing USB,
configuration transactions, motion control, and diagnostics.

| Constraint | Consequence for the design |
| --- | --- |
| 750 kbaud UART reference transport | An 8N1 byte takes about 13.33 μs, or 640 CPU cycles at 48 MHz. Masking UART service or executing long interrupt work must be measured against that budget. |
| CS-window and frame-sync edges | Treat transfer windows and declared frame length as separate objects. Timestamp and validate before dispatching commands. |
| Observed longest frame 210 bytes | Provides a starting buffer size; it is not proof of the maximum possible A7C II frame. Bound buffers and reject unsupported lengths with diagnostics. |
| Reference servo updates every 5 ms | Start from this behavior, then select the production period through actuator and load measurements. A 5 ms period is not evidence of 5 ms worst-case execution. |
| 16 KiB SRAM | No general heap, recursion, unbounded queues, or large text logs in the device. Inspect the linked image and worst-case nested stack usage. |
| Cortex-M0+ has no FPU | Prefer integer/fixed-point motor arithmetic. Precompute optical or distance tables where useful; measure any necessary software floating-point operations. |
| Single flash array and finite erase endurance | Buffer normal telemetry in RAM. Persist settings and evidence in controlled maintenance windows, with validated power-loss behavior. |

The pinned UART implementation uses RX interrupts and blocking TX, while its
comments describe stock DMA. Its actual ISR performs more than the comment's
"two-instruction" shorthand: it drains bytes, updates counters, and records
errors. Treat headroom as an experiment, not a proof. A 210-byte TX consumes
2.8 ms at 750 kbaud; recurring 105- and 48-byte transmissions consume 1.4 ms
and 0.64 ms. Those wire times explain why polling can perturb the motor loop.
See [em_uart.c](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/em_uart.c).

**Correction to earlier research:** the pinned replacement's millisecond clock
is **SysTick**, implemented in `delay.c`. TC4 appears in recovered-stock
commentary, including one-shot protocol gaps that the replacement implements
with busy waits. There is no configured TC4 millisecond tick in this snapshot.
See [delay.c](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/delay.c)
and [emount.c](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/emount.c).

## Language options

| Option | Advantages | Costs and conditions | Assessment |
| --- | --- | --- | --- |
| C with CMSIS/vendor device headers and a small board layer | Closest to working EA9 code, direct register control, straightforward ARM GCC and host testing | Bounds, ownership, interrupt handoffs, and error-state invariants require discipline and review; existing parser must be hardened | Strong production choice and best fallback |
| Embedded C++ with restrained language features | RAII, typed units, bounded containers and explicit interfaces; can retain C drivers | Disable exceptions/RTTI if unused, avoid heap-backed STL, inspect templates and global initialization; less automatic memory safety than Rust | Viable if team expertise strongly favors it; modest benefit over C migration here |
| Rust `no_std` with `cortex-m-rt`, `atsamd-hal`/PAC and static state | Safe parser/configuration code, ownership of peripherals, state models, host-testable core, Cargo dependency pinning | Adapter-specific startup/clocks/pins still need implementation; register access and ISR/DMA boundaries need audited `unsafe`; complete memory and timing unproven | Preferred candidate to prototype |
| Rust logic plus C board/USB code | Can preserve proven drivers while introducing safe high-level components | Two toolchains, linker/startup ownership, FFI types/lifetimes and duplicated synchronization rules; faults can cross boundaries | Useful temporary bridge or narrowly justified permanent driver boundary |
| Arduino framework plus C++ sketch | Rapid development-board prototypes, existing historical E-mount example | LexOptical targets Teensy/NEX7 manual-lens emulation, not EA9 motion; generic startup, clocks, pins and interrupt behavior must be replaced or audited | Research/prototyping aid, weak default for final EA9 firmware |
| MicroPython/CircuitPython, JavaScript, or other managed runtime | Interactive experimentation | Runtime/heap footprint, garbage collection and timing assurance conflict with this device's small memory and fast camera link | Do not shortlist for production |
| Zig or another native systems language | Potentially small native output and explicit memory use | No collected EA9 implementation or demonstrated matching driver/tooling stack; would add ecosystem qualification work | Revisit only with a concrete advantage, not to expand an unbounded comparison |

Arm's supported GNU toolchain provides C/C++ Cortex-M builds; its publication
location has changed, so pin an exact release and checksum rather than relying
on an old download URL. Arm also publishes a Clang-based embedded toolchain
with a macOS universal package. Keeping GCC for the C baseline avoids changing
compiler and architecture simultaneously. See
[Arm GNU Toolchain](https://developer.arm.com/Tools%20and%20Software/GNU%20Toolchain)
and [Arm Toolchain for Embedded installation](https://learn.arm.com/install-guides/llvm-embedded/).

Rust's `thumbv6m-none-eabi` is an official Tier 2 bare-metal target supporting
`core`/`alloc` and Cortex-M0+, with soft-float ABI. `alloc` support is not a
reason to add a heap to this design. See the
[rustc target documentation](https://doc.rust-lang.org/rustc/platform-support/thumbv6m-none-eabi.html).

The current atsamd-rs project supplies a `samd21e` PAC/HAL variant and optional
USB, DMA, and async APIs; its documented async peripherals include UART, SPI,
EIC, timers and ADC. It expects the application to choose an executor. Thus
"SAMD21 has no Rust HAL" and "Embassy cannot be used on SAMD21" are not valid
rejection arguments. Exact clocks, PA00/PA01 UART muxes, simultaneous PWM
channels, encoder protocol and USB-cap behavior still require a device
prototype. The Git master package and docs.rs pages retrieved during this
audit showed different version numbers; pin one tested release/revision and
its dependency lockfile instead of combining snippets across versions. See
[atsamd-rs](https://github.com/atsamd-rs/atsamd),
[HAL device list](https://github.com/atsamd-rs/atsamd/tree/master/hal), and
[USB API](https://docs.rs/atsamd-hal/latest/atsamd_hal/usb/index.html).

One concrete memory issue: the HAL's inspected package configuration defaults
USB endpoint storage to 2 KiB and offers a 1 KiB option. This is 12.5% or 6.25%
of the entire SRAM before descriptors, application buffers and stack. Select
only necessary endpoints/features and measure actual allocation. See
[HAL Cargo configuration](https://raw.githubusercontent.com/atsamd-rs/atsamd/master/hal/Cargo.toml).

For C/C++, TinyUSB supports SAMD21 and HID/CDC without requiring an RTOS. Its
static buffers and deferred interrupt processing are useful candidates for a
future application management service. It does not establish that the stock
bootloader will start that service through the USB cap. See
[TinyUSB](https://github.com/hathach/tinyusb).

## Scheduling options

**Default recommendation: short peripheral interrupts, a fixed-period motion
step, and a cooperative event dispatcher.** Camera receive/CS capture must
complete promptly; motion supervision must not wait behind USB or flash work.
Do not equate an event-driven architecture with a monolithic `while` loop.
Each subsystem owns state and processes bounded events, with explicit
deadlines and bounded mailboxes.

| Runtime | Fit for this device | Recommendation |
| --- | --- | --- |
| Bare metal with static state machines | Small footprint, clear scheduling, maps to collected hardware behavior | First candidate in C or Rust |
| RTIC | Rust framework with priorities/shared-resource rules; explicitly supports M0/M0+ using source masking because ARMv6-M lacks BASEPRI | Good optional structure if concurrency warrants it; verify lock duration and use external timer IRQs for shared tasks |
| Embassy executor with atsamd-hal | Static async tasks can simplify USB/background operations without heap or a thread stack per task | Viable alternative; keep hard deadlines in hardware interrupts or a measured interrupt executor, bound each future's polling work |
| FreeRTOS with static allocation | Mature Cortex-M0 kernel; can be used without dynamic allocation | Feasible, not ruled out by 16 KiB; separate task stacks and synchronization add qualification work without an established requirement |
| Zephyr | SAMD21 drivers/build integration and many product services | Lower priority: matching board/memory adaptation and tuning must earn their complexity; a 256/32 KiB Arduino Zero example is not proof of fit on this 128/16 KiB adapter |

RTIC's source-masking critical sections can defer the UART if it shares a
locked resource. Its documentation also prohibits ARMv6-M exception handlers
such as SysTick/PendSV from sharing resources in the same way as maskable IRQ
tasks. This affects timer choice; it is not a lack of M0+ support. See
[RTIC target architectures](https://rtic.rs/2/book/en/internals/targets.html).
Embassy allocates task futures statically and supports Cortex-M executors;
compile-time RAM fit does not prove a runtime deadline. See
[Embassy executor](https://docs.embassy.dev/embassy-executor/git/cortex-m/index.html).

FreeRTOS has static object creation and a modern MIT-licensed kernel. See
[static allocation](https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/09-Memory-management/03-Static-vs-Dynamic-memory-allocation)
and [license](https://www.freertos.org/libraries/license.html).
Zephyr explicitly recommends tuning generous thread-stack defaults; its
Arduino Zero target has twice this adapter's memory. See
[footprint guidance](https://docs.zephyrproject.org/latest/develop/optimizations/footprint.html)
and [SAMD21 Arduino Zero target](https://docs.zephyrproject.org/latest/boards/arduino/zero/doc/index.html).

## Recommended firmware boundaries

| Component | Owned state and contract |
| --- | --- |
| Board package | Only owner of pins, clocks, interrupt registration, UART/SPI/PWM/ADC/NVM registers and reset entry assumptions |
| Camera transport | Timestamped CS windows, bounded RX buffers, explicit overflow/error state, TX completion and timed CS release |
| Frame codec | Validates `9 <= length <= captured bytes <= buffer capacity`, terminator and additive checksum; separates tail bytes; no register access |
| Camera session | Initialization/negotiation, supported capability/command semantics, sequence handling, typed requests and completion events |
| Motion axis | Homing/reference state, position/velocity estimation, bounded trajectories, arrival, abort, retargeting and physical guards |
| Device calibration | Travel limits, encoder polarity/scale, backlash/friction and hardware-specific limits, independently versioned from lens metadata |
| Lens profiles | Nominal metadata, explicitly selected zoom/aperture/prefocus settings, optical calibration provenance and supported confidence levels |
| Lifecycle supervisor | Power/mode transitions, command admission, fault latching, safe startup, parking, watchdog and reconnect behavior |
| Management service | Capability discovery, versioned commands, settings transactions and telemetry, separate from Sony's E-mount codec |
| Persistence | Fixed partitions, validated records, generations/CRC, power-loss handling and erase policy; no arbitrary-address host writer |
| Diagnostics | Bounded counters and compact RAM trace, fault context and explicit maintenance export |

Keep motors under one motion owner. Camera or host commands produce bounded
requests; they never directly select PWM. Apply an active profile as one
validated snapshot at a defined session transition, so different replies
cannot describe different lenses. Report movement completion only when the
motion state and protocol semantics agree. Unknown or malformed camera records
must not become motion commands, and unknown-size records cannot be skipped
by guessing.

Begin with interrupt RX and measured bounded parsing. DMA is an optimization
option, not a requirement or automatic improvement. It becomes valuable if
USB work, faster camera negotiation, or TX polling makes the measured budget
fail. If used, make DMA buffer ownership and CS-edge finalization explicit;
DMA-complete alone does not mean the UART's last stop bit has left the pin.

The release fault path must disable drive and reset or recover predictably.
A `panic-halt` or endless C default-handler loop is unsuitable while PWM can
remain active. Use a board-validated drive-off action, a supervisory watchdog,
safe reset pin states and a bounded fault record. Fault handling should not
attempt a blocking flash erase while the camera or motor is active.

## Flash, configuration, and updates

The reference reserves no linker range for its diagnostics starting at
`0x16000`; application growth can collide with them. It also writes warm-reset
counters at hard-coded SRAM addresses near the RAM end. Production needs
linker-owned partitions, assertions, and a declared `.noinit` region rather
than addresses assumed to remain unused. See
[diag.c](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/diag.c).

An **illustrative budget**, to revise after bootloader and profile-size tests:

| Region | Candidate address range | Size |
| --- | --- | ---: |
| Stock bootloader | `0x00000–0x05000` | 20 KiB |
| Application | `0x05000–0x1A000` | 84 KiB |
| Configuration bank A | `0x1A000–0x1B000` | 4 KiB |
| Configuration bank B | `0x1B000–0x1C000` | 4 KiB |
| Explicit maintenance diagnostics | `0x1C000–0x1E000` | 8 KiB |
| Growth/format reserve | `0x1E000–0x20000` | 8 KiB |

Ranges are half-open. These addresses are **not yet an upload specification**:
the stock loader may erase or pad across reserved areas. A sequential firmware
update can destroy configuration unless tests establish preservation or the
app backs it up and restores it through a supported service. Two configuration
banks provide transactional settings, not two bootable firmware slots. Do not
promise automatic firmware rollback with this bootloader and memory map.

Store only compact device-needed profiles and active calibration. Keep the
larger lens library, rich names, history, and research traces on the Mac.
Write the inactive bank, verify it, and commit a generation/validity record
last; startup selects the latest complete valid generation or defaults. CRC
detects corruption but is not authentication. Design row/page boundaries and
the commit sequence against the actual NVM parameters, then cut power at each
write boundary in controlled tests. Microchip documents four pages per row,
erase-before-write behavior, and device-specific parameter discovery. Its
NVM library warns that main flash cannot be read during erase/program; running
one writer from RAM does not make all flash-resident ISR code safe. See
[SAMD21 NVM overview](https://developerhelp.microchip.com/xwiki/bin/view/products/mcu-mpu/32bit-mcu/sam/samd21-mcu-overview/peripherals/nvmctrl/)
and [NVM library behavior](https://onlinedocs.microchip.com/oxy/GUID-450989FA-38E4-4D68-AB61-15ADB29AD718-en-US-6/GUID-959B9108-7325-499B-AA9A-387A164FAA7A.html).

Keep the stock updater exchange behind a distinct recovery/update backend.
It currently offers sequential application upload and addressed reads, not
arbitrary configuration transactions. A new application HID/CDC service is
conditional on proving that the USB cap can reach application mode. If it
cannot, a signed/versioned custom firmware package with a generated settings
block can give a useful first app workflow, but it is not equivalent to the
full management protocol in the intended product. The hardware gate must be
resolved before promising ordinary profile writes.

## Verification and selection gates

Use the same workload for both shortlisted languages; compare full linked
images rather than language microbenchmarks. Compiler optimization, logging,
UART/DMA policy and USB inclusion must be controlled.

1. **Read-only hardware baseline.** Identify MCU/revision, memory parameters,
   bootloader range/entry assumptions, fuses, USB descriptors/modes and a
   repeatable recovery path. Capture stock A7C II startup and focus traffic.
2. **Codec qualification.** Replay the 3,456 independently validated historical
   frames, then malformed lengths/checksums/terminators, partial frames,
   nonzero tails, unknown records, dropped windows and resets. Golden byte
   fixtures can be shared even if implementations use different languages.
3. **Comparable build prototypes.** Link a minimal C baseline and Rust candidate
   at `0x5000` with the correct 128/16 KiB limits, actual pin map, active
   profile and bounded trace. Record toolchain and exact dependencies, map
   files, code/data/BSS, stack estimates and release/debug differences.
4. **Timing and concurrency.** Use analyzer/GPIO timing on the actual unit:
   RX overruns, worst interrupt masking, CS-release gaps, parser execution,
   control-step jitter, UART TX completion and USB bursts. Deliberately fill
   queues; verify explicit overload behavior. An initial engineering goal is
   at least 25% SRAM margin after worst-case stack and a clearly measured
   deadline margin; this is a proposed gate, not an achieved result.
5. **Motion qualification.** Verify encoder fault detection, home/reference,
   travel clamps, stall/wrong-way/timeout guards, abort, retargeting, reset and
   disconnect while under load. Then compare AF-S acquisition and image
   accuracy across the user's lenses; AF-C/tracking/video require additional
   camera evidence. Do not substitute simulated servo tests for optical tests.
6. **Persistence/update qualification.** Exercise configuration interruption,
   firmware padding/erase behavior, read-back, profile migration, interrupted
   update and recovery. Reserve partitions in the linker and verify upload
   ranges in the host tooling.
7. **Selection.** Choose Rust if the actual HAL/PAC integration, release memory,
   timing, fault paths and development/debug loop pass these gates without
   excessive custom infrastructure. Otherwise select modular C, retaining
   the same interfaces and fixtures. Choose C++ only if it offers a concrete
   maintainability advantage with the team's expertise. Add RTIC/Embassy or
   an RTOS only when a measured requirement outweighs its cost.

## Licensing and evidence hygiene

The EA9 code snapshot has an MIT repository license; Microchip startup/linker
files retain Apache-2.0 notices. atsamd-rs is MIT OR Apache-2.0; TinyUSB and the
modern FreeRTOS kernel are MIT. Preserve the actual selected versions'
notices, including dependencies. The sigrok decoder carries GPL notices and
LexOptical lacks a repository license file in the collected snapshots; use
them as analysis evidence until any code-reuse decision resolves those
conditions. No product license is selected here.

Keep derived packet fixtures and optical rows tied to their captured or
recovered source and confidence. A top-level MIT notice on the reference
project does not by itself establish the provenance or redistribution status
of every stock-derived blob. Ship our independently implemented semantics and
documented calibration only after reviewing the selected data sources. The
[collection manifest](../../references/sources.json) and
[prior-work analysis](../../references/analysis/prior-work-analysis.md) retain
the distinctions needed for that decision.
