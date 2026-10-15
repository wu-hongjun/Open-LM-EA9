# Rust feasibility study — candidate only

October 14 follow-up: the [updated working recommendation](system-design-recommendation.md)
is to build on upstream C firmware and the native Swift app, deferring Rust.
The direct upstream camera trial also failed; resolve that compatibility
boundary before a language port. This document retains the earlier feasibility
study and does not describe the implementation now running on the adapter.

**The stack is undecided.** This document explores a Rust-based option, grounded
in [the reference investigation](reference-research.md). It is not an approved
implementation plan. The [product direction](product-direction.md) defines the
confirmed deliverables and the research needed before selecting a stack.

At the time of this original study no custom firmware had been flashed. The target is a Sony A7C II and
the eight user-supplied lenses in [requested-lenses.json](../profiles/requested-lenses.json).

## Candidate approach to the intended product

The Mac app maintains lens profiles, reads the adapter's identity and backups,
applies a selected profile, installs verified firmware, and displays exported
session diagnostics. Firmware emulates the camera-facing lens protocol and
drives the focus mechanism predictably. The camera supplies autofocus decisions.
Our work improves the actuator, its reports, and its lens description. A
separately specified host/device management protocol is also a product
deliverable; the bootloader exchanges discussed here are only an existing
transport/update reference.

