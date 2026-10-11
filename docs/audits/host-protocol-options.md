# Host communication, persistence, and recovery audit

Audited October 10, 2026. This is a system-design recommendation, not an
implemented protocol or a hardware compatibility claim. The stack remains
undecided in [product-direction.md](../product-direction.md). No adapter was
accessed, no updater was run, and no firmware or bootloader was changed.

## Recommendation

Keep the original bootloader as the recovery/update channel. Define our
management operations independently of that channel and of any implementation
language. Prefer a small vendor HID service for application-level management
**if the application can actually execute while connected to the existing USB
cap**. That feasibility question is unresolved and is the first hardware gate.

Use a bounded binary envelope and restricted CBOR payloads described by a
versioned CDDL schema. Keep lens-library JSON and firmware release manifests on
the Mac; use compact validated records on the adapter. Configuration needs
transactions and explicit read-back, independently of firmware installation.
Use two row-aligned persistent config banks with a final commit page, a separate
active-selection journal, and infrequent fault records. Do not write main-array
flash while servicing focus motion or camera deadlines.

The immediately evidenced integration path is narrower: the app builds a
known custom application image containing a validated profile bundle, uploads
it through the legacy bootloader, and verifies the actual written bytes. This
is an honest initial backend for applying profiles. It is not evidence that
the stock bootloader supports dedicated settings writes. If application USB
access is impossible without modifying the bootloader, retain this backend and
make a separate, explicit product decision about bootloader development only
after SWD recovery and complete bootloader behavior have been established.

## What the local evidence establishes

The inspected firmware and uploader are pinned at
`d52ed06cc449918f938e0695fbf29a0c4141f2b2`. The
[uploader](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/tools/ea9flash.py)
defines the following protocol. Its hardware statements describe the author's
LM-EA9; they have not been independently repeated on this adapter.

| Operation | Host report content | Observed/reported reply and limitation |
| --- | --- | --- |
| Discovery | USB VID:PID `0483:575A`, unnumbered HID reports | Not a unique LM-EA9 identity or a firmware integrity result |
| CHECK | `95 27 68 18 02 02`, zero padded | Same magic/command followed by a three-byte version declaration |
| START | `95 27 68 18 01 01`, three version bytes | Same magic/command; begins a sequential application write |
| DATA | Raw 64-byte image chunks | Script advances after any inbound report; no address, sequence or chunk CRC is in the stream |
| READ | `95 27 68 18 03 03`, little-endian 32-bit address | 64 raw bytes with no magic or echoed address; upstream reports reads below `0x5000` too |

The source has no dedicated config-write command, application-run command,
capability query, authenticated image admission, or demonstrated resume
operation. Absence from this implementation is not proof that no undiscovered
bootloader command exists. The host must not experiment with unknown commands
on a user's adapter to discover them.

The uploader's `send` method writes a leading zero report-ID byte plus 64 report
bytes to Linux hidraw. That 65-byte API buffer is not a 65-byte USB firmware
payload. `READ` replies have a different shape from CHECK/START replies. A port
must preserve those distinctions and validate actual report lengths before
indexing them. A single outstanding legacy operation is required because READ
does not echo its address and DATA ACKs lack identifying information.

The upload loop computes `limit = (image_length // 1024) * 1024 + 1024` and
continues while `pos <= limit`, with 64-byte chunks. Therefore this source sends
**`limit + 64` bytes**, not simply a rounded-up image length. For the recovered
20,172-byte stock image that is 20,544 bytes, potentially covering
`[0x5000, 0xA040)` if sequential destination behavior matches upstream. This
footprint is a code calculation, not a measured erase/write boundary. Confirm
the official updater's transfers and the bootloader's erase granularity before
copying the algorithm into a release app.

The [linker](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/ea9.ld)
starts application code at `0x5000` and permits growth to `0x20000`, with 16 KiB
SRAM. The original diagnostics occupy `[0x16000, 0x18100)`, but that range is
not excluded by the linker. The [diagnostic implementation](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/src/diag.c)
also writes warm-reset counters at fixed high RAM addresses. These are useful
development examples; they are not a final partition/persistence contract.

The [reference README](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/blob/d52ed06cc449918f938e0695fbf29a0c4141f2b2/README.md)
says USB is implemented only by the bootloader and that it runs independently
of application validity. `board.c` and `recovered_config.h` describe PA23 as a
bootloader mode input before the application changes it into an output; later
shutdown code uses it as a signal. Supporting `EA9.md` and the author's complete
bootloader dump are absent from this snapshot. Our cache recovery preserved an
application image, **not this device's bootloader**. Do not infer an available
USB application service or an unconditionally recoverable device from those
comments.

## Transport alternatives

