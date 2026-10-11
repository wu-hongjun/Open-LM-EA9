# LM-EA9 reference research

Investigation date: October 10, 2026. Target: Sony A7C II, a Contax C/Y-to-Leica M
adapter, and the lenses recorded in [the inventory](../profiles/requested-lenses.json).
The confirmed scope and undecided stack are recorded in
[the product direction](product-direction.md). A
[Rust feasibility study](rust-architecture.md) explores one candidate only.

## What the references provide

The [LM-EA9 repository](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9)
provides an application firmware replacement with reported camera testing on a
Sony a9 II. It is a useful working reference, but A7C II compatibility remains to
be established. Its companion [protocol documentation](https://github.com/weiziqian/E-mount-protocol-RE)
labels conclusions CERTAIN, PROBABLE, POSSIBLE, or UNKNOWN. Preserve those
distinctions when translating the implementation.

The snapshots inspected were:

| Reference | Git commit |
| --- | --- |
| LM-EA9 implementation | d52ed06cc449918f938e0695fbf29a0c4141f2b2 |
| E-mount protocol documentation | 3a94a8d2e6a7786ab3e05b1319b421e76744b4c0 |

Local source snapshots are now in [references/upstream/](../references/upstream/),
with licenses preserved and build outputs excluded. The
[collection manifest](../references/sources.json) pins every revision. The
[prior-work analysis](../references/analysis/prior-work-analysis.md) adds
Entropy512's captures/decoder and LexOptical's implementation/traffic samples.
The original snapshots in artifacts/private/references/ are retained.

The device code is **C**, using GNU C99, ARM Thumb instructions, and the
arm-none-eabi GCC toolchain. Python supplies flashing, packet extraction, image
checks, and diagnostic decoding. Make orchestrates compilation. The build uses
Microchip ASF4/CMSIS headers; many hardware accesses are direct register writes.
There is no operating system in the application. See the pinned
[Makefile](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/Makefile).

[REA](https://morluto.github.io/rea/) is a reverse-engineering CLI and MCP server.
Its [package configuration](https://github.com/morluto/rea/blob/main/package.json)
builds TypeScript into a Node.js program; provider bridges include Python and
Java. It can help investigate compiled desktop applications, but it is not an
LM-EA9 firmware project or a compiler for the adapter.

## What was recovered from this Mac

The updater exists at /Users/hongjunwu/Downloads/TECHART_Update.app. Its
USB_Update executable is an Intel x86_64 Mach-O application with Swift runtime
dependencies. The application bundle's version is 1.0; that identifies the
updater, not the adapter firmware.

Its executable contains the product-manifest URL:

    http://www.techart-logic.com/product/TECHART_LST.txt

The firmware was found outside the app bundle, in its URL-loading cache:

    /Users/hongjunwu/Library/Caches/TECHART.USB-Update/Cache.db
    /Users/hongjunwu/Library/Caches/TECHART.USB-Update/fsCachedData/5EFD3032-D8AD-4A34-BE34-6D22272A7053

The SQLite response entry associates that second file with the official URL
ending in /firmware/LM-EA9/EA9-VER-1-8-0.bin. The cached product manifest explicitly
labels it VER 1.8.0. The release note, decoded as GB18030, says that some bugs were
fixed. These cache contents substantiate a downloaded release; they do not prove
that the current device still contains it.

The recovered application image is preserved locally at
references/private/techart/stock-1.8.0/EA9-VER-1-8-0.bin, beside the original
manifest, release note, and provenance.json. The earlier copy under
artifacts/private/stock/ remains available. Recovery read the cache without launching the updater
or communicating with the adapter.

| Property | Observed value |
| --- | --- |
| Image size | 20,172 bytes, hexadecimal 0x4ECC |
| SHA-256 | f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564 |
| Initial stack pointer | 0x20002AB0 |
| Reset vector | 0x00006145, Thumb code at 0x6144 |
| Assumed load address, consistent with vectors | 0x5000 |
| Exclusive image end | 0x9ECC |
| Camera-facing version byte | 0x18 at file offset 0x4A44 |

The upstream image checker passed all vector and memory-range checks. Its packet
generator recovered 20 outgoing packets and a 1,272-byte data initializer.
Generated emount_packets.c was byte-for-byte identical to the checked-in source;
the generated header differed only in its source-path comment. This strongly
connects the recovered firmware to the version used by the reference project.
The evidence is saved in [stock-image-verification-2026-10-10.txt](evidence/stock-image-verification-2026-10-10.txt).

The official updater uses a manifest version triplet, while the camera reads a
BCD field in an E-mount response. Those are separate records; do not derive one
from the other when building our app. The local evidence identifies release
**1.8.0**, which likely explains the user's remembered 0.1.8 designation.

## Hardware and firmware boundary

The reference targets a **SAMD21E17A**, ARM Cortex-M0+, with 128 KiB flash and
16 KiB SRAM. Its linker places the application at 0x5000, leaving a 20 KiB
bootloader below it. This investigation verified the stock image's shape, but
has not independently inspected this adapter's board or bootloader. See the
[linker script](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/ea9.ld)
and [startup source](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/startup_samd21.c).

| Peripheral | Reference implementation's use |
| --- | --- |
| SERCOM1 | E-mount UART, 750 kbaud, 8N1 |
| EIC | Camera transfer-window and frame-sync edges |
| SERCOM0 | SPI position encoder, 1 MHz, 14-bit readings |
| TCC0 | Four motor PWM outputs, approximately 18.75 kHz |
| SysTick | Millisecond timing in the reference; TC4 appears in recovered stock scheduling |
| ADC | Supply-voltage measurements for diagnostics |

The pin and clock configuration is recovered from stock firmware in
[board.h](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/board.h)
and recovered_config.h. Preserve those settings during initial bring-up rather
than substituting a generic development-board configuration.

There is a hardware-description discrepancy worth resolving: upstream describes
one motor with parallel H-bridges, whereas [Techart describes four physical
motors](https://techartpro.com/?product=lmea9). The code demonstrably commands two
PWM pairs together. That establishes coordinated drive behavior, not the
physical number of motors or their wiring. Model one focus axis in software
until a board inspection or electrical measurements establish more.

The SPI encoder is absolute within one revolution, but linear travel still
needs a home reference. The reference tracks small wrapped sample differences
to accumulate motion, and homes at startup. The position conversion advertises
4144–5632 protocol units, corresponding to 5,952 encoder counts. Treat that as
the reference unit's measured configuration. See
[abs_encoder.c](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/abs_encoder.c)
and [focus_map.h](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/focus_map.h).

## How autofocus actually works

The camera measures defocus and chooses the requested motion. The adapter moves
the entire mounted lens along the optical axis; it cannot read or turn the
manual lens's rings. Better adapter autofocus therefore requires accurate
camera communication, reliable actuation, and useful optical calibration.

The [frame specification](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/frame_format.md)
defines a start byte F0, a little-endian total length, class, sequence, message
ID, payload, additive 16-bit checksum, and terminator 55. Chip-select delimits
the transfer window, which can contain extra bytes beyond the declared frame.
Independent extraction of the older A6000 captures found both zero and nonzero
tails; see the [captured evidence](../references/analysis/prior-work-analysis.md).
Parse the declared length against available bytes; padding must not become
motor instructions.

The [focus protocol](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/autofocus.md)
describes a roughly 60 Hz cycle: adapter status messages 0x05 and 0x06, then
camera messages 0x03 and 0x04. Tagged records inside 0x04 request movement,
stopping, scans, continuous drive, and position/distance conversions. Message
0x06 supplies position, anticipated position, travel limits, and completion
events. Continuous-drive support alone does not establish video-AF support.

The implementation separates responsibilities as follows:

| Module | Responsibility |
| --- | --- |
| em_uart.c / em_eic.c | UART bytes and camera timing edges |
| emount.c | Handshake, status packets, command records, completion events |
| emount_packets.c | Stock-derived response templates |
| main.c | Startup, homing, movement execution, parking, shutdown |
| servo.c | Position-to-speed profile, drive control, motion guards |
| motor.c / abs_encoder.c | PWM outputs and encoder sampling |
| focus_map.c / focus_dist.c / focus_pred.c | Unit conversion, distance approximation, position forecast |
| diag.c / trail.c | Flash diagnostics and session evidence |

The inspected [responder](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/emount.c)
bounds record parsing, stops at unknown-size records, and filters the 0x7FFF
absolute-move sentinel. Its incoming frame dispatch does not perform complete
checksum and terminator validation before interpreting commands. Harden that
boundary in our implementation and test malformed and truncated traffic.

Its [servo](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/servo.c)
updates control every 5 ms. Remaining position error creates a speed request;
feedforward anticipates required drive, proportional speed feedback trims it,
and a bounded boost overcomes friction. Arrival requires both position accuracy
and low speed across consecutive samples. Stall, timeout, excessive overshoot,
wrong-direction movement, aborts, and retargeting are handled explicitly.
Calibration constants in
[servo.h](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/servo.h)
come from the author's mechanism; they need checking with our unit and lens loads.

## Metadata and optical profiles

The current firmware selects focal length, aperture declarations, and optical
rows through constants in
[emount.h](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/emount.h).
It defaults to 50 mm and a quantized f/1.8 declaration. Changing constants and
rebuilding works for one lens, but our app should instead populate a defined
configuration block.

Changing focal length must update every related protocol field consistently.
Lens names and numerical lens IDs need separate A7C II checks: an identity can
affect the camera's behavior, and an arbitrary name is not guaranteed to appear
in EXIF. The default upstream numerical lens ID is experimental. Maximum
aperture, the declared current aperture, and what the lens is physically set to
are distinct values. The adapter has no aperture-ring sensor.

The [optical-row research](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/optical_data.md)
connects correction rows to pupil geometry and off-axis phase detection. Some
interpretations remain POSSIBLE or PROBABLE, and two row channels remain
UNKNOWN. The reference's borrowed rows are not calibrated Contax profiles.
Correct EXIF alone does not prove correct optical behavior. Measure actual
focus accuracy at center, intermediate positions, and frame edges for each lens.

The distance conversion in
[focus_dist.c](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/focus_dist.c)
uses a thin-lens approximation with 4.5 mm total extension and an infinity
reference. A manually prefocused lens invalidates that absolute-distance
assumption. Longer lenses and the 100 mm macro particularly need measured
reference settings. The 28–70 mm zoom needs an explicitly selected focal
length; the hardware cannot sense zoom or its corresponding maximum aperture.

## Flashing, diagnostics, and macOS implications

The inspected [Python uploader](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/tools/ea9flash.py)
uses HID device 0483:575A and 64-byte reports. It implements version checking,
sequential application upload, and addressed flash reads. Its transport directly
uses Linux hidraw and sysfs, so it does not run unchanged on macOS. The Mac app
needs a corresponding HID backend. Upload padding and the exact final report
count should be reproduced from observed behavior, including the script's
inclusive loop boundary, rather than inferred from its prose comment.

The bootloader is the USB endpoint in the reference; the camera application does
not provide its own USB profile-settings service. Ordinary operation therefore
means moving between camera use and USB-cap configuration. A metadata-only
update protocol is a future design task, not an existing feature.

Debug firmware records evidence in flash starting at 0x16000. Release firmware
omits diagnostic writers. The
[diagnostic layout](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/diag.h)
occupies four 0x800-byte slots plus a 0x100-byte tally. The current linker permits
application growth across that area; our linker should reserve logs and
configuration explicitly. Validate the actual uploaded and read-back image,
including padding, against those boundaries.

Recoverability depends on preserving the bootloader and correctly implementing
flash writes. The author's recovery experience is useful evidence, but is not a
guarantee against every application bug or hardware damage. A full read-only
device dump, successful read-back, and a retained recovery path should precede
custom motor experiments.

## What REA can contribute

REA's [firmware guide](https://github.com/morluto/rea/blob/main/docs/firmware-analysis.md)
documents Binwalk/Unblob workflows verified on Linux x64 and explicitly excludes
raw-flash load profiles. Arbitrary firmware bytes do not pass its native
executable admission. Consequently, installing REA is not sufficient to analyze
this bare Cortex-M image. Use Ghidra directly with a raw binary load address of
0x5000, little-endian ARM Cortex-M/Thumb analysis, and the SRAM map above; verify
the tool's exact processor selection before interpreting code.

REA could still help inspect the x86_64 macOS updater through a supported native
provider, especially USB exchange behavior and error handling. Its
[setup documentation](https://github.com/morluto/rea/blob/main/docs/installation.md)
describes registration and provider prerequisites. No REA installation or agent
configuration change was performed in this investigation.

## Verification and remaining evidence

On this Mac, upstream make hosttest completed successfully: seven test
executables, eight runs including no-camera and slow-camera scenarios, all
reporting zero failures. The linker emitted alignment warnings for three test
executables, without test failures. See [the retained log](evidence/upstream-hosttest-2026-10-10.txt).

The host tests exercise protocol handling and simulated movement. They do not
establish timing, motor behavior, image sharpness, or A7C II compatibility.
An ARM image was not built: arm-none-eabi GCC and the expected ASF4 directory
were not found in the checked tool locations. Rust 1.97.1 is installed, but the
thumbv6m-none-eabi target is not. REA and Ghidra/Hopper were not found in the
checked PATH and application locations.

Some upstream comments reference EA9.md, NOTES.md, servo.md, CLAUDE.md, and
tools/mkfw.py, which are absent from these snapshots. Published hardware
measurements cannot all be audited from this checkout. Preserve the working
code as a behavioral reference while collecting our own traces, calibration,
and repeatable A7C II results.