A stack built mainly in Rust is a candidate to evaluate. Rust has
[SAMD21 support](https://github.com/atsamd-rs/atsamd), including a SAMD21E
peripheral-access crate exposed through
[atsamd-hal](https://docs.rs/atsamd-hal/latest/atsamd_hal/). The Cortex-M0+
[compilation target](https://docs.rust-embedded.org/book/intro/install.html) is
thumbv6m-none-eabi. If selected, Rust firmware should use no_std, fixed-capacity
buffers, integer or fixed-point control arithmetic, and small, explicit hardware
boundaries.
The SAMD21E17A's 128 KiB flash and 16 KiB RAM must be set in our own memory map;
a SAMD21E18 development board's larger memory layout is unsuitable.

For the Mac app, [egui/eframe](https://docs.rs/eframe/latest/eframe/) offers a Rust
desktop UI, and [hidapi](https://docs.rs/hidapi/latest/hidapi/) provides HID access
on macOS. The latter wraps a C library on macOS, so this is Rust application
code with platform/native dependencies, not a claim of zero C dependencies.
A SwiftUI front end with a Rust core is another candidate arrangement. Native
macOS interaction quality is a product criterion to evaluate before choosing
the app stack; this study does not select egui or defer that decision to a later
release.

## Proposed boundaries

| Component | Host / device | Responsibility |
| --- | --- | --- |
| lens-profile | Both | Profile schema, fixed-point values, format validation |
| emount-protocol | Both | Frame validation, packet encoding, handshake and command semantics |
| focus-control | Both | Motion state machine, controller, guards, prediction |
| ea9-board | Device | Clocks, pins, UART, SPI, PWM, ADC, interrupt handling |
| ea9-firmware | Device | Startup, homing, profile loading, runtime scheduling, shutdown |
| ea9-management | Both | Host/device contract, versioning, capabilities, settings, profiles, diagnostics and errors |
| ea9-usb | Host | Device selection, CHECK / READ / upload exchanges, timeouts |
| ea9-image | Host | Image validation, profile insertion, upload padding, read-back comparison |
| ea9-cli | Host | Repeatable backup, verify, install, restore, and diagnostics commands |
| ea9-macos | Host | Lens library, connection state, progress, results, diagnostics |

These are possible crate boundaries if Rust is selected. Keep the pure libraries
independent of GUI and register code so their behavior can be checked on the Mac.
Retain the C
reference and its tests for differential testing in a Rust prototype or port.

~~~mermaid
flowchart LR
    Camera[Sony A7C II] <--> Protocol[E-mount protocol]
    Protocol <--> Motion[Focus control]
    Motion --> Drive[PWM drive]
    Encoder[Position encoder] --> Motion
    Drive --> Mechanism[Lens extension]
    Mechanism --> Encoder
    Profiles[Lens profile] --> Protocol
    Profiles --> Motion
~~~

The Mac app and camera operate in separate sessions. USB configuration uses the
existing bootloader through the rear update cap. Do not make simultaneous
camera and USB operation a requirement without checking the hardware behavior.

## Metadata updates through the existing bootloader

The current bootloader protocol exposes addressed reads and sequential whole
application uploads. It does not expose a separate profile-write command. A
new GUI alone cannot make the existing firmware understand saved lens profiles.

One candidate design is a **profile block inside our custom application
image**. The Mac app would fill that block in a known firmware release and upload
the resulting image. Firmware would validate and read it at startup. This allows
profile changes without a compiler on the user's Mac, although each change
still performs an application upload. Keep the official bootloader intact.

Proposed flow:

1. Detect and select the LM-EA9 HID endpoint; read the bootloader version.
2. Read the installed application and, when supported, the bootloader. Save
   hashes and a complete recovery copy before the first custom upload.
3. Select a lens profile and a firmware release with a recognized image format.
4. Validate profile values and create a candidate image locally.
5. Validate vector table, memory bounds, configuration format, and transfer size.
6. Upload with bounded waits and progress tied to acknowledged reports.
7. Read the written region back and compare it to expected uploaded bytes.
8. Retain the verified image, profile, and transaction result for recovery.

Do not patch arbitrary offsets in official images to implement profiles:
runtime code can overwrite stored templates. Our firmware needs a stable,
versioned profile format and a discoverable configuration location. Use a
magic identifier, schema version, length, and corruption check, with defined
behavior for invalid or unsupported records. The corruption check is not an
authentication mechanism.

Read-back is what establishes that the selected image was installed. Neither
an ACK nor a bootloader version string proves image integrity or profile state.
Port upload report-ID handling and termination carefully; the Linux Python tool
is a protocol reference rather than a macOS transport implementation.

For faster switching later, consider storing multiple profiles in one image
and selecting one using a documented camera control sequence. Techart's
[manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf)
already demonstrates using camera aperture values for focal-length settings.
Our sequence and its persistence would be a new feature, requiring A7C II
testing. A separate USB configuration service is another option, but depends
on learning when the stock bootloader permits the application to run on USB.
Do not assume a new service is reachable through the existing cap.

## Lens-profile semantics

Separate three categories of data:

| Category | Examples | How it becomes trustworthy |
| --- | --- | --- |
| User metadata | Display name, focal length, nominal maximum aperture | User input and camera/EXIF verification |
| Optical calibration | Pupil-correction rows, distance mapping, reference focus setting | Source provenance and measured optical tests |
| Mechanism calibration | Encoder scale, travel, drive response, friction, loaded behavior | Measurements on the actual adapter |

Maximum aperture is not the current physical aperture. With no ring sensor,
the app can declare a value or provide a manual update mechanism, but firmware
cannot discover it. Preserve unknown calibration values as unknown rather than
generating plausible pupil rows from focal length alone. Editing metadata must
not silently claim a calibrated optical profile.

Numerical lens ID, lens-name response, focal-length fields, aperture fields,
distance model, defocus scale, and optical rows must describe one consistent
profile. Verify which fields the A7C II uses for EXIF and stabilization. A lens
ID can change camera protocol behavior, so retain identity separately from the
human-readable profile name.

The initial inventory is:

| User-supplied lens | Initial profile requirement |
| --- | --- |
| Contax Zeiss 28 mm f/2 | Prime metadata and optical calibration |
| Contax Zeiss 35 mm f/1.4 | Prime metadata and optical calibration |
| Contax Zeiss 50 mm f/1.4 | Candidate first reference lens |
| Contax Zeiss 85 mm f/1.4 | Prime metadata; measure behavior with its load |
| Contax Zeiss 100 mm f/2.8 macro | Record manual focus reference; calibrate macro behavior |
| Contax Zeiss 135 mm f/2.8 | Record useful manual prefocus settings |
| Contax Zeiss 28–70 mm f/3.5, as supplied | Manual current focal-length selection; verify aperture variation |
| Zeiss Jena Biotar 55 mm f/2, as supplied | Preserve supplied values pending model/calibration verification |

Names and specifications here reproduce the user's inventory. They are not
claims that model identity or every zoom aperture specification was independently
verified. Firmware operates behind the Leica M interface; the passive adapter
mount does not add electronic lens identification.

Changing a zoom setting requires changing the selected profile's active focal
length, manually or through a future camera sequence. Predefined 28, 35, 50,
and 70 mm entries are a useful initial interaction, with maximum aperture at
each setting left unverified until measured or checked against the exact lens.

The mechanism's approximately 4.5 mm extension cannot replace the lens's entire
focus-ring travel. For perspective, a thin lens initially set to infinity would
have an approximate nearest focus of f + f²/4.5 mm: about 0.61 m at 50 mm,
2.32 m at 100 mm, and 4.19 m at 135 mm. These are illustrative calculations,
not measured distances for the user's lenses. Manual prefocus expands the
useful range but changes the absolute distance model. The macro profile needs
an explicit reference setting rather than a universal infinity assumption.

## What a mature autofocus implementation needs

Preserve the camera's focus commands and its required completion semantics.
Use a nonblocking motion state machine so handshake, status, aborts, and
shutdown remain responsive during motor movement. Move from the reference's
single pending-command slot to deliberately specified replacement/queue rules;
do not assume every relative command can be collapsed into the latest target.

Enforce valid incoming frames before accepting motion commands. Unknown-size
records must stop parsing safely. Test malformed lengths, bad checksums,
truncated transfer windows, padding, unsupported commands, idle sentinels,
retargeting, stop priority, and shutdown during a move.

Measure encoder noise and wrap tracking, breakaway drive, forward/reverse speed
response, stopping distance, backlash or relaxation, and behavior under the
different lens loads. Tune using those results. Add bounded hardware waits,
motor-off fault handling, and a watchdog policy whose resets leave drive pins
in a verified safe state. A faster controller is not automatically a sharper
focus result.

Establish optical results separately: repeated acquisitions at several subject
distances, center and edge focus points, bright and dim scenes, and relevant
manual aperture settings. Record acquisition success, false focus locks,
time-to-lock, final sharpness, commanded-versus-achieved position, and recovery
after interruptions. Test AF-S first, then still-photo AF-C and tracking. Treat
video AF as separate protocol research until A7C II traces establish its needs.

## Illustrative milestones if Rust is selected

These illustrate the candidate's implementation sequence after research and
stack selection. They are not the current approved development roadmap.

| Milestone | Work | Evidence required to move forward |
| --- | --- | --- |
| 0: Preserved baseline | Cache image, hashes, reference snapshots, host tests | Completed in this investigation |
| 1: Device and camera baseline | Rust HID CLI with CHECK/READ; full dump; capture official A7C II traffic and stock focus results | Repeatable read-back and a stock behavior record |
| 2: Host application core | Shared profile schema, image validation, recovery transactions, CLI, Mac profile editor | Offline malformed-image tests and read-only device checks |
| 3: Rust protocol core | Match known C behavior, then improve validated parsing and command semantics | Differential tests, trace replay, no_std target build |
| 4: Device bring-up | Startup, clocks, UART, encoder; motor-disabled handshake | Correct identity, stable power, shutdown and reboot on A7C II |
| 5: Controlled motion | Measured bounds, homing, short moves, control loop and guards | Encoder traces and bounded fault behavior on actual mechanism |
| 6: One working lens profile | Start with the 50 mm prime if convenient; apply through Mac app | Verified upload, correct metadata, repeated optical focus tests |
| 7: Lens library and autofocus maturity | Remaining primes, zoom workflow, macro reference settings, AF-C | Per-profile results and regression matrix on A7C II |
| 8: Normal-use release | Reduce diagnostic writes, package app, retain recovery workflow | Exact release image and packaged Mac app independently validated |

A short C-based baseline may be useful if needed to compare hardware behavior.
A Rust candidate could cover the protocol, controller, firmware, app core, and
GUI, or use a native macOS front end. These alternatives need evaluation before
selection. Implement the protocol against evidence before changing the motor
control law. Early correctness work can proceed without an adapter connected;
camera compatibility and final focus performance require hardware sessions.

## Build and memory considerations for this candidate

If Rust is selected, use a pinned toolchain, locked dependencies, host tests for
pure crates, and a separate thumbv6m-none-eabi target build. Preserve the application start
at 0x5000, correct relocated interrupt vectors, SAMD21 startup errata handling,
and the measured clock configuration.

Reserve bootloader, application, configuration, and diagnostic regions in the
linker. The reference's diagnostic region starts at 0x16000 and extends through
0x18100; our eventual partitioning must explicitly prevent overlap rather
than assuming the code remains small. Ensure the complete padded upload also
fits its permitted region. Check stack/RAM headroom and avoid dynamic
allocation in time-critical firmware.

Preserve license notices when adapting reference sources, including the
Microchip startup/linker components. The recovered official firmware and
local source snapshots remain outside tracked project files, in the
[reference collection](../references/README.md). The
[prior-work analysis](../references/analysis/prior-work-analysis.md) and
independently extracted A6000 frames provide a first corpus for a frame codec
in any selected language; modern camera and motion behavior still require new
evidence.

The main outstanding dependency is direct A7C II/device evidence, not a choice
of programming language. Evaluate Rust's benefits and costs alongside other
viable stacks after the research; a language cannot supply missing protocol
observations or lens calibration.