| Option | Fit | Decision |
| --- | --- | --- |
| Existing HID bootloader | Already evidenced update/read path; smallest compatibility change | Keep for installation/recovery. Treat as a separate legacy state machine. |
| Application vendor HID | Good fit for small profile/config/control messages; macOS user-space API; report-sized framing | Preferred management binding if USB-cap application execution is proved. Separate custom identity/usage and protocol from stock commands. |
| Application CDC ACM | Convenient development terminal and byte stream; needs explicit framing, discovery and port ownership | Good bench/debug option; no benefit that resolves the application-execution gate. Avoid shipping HID+CDC solely to support a second way of doing the same work. |
| Vendor bulk | Useful for sustained large trace export; more direct USB integration and interface ownership work | Defer unless measured trace volume exceeds HID needs. |
| USB mass-storage configuration | Familiar file drag/drop | Poor primary management interface: filesystem caching and eject/write completion obscure transactional device state. |
| Camera aperture/control sequence | Can select preloaded profiles without moving the adapter back to the Mac | Optional camera-side selection mechanism, tested on A7C II. It is not a Mac communication channel. |
| New/custom bootloader | Could provide settings writes, app launch, verified updates or richer recovery | Separate high-risk engineering scope. No replacement before actual bootloader/SWD recovery measurements. |

