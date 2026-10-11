# Product direction and research decisions

Updated October 10, 2026 from the user's clarification. This document is the
source of truth for the intended product and the status of stack decisions.

## Confirmed product

The final product comprises three connected deliverables:

1. **Comprehensive, modular firmware for the Techart LM-EA9.** It implements
   camera communication, lens descriptions, focus motion, calibration,
   configuration, diagnostics, and dependable lifecycle/fault handling.
2. **A documented protocol for host communication with the LM-EA9.** It gives
   the macOS app a stable way to identify the device, discover capabilities,
   manage lens profiles and settings, and obtain diagnostic information. Its
   relationship to firmware installation and recovery must be specified.
3. **A polished, easy-to-use macOS app.** It makes lens metadata and profile
   management straightforward and provides clear connection, operation,
   verification, and recovery feedback.

The initial camera is the **Sony A7C II**. The user's manually adapted lenses
are recorded in [the inventory](../profiles/requested-lenses.json). Better
autofocus and convenient metadata editing remain core objectives. The firmware
must be designed as a maintainable product rather than a collection of lens-
specific patches.

## Stack decision: open

**No language, framework, GUI toolkit, embedded runtime, or host transport has
been selected.** Rust is an expressed interest and a candidate for evaluation.
It is not a requirement or the default implementation decision. Firmware,
protocol tooling, and the app may use different languages if the research
supports that choice.

The existing [Rust feasibility study](rust-architecture.md) explores one option.
Its crate layout, GUI suggestions, and implementation milestones are conditional
examples, not the approved architecture or development plan. The
[reference collection](../references/README.md) and
[research findings](reference-research.md) remain evidence regardless of the
language eventually chosen.

The [parallel audits](audits/README.md) and
[system design recommendation](system-design-recommendation.md) now identify
Rust firmware, native SwiftUI/AppKit presentation, and a bounded language-neutral
management contract as the leading design to prototype. This is a recommendation
with explicit qualification gates, not a frozen production stack.

Decide the stack after the research phase establishes the hardware constraints,
protocol behavior, host-access options, and practical app requirements. Record
the alternatives, evidence, tradeoffs, and chosen boundaries in a decision
document before committing to the implementation. A single-language stack is
one option, not a product goal.

## Modular responsibilities

These are logical boundaries; they do not prescribe crates, processes, or an
operating system.

| Module | Responsibility |
| --- | --- |
| Board and peripheral access | Clocks, pins, interrupts, UART, encoder, motor outputs, supply monitoring |
| Camera-facing E-mount transport and protocol | Transfer timing, frame validation, negotiation, commands, status and completion semantics |
| Lens/profile model | Metadata, identity, active settings, calibration records, provenance and schema evolution |
| Focus and motion control | Homing, position tracking, motion planning, control loop, aborts and motion guards |
| Firmware lifecycle | Startup, scheduling, configuration loading, persistence, shutdown and fault recovery |
| Device management protocol | Versioned host commands/responses, capabilities, configuration transactions and diagnostic access |
| Update and recovery support | Compatibility checks, image validation, backup, installation, read-back and recovery |
| Diagnostics and analysis tools | Trace export, measurements, fault reports and repeatable experiments |
| macOS app | Lens library, profile editing, device workflows, progress, actionable results and accessible interaction |

Define explicit interfaces and ownership between modules. Protocol/model logic
should be testable away from hardware. The app's presentation should be separate
from transport and device operations, so UI changes do not change wire semantics.
Scope and version the interfaces before choosing whether implementations are
shared across firmware and host code.

## Two distinct communication contracts

**Camera to adapter:** E-mount behavior is constrained by Sony camera traffic
and existing lens expectations. Reference captures and firmware establish an
initial body of evidence; our A7C II behavior still needs direct measurements.

**Mac to adapter:** The product needs its own documented device-management
contract. Specify protocol versioning, capability discovery, message limits,
error responses, transaction boundaries, persistence, timeouts and reconnect
behavior. Candidate operations include reading/selecting/editing profiles,
reading settings and calibration, retrieving diagnostics, and coordinating
updates where the device supports them.

The stock bootloader's HID update/read exchanges are an existing integration
constraint, not automatically the final management protocol. Application access
through the USB update cap and the ability to write configuration separately
from firmware remain research questions. Keep the protocol's logical operations
separate from the eventual transport binding. Do not promise live profile writes
or simultaneous camera/USB use before establishing that the hardware can support
them.

The [connected-device investigation](usb-cap-investigation.md) now confirms
native macOS CHECK/READ, a repeatable bootloader dump, and installed 1.8.0
application bytes. The inspected stock bootloader remains in USB mode instead
of launching the application. Full application management therefore needs a
qualified boot-entry bridge or alternate cap/mode path; those are new design
work, not already available commands.

The [read-only follow-up](usb-cap-followup.md) establishes the exact chip,
128 KiB capacity, fuse/protection baseline and two matching full main-flash
backups. PA23 digitally reads high in cap mode; analog levels and continuity
remain unmeasured. The [entry design proposal](management-entry-design.md)
records the next implementation boundary and independent recovery requirement.

## App quality and autofocus evidence

The app should support an ordinary user choosing a lens, entering known metadata,
applying settings, and understanding the result without a compiler or command
line. Clearly distinguish saved profiles, requested settings, and settings
confirmed on the device. Unknown optical calibration must remain identifiable;
editing a display name or focal length must not imply measured autofocus
calibration. Keyboard access, readable status, useful errors, and a coherent
macOS experience are part of the product quality target.

Autofocus maturity requires measured camera compatibility, repeatable acquisition,
accurate motion and status reporting, sensible lens-dependent calibration, and
recovery from interruptions. Test the actual adapter and lens loads. Establish
AF-S behavior first, then evaluate AF-C/tracking; video behavior needs its own
evidence. The stack choice cannot substitute for those measurements.

## Research completion and selection criteria

Before selecting the implementation stack, resolve or explicitly record the
remaining uncertainty in:

- Actual board, memory, bootloader and peripheral constraints, including a
  repeatable read-only device baseline and recovery path.
- A7C II initialization, command/completion behavior, metadata handling, timing
  and stock autofocus results with the user's lenses.
- USB-cap behavior, application connectivity and configuration persistence,
  which determine the host protocol's feasible operations.
- Relevant frame/field interpretations, including conflicts between older
  descriptions and captured bytes.
- Embedded toolchain/driver maturity, real-time predictability, memory use,
  debugging, testing and long-term maintenance for each candidate.
- macOS UI quality, accessibility, hardware integration, packaging and
  maintenance for each app candidate.

Evaluate viable candidates with focused prototypes where evidence is missing.
Compare against the same requirements and record results. Then select the stack,
finalize interface specifications, and plan staged implementation and hardware
validation. Research scripts already present in this repository do not select
the product's language.