The SAM D21 supports USB device endpoints and control, interrupt, bulk and
isochronous transfers. Its USB data pins are PA24/PA25; valid USB clock setup
also matters. These capabilities establish silicon feasibility, not the
LM-EA9 cap's routing, mode-selection behavior or simultaneous camera/USB use.
[Microchip USB overview](https://developerhelp.microchip.com/xwiki/bin/view/products/mcu-mpu/32bit-mcu/sam/samd21-mcu-overview/peripherals/usb-overview/),
[SAM D21 USB application note](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42261-SAM-D21-USB_Application-Note_AT06475.pdf),
[driver clock considerations](https://onlinedocs.microchip.com/oxy/GUID-2A8AADED-413E-4021-AF0C-D99E61B8160D-en-US-4/GUID-E1A10519-71AD-44B7-BD52-FD0CD8EB5077.html).

For C/C++, TinyUSB documents SAM D21 device support, HID, CDC, and no-OS use.
Those are library capabilities, not tested EA9 builds. For a Swift app, direct
IOHID APIs avoid a transport dependency; for Rust or a portable host core,
HIDAPI uses IOHIDManager on macOS. Keep either backend behind the same report
transport interface. Apple recommends input-report callbacks rather than
polling input with GetReport; sandboxed distribution has a USB entitlement.
No custom kernel driver is implied by this HID design.
[TinyUSB](https://github.com/hathach/tinyusb/blob/master/README.rst),
[HIDAPI](https://github.com/libusb/hidapi),
[Apple input report guidance](https://developer.apple.com/documentation/iokit/1588662-iohiddevicegetreportwithcallback),
[USB entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.device.usb).

## Encoding and schema ownership

| Candidate | Strength | Cost / boundary |
| --- | --- | --- |
| Fixed binary records with TLV extensions | Explicit bounded buffers, simple small decoder, exact field offsets | We own field registry, evolution rules, validator, tooling and cross-language codec maintenance. Viable footprint fallback. |
| Restricted CBOR + CDDL | Language-neutral standard, explicit schemas, optional typed fields, compact integer keys | Restrict the format and enforce limits; a general-purpose decoder's acceptance policy is insufficient. Recommended. |
| Protobuf | Mature tagged-field evolution and generated codecs; Swift runtime and static C nanopb available | Extra generator/toolchain and embedded field-allocation choices. Viable alternative, but not necessary for this small protocol. |
| Postcard / serde-shaped serialization | Compact and convenient for an all-Rust implementation; documented stable wire format | Stable primitive encoding does not freeze a Rust struct's field order/schema. Avoid making firmware's language the external specification. |
| JSON on device | Excellent host editing and support artifacts | Unnecessary device parse/string overhead and canonical numeric ambiguity. Keep as app import/export representation. |
| FlatBuffers / Cap'n Proto / general RPC stack | Rich generic application ecosystems | No demonstrated need that justifies the additional format/runtime surface here. |

CBOR's core deterministic profile defines preferred encoding, definite lengths
and key ordering; CDDL defines schemas. Adopt a smaller product profile:
unsigned integer field keys, bounded signed/unsigned integer values, booleans,
bounded UTF-8 text and byte strings, and shallow bounded arrays/maps. Reject
duplicate keys, indefinite lengths, unsupported tags/floats, unknown critical
fields, and trailing bytes. Use explicit integer units such as tenths of a
millimeter for focal length; physical f-number and Sony's encoded aperture are
different fields. Each schema defines whether unknown optional keys may be
skipped. [RFC 8949](https://www.rfc-editor.org/rfc/rfc8949.html),
[RFC 8610](https://www.rfc-editor.org/info/rfc8610/).

Rust's minicbor documents no-std support and fixed-buffer encoding without
enabling alloc. C's zcbor can generate validating codecs from CDDL. Its
canonical option does **not** enforce map key ordering, so do not rely on a
library feature name as conformance evidence. Nanopb supports bounded/static
fields, and SwiftProtobuf is maintained by Apple; these make Protobuf a real
alternative, not an impossible embedded option.
[minicbor](https://docs.rs/minicbor/latest/minicbor/),
[zcbor](https://github.com/nordicsemi/zcbor),
[nanopb allocation options](https://github.com/nanopb/nanopb/blob/master/docs/reference.md),
[SwiftProtobuf](https://github.com/apple/swift-protobuf),
[Postcard wire-format documentation](https://docs.rs/postcard/latest/postcard/).

Own schemas in an independent `protocol/` package: the normative wire document,
numeric field/error registry, CDDL, version compatibility table, golden byte
vectors, malformed corpus and import/export schema. Bindings implement that
contract; their in-memory struct layouts do not define it. The full Mac library
may retain notes, calibration evidence and unsupported future fields. Device
records contain only bounded data required for operation, with explicit
calibration state/provenance identifiers. Never silently convert unknown
optical calibration into zeros that look measured.

Before finalizing CBOR, measure the same hello/profile/transaction corpus with
the chosen embedded codec and a minimal TLV prototype. Require target flash,
stack/RAM, malformed-input and host interoperability results. This is a narrow
encoding acceptance test, not a proposal to defer the whole architecture.

## Management contract

The custom envelope should carry protocol major/minor, message kind/opcode,
session token, request ID, declared total length, fragmentation information,
and an explicitly defined integrity check. Keep a report-sized header separate
from payload serialization. Specify report-ID handling at the HID API boundary.
Reassembly uses a single bounded request buffer and bounded timeout; start with
one outstanding mutating transaction. Large library/log reads are paginated,
not unbounded responses. Set exact caps after target measurements and advertise
them in capabilities; the Mac may keep all eight requested lenses even if early
firmware stores only a smaller selected subset.

The minimal logical operations are:

| Group | Contract |
| --- | --- |
| Identify / capabilities | Product/board ID, firmware build identity, protocol/schema ranges, operating mode, supported operations, profile capacity, object sizes and transaction limits |
| Read state | Installed profile generation/hash, selected profile ID, calibration states, mechanism identity, faults and diagnostic availability |
| Read library | Stable profile IDs and paginated bounded records |
| Begin / write / validate / commit | Expected current generation, transaction ID, target object length/hash, offset-checked chunks, full semantic validation, explicit persistent commit result |
| Abort / query transaction | Reconcile a timeout or reconnect; determine whether the intended generation committed |
| Select profile | Immediate RAM selection or explicit persisted selection; only at a defined idle/session boundary |
| Diagnostics | Bounded snapshots/log export, format/build ID, dropped-record counts, timebase and wrap behavior |
| Update coordination | State readiness and report transport transition; installation itself remains the separately specified bootloader workflow |

Error classes should include malformed, unsupported version/operation,
unsupported/critical field, limit exceeded, invalid profile, generation
conflict, busy mode, stale session, persistence failure, and operation state
unknown. A retry reuses request/transaction identity. Duplicate chunks must be
idempotent, and a duplicate commit must return the previous result without
another flash erase. An interrupted reply is not evidence that the write failed.
Reconnect reads the committed generation/hash before presenting a result.

Capabilities must distinguish the custom application from the legacy
bootloader. CHECK is not a substitute for HELLO. Never send custom management
opcodes to a stock bootloader identified merely by VID/PID. The legacy backend
can offer read/backup/install and apply-by-image; it must report dedicated
settings writes unavailable. The app distinguishes locally saved, prepared,
uploaded/read-back verified and runtime-selected state.

## Persistence and update transactions

SAM D21 main flash uses 64-byte pages and four-page, 256-byte erase rows. Its
variant-specific RWWEE section is not a general property of the E17A target;
confirm the actual part instead of assigning it EEPROM storage. Main-array
program/erase stalls AHB access, so a nonblocking software NVM state machine
alone does not prove camera deadlines remain serviceable.
[Physical memory parameters](https://onlinedocs.microchip.com/oxy/GUID-22527069-B4D6-49B9-BACC-3AF1C52EB48C-en-US-21/GUID-BFF407FF-FE62-4CC6-B902-8DFA87AA8826.html),
[NVM memory organization](https://onlinedocs.microchip.com/oxy/GUID-DDF2C9BC-07FB-4ABF-938A-774B157B4519-en-US-10/GUID-0A57A35A-4CD7-45F3-8D90-4E81614DDF28.html),
[family datasheet, NVM write procedure](https://ww1.microchip.com/downloads/en/DeviceDoc/SAM-D21DA1-Family-Data-Sheet-DS40001882G.pdf).

Reserve linker-enforced, row-aligned regions for app code/image config,
persistent config banks, selection journal and bounded fault records. Choose
addresses after actual code-size, maximum profile/calibration record-size and
bootloader erase-footprint measurements; do not copy the old diagnostic map.
Assertions must include padded upload spans and RAM/stack headroom.

An A/B config bank contains a schema/version, device/mechanism compatibility,
generation, payload length, checksum and payload. Write only the inactive bank:
erase its rows, write and read-back validate payload/header, then program a
previously erased separate commit page **last**. Verify that page before
acknowledging persistence. At boot select the newest completely valid compatible
generation and retain the previous bank until the new one is confirmed. Never
erase the sole valid bank. This detects interrupted/corrupt programming; a CRC
is not authentication. Do not treat a page write as intrinsically power-fail
atomic. Test reset/power loss at every erase/program boundary.

Keep frequent selection changes in RAM. Persist only explicit user selections
using a small append journal with bounded compaction, and coalesce repetitive
requests. Store mechanism calibration separately from optical lens data so
importing a lens does not replace unit-specific travel/motor limits. A fault log
must not trigger an erase storm on a repeating fault or every camera frame.
In camera mode, defer flash writes to a measured idle/shutdown opportunity or
require a management session. A USB-only motor-disabled management mode makes
this easier if it is reachable.

Firmware upgrades must define which config regions the bootloader can erase.
If they can be overwritten, back up the exact records and migrate/restore as
part of the upgrade instead of assuming persistence. For image-backed initial
configuration, use a release manifest containing hardware ID, application load
address, maximum upload span, build digest, config location/schema/size and
allowed variants. Patch only a recognized custom release's reserved config
section. Preserve and verify the original code regions; record both release
identity and personalized image digest. Never patch guessed offsets in official
firmware.

Legacy uploads are **not atomic firmware updates**. A timeout after a DATA
report leaves uncertainty about whether the device accepted it; retransmitting
that chunk can shift the whole sequential image. Stop, establish a fresh known
bootloader session, and restart only according to validated recovery behavior.
Do not promise resume, on-device rollback, dual application slots, or firmware
signature enforcement that the retained bootloader does not provide.

The host operation journal records selected device identity/path, backup hash,
source release, prepared image hash, intended profile generation, calculated
span, acknowledged progress and read-back result. Backups include original
application and accessible bootloader/config regions before first custom
installation. Validate vectors, SRAM/flash bounds and all protected spans
locally before START. After upload compare the complete expected transmitted
range through READ, not just CHECK or an ACK. Boot/runtime/camera validation is
a subsequent stage. A backup is useful recovery material; it cannot by itself
restore a damaged bootloader through an absent USB endpoint.

## Validation gates and assumptions to reject

1. **Read-only baseline:** enumerate a selected adapter, capture descriptors and
   stable identity fields, CHECK and repeat READ/dumps with hashes on macOS.
   Confirm main-array size/part and compare the installed image with the cached
   release. Do not broadcast to every device sharing a VID/PID.
2. **Recovery and overwrite boundary:** inspect the real bootloader, cap wiring,
   PA23 startup behavior, upload padding/erase range and reset paths. Establish
   SWD access and a repeatable recovery procedure before bootloader changes.
3. **Application USB experiment:** motor-disabled application execution and
   enumeration through the cap, with stock recovery preserved. If the bootloader
   prevents entry, record that result before adding USB software to the product.
4. **Offline conformance:** shared codec vectors across host/device languages,
   malformed lengths/keys/fragments, generation conflicts, duplicate commands,
   unsupported schema and corrupted banks. Measure target resource use.
5. **Transactional hardware checks:** disconnect/reset at every update/config
   stage; determine state after reconnect; verify previous-bank survival,
   wear policy and image/config migrations.
6. **Camera interaction:** A7C II selection/metadata verification, clean
   startup/shutdown, fault behavior and timing with diagnostics/persistence
   enabled. Never assume host configuration and camera operation can coexist.

The design must reject these shortcuts: HID availability implies application
access; CHECK proves what was installed; a bootloader ACK proves integrity; a
backup guarantees unbrickability; a higher-level async task eliminates flash
stalls; selecting Rust makes the schema portable; changing EXIF fields produces
optical calibration; and a metadata edit is necessarily a configuration-only
write on current hardware.

The principal unresolved issue is reachable application management mode. The
recommended modular boundaries and versioned semantics stand regardless of its
outcome; the final product's settings backend must be selected from measured
hardware behavior.
