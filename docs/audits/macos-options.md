# macOS application and host tooling audit

Research date: October 10, 2026. This is a recommendation for the system-design
decision, not an approved stack selection or a working application. It follows
[the confirmed product direction](../product-direction.md). No updater was run,
no device transaction was attempted, and no third-party tool was installed.

## Recommendation

Use **Swift with SwiftUI for the product app, selective AppKit integration, and
a small native IOHID transport**. Keep presentation, device transactions, profile
semantics, and update/recovery policy in separate modules. Choose the firmware
language on its own evidence. If Rust wins the firmware audit, share a narrowly
scoped Rust codec/validation library where it demonstrably prevents divergence;
do not move the whole app into Rust to achieve a single-language stack.

This is an engineering judgment for a **macOS-only, approachable hardware
utility**, not a measured performance ranking. Native controls and platform
integration reduce the amount of custom macOS behavior we must build. SwiftUI
can incorporate AppKit views through
[NSViewRepresentable](https://developer.apple.com/documentation/swiftui/nsviewrepresentable),
and standard AppKit controls have built-in accessibility support. That does not
remove our responsibility to test custom flows, labels, focus order, and status
announcements. [Apple accessibility guidance](https://developer.apple.com/documentation/appkit/accessibility-for-appkit)

The decisive unresolved risk is **what service the USB update cap exposes**.
The known transport speaks a bootloader update/read protocol. A new GUI cannot
create runtime configuration commands or live telemetry in that bootloader.
Framework selection must not hide this limitation.

## Constraints established by the references

The [reference uploader](../../references/upstream/weiziqian/E-mount-impl-on-Techart-EA9/tools/ea9flash.py)
uses Linux hidraw, unnumbered 64-byte HID reports, VID/PID `0483:575A`, a CHECK
exchange, addressed READ requests, and a sequential START/DATA upload. Its
macOS port needs a different transport implementation. The READ response is raw
flash data, not a framed response with an echoed command; upload ACKs also lack
the transaction information we would design into a new protocol.

Bootloader-reported version, image identity, camera-facing version, profile
revision, and calibration revision must be represented separately. A cached
stock image does not establish the currently installed image. A CHECK response
does not verify a profile or a completed installation. The user's A7C II and
actual adapter have not been tested by this project.

The camera-facing E-mount protocol is separate from our host-management
contract. The Mac normally configures the adapter in an update-cap session;
the camera operates the adapter in a camera session. Whether custom application
firmware can run and expose USB management through that cap remains a hardware
research question. Concurrent camera/USB operation is not an established feature.

## Viable stack comparison

These judgments assume the current macOS product goal. They should be revisited
if Windows/Linux support becomes a requirement or the maintainers have strong
existing expertise in another toolkit. No binary-size, energy, or development-
time measurements have been made.

| Candidate | Product fit | Hardware/core integration | Main costs and uncertainty | Decision |
| --- | --- | --- | --- | --- |
| SwiftUI + selective AppKit; Swift host core | Strong fit for Mac forms, menus, file workflows, keyboard use, and accessible controls | Direct system IOHID APIs; typed async session layer; pure Swift codecs can be tested independently | SwiftUI custom views still require accessibility work; some detailed table/window interactions may need AppKit; Mac-focused tooling | Preferred starting point |
| SwiftUI/AppKit + narrow Rust core | Same native presentation; useful shared byte codecs, image checks, and validation if Rust firmware is chosen | Static Rust library behind a small C ABI or generated bindings; Swift owns hardware/lifecycle | Two build systems, FFI ownership, errors, toolchain compatibility, and architecture slices; bindings need a prototype | Preferred conditional variant when sharing has a concrete benefit |
| Rust egui/eframe + hidapi | Effective engineering/diagnostic UI and rapid custom plots; cross-platform opportunity | Rust host logic; macOS hidapi backend already uses IOHID | Custom-drawn interaction must prove Mac keyboard/menu/text behavior; native dialogs and packaging still need integration | Good laboratory tool candidate; product UI only if it passes the same usability gate |
| Tauri + web UI + Rust backend | Strong if web expertise, a shared web design system, or cross-platform delivery becomes central | HID stays in Rust/native backend; typed commands/events bridge the UI | Web UI/native behavior work, webview differences, IPC capability policy, Rust and JS dependency maintenance | Viable alternate, weaker fit for current Mac-only scope |
| Qt C++ / Qt Widgets or Qt Quick | Mature desktop toolkit, native integration and cross-platform controls | Native IOHID or hidapi; C/C++ firmware-library reuse possible | Framework/plugin deployment, module license selection, C++ build and ownership discipline; toolkit controls are not individually AppKit controls | Good alternate for an experienced Qt team or broader platform mandate |
| Swift/AppKit-first | Strong native desktop fit; detailed control of windows, tables and responders | Same Swift host layers and IOHID boundary | More imperative presentation code and bookkeeping | Valid fallback for individual screens; no need to commit the whole app initially |

**egui accessibility is supported.** Current eframe documentation enables
AccessKit by default, so dismissing it as inaccessible would be incorrect.
Support in a framework is different from verified VoiceOver behavior for our
forms, progress, and diagnostic plots. [eframe feature documentation](https://docs.rs/eframe/latest/eframe/)

**Tauri is a system-webview application.** Its macOS webview is supplied with the
OS; it does not substitute native AppKit controls for ordinary HTML forms. HID
access belongs behind the backend command boundary. Tauri provides capability
and permission checks, but our command implementations still own device
selection, bounds, and transaction correctness. Ship local UI assets and keep
device operations unavailable to arbitrary remote content.
[Webview versions](https://v2.tauri.app/reference/webview-versions/),
[runtime authority](https://v2.tauri.app/security/runtime-authority/)

**Qt has a real macOS accessibility bridge.** Qt's documentation also makes
clear that Qt Widgets are not each a wrapped native control. `macdeployqt`
packages frameworks and plugins, including the accessibility plugin. Select
the exact modules and license model before adopting it; Qt offers commercial,
LGPLv3, and GPL options depending on the component.
[Mac-specific behavior](https://doc.qt.io/qt-6.8/macos-issues.html),
[deployment](https://doc.qt.io/qt-6/macos-deployment.html),
[licensing](https://doc.qt.io/qt-6/licensing.html)

Electron, Flutter, Python GUI stacks, and other managed desktop toolkits could
also implement this product. They offer no currently identified requirement
that changes this shortlist: we have neither a web/mobile UI to reuse nor a
multi-platform mandate. This is scope triage, not a finding that those toolkits
cannot work. Add them to a measured bake-off if a maintainer skill or new
distribution requirement makes one competitive.

## Recommended module boundaries

| Module | Owns | Does not own |
| --- | --- | --- |
| Mac presentation | Lens library, profile editor, device summary, operation progress, errors, diagnostics views | Raw HID reports or firmware offsets |
| App state/model | Saved profile revisions, pending changes, confirmed device snapshots, selection and navigation | Inferring installed state from UI intent |
| Device session | Endpoint lifetime, exclusive transaction ownership, deadlines, reconnect generations, command routing | Presentation or optical calibration guesses |
| Native HID transport | Enumeration, descriptors/properties, open/close, report ID normalization, callback lifetimes, report delivery | Profile meaning or update policy |
| Management codec | Explicit message encoding/decoding, lengths, versions, capabilities, errors | OS APIs, retries, GUI state |
| Bootloader adapter | CHECK/READ/upload semantics of the preserved stock bootloader | Pretending those exchanges implement the new management contract |
| Profile/image validation | Units and ranges, schema migration, image partitions, compatibility, release identity | UI controls or arbitrary binary patching |
| Update/recovery coordinator | Preflight, backups, prepared image, install plan, verification and durable operation record | Hiding incomplete verification as success |
| Profile and evidence store | Versioned local profile documents, backup images, diagnostic bundles, provenance | Flash calibration defaults for unknown lenses |
| CLI/analysis tools | Repeatable developer operations using the same tested host boundaries | A required command-line step for normal app users |

The protocol specification and golden vectors are the durable cross-language
contract. Sharing source code is an optimization, not a prerequisite. A Swift
codec and C/Rust firmware codec must pass the same valid, boundary, corrupt,
and version-mismatch vectors. Do not serialize a compiler's in-memory struct
layout onto the wire.

### Swift/Rust integration decision

If Rust firmware is selected, make a short prototype of a **synchronous,
pure-data** Rust library called by Swift: parse a profile/configuration block,
validate an image, encode/decode management messages. Keep Core Foundation/HID
objects, UI objects, callbacks, and cancellation out of that first boundary.
Expose explicit byte buffers, results, and ownership/free functions; contain
panics before they cross FFI. Build required architecture slices and lock the
Rust and binding tool versions together.

[UniFFI](https://mozilla.github.io/uniffi-rs/latest/swift/overview.html) generates
Swift bindings and is a credible option for a larger typed API. Its current
guide documents partial Swift 6 support and an async `Sendable` gap. That is a
reason to test the exact pinned release, not to claim integration is impossible.
A small C ABI can be simpler for a handful of stateless functions. Large,
asynchronous, cross-language objects would need considerably more lifecycle and
cancellation testing. Begin with one owner for device I/O, not simultaneous
Swift and Rust transport implementations.

If firmware is C/C++, a C-compatible library can also be imported into Swift.
Only share code that is cleanly separated from register access, board memory,
interrupt assumptions, and the upstream global state. Do not couple the host
app to the full firmware build or raw peripheral headers.

## HID integration and transaction correctness

Apple's user-space IOHID API supports report transfers. The installed SDK
headers were inspected read-only at
`/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk/System/Library/Frameworks/IOKit.framework/Versions/A/Headers/hid/`:
`IOHIDManager.h` declares device matching/removal callbacks and dispatch-queue
scheduling; `IOHIDDevice.h` documents blocking SetReport/GetReport functions and
input-report callbacks. This establishes API availability, not LM-EA9 access
on a packaged application. [IOHIDDeviceSetReport](https://developer.apple.com/documentation/iokit/1588656-iohiddevicesetreport)

Implement the transport around a dedicated callback queue or an explicitly
owned run loop. Keep synchronous HID calls off the UI thread and avoid blocking
Swift's cooperative executor. Copy callback data into owned bounded buffers,
retain contexts and buffers until cancellation completes, and deliver typed
events to the device session. The hidapi macOS backend is a useful independent
implementation reference for IOHID usage and disconnection handling.
[hidapi macOS backend](https://github.com/libusb/hidapi/blob/master/mac/hid.c)

Report IDs are part of the **transport binding**, not the bootloader payload.
Linux hidraw and hidapi output APIs require a leading zero for unnumbered
reports, while native IOHID accepts a report-ID argument and has its own buffer
convention. Normalize this once and test exact report sizes. Do not prepend a
Linux zero byte blindly to the native 64-byte payload. Numbered input reports
must also be handled according to the observed descriptor.
[hidapi public report API](https://github.com/libusb/hidapi/blob/master/hidapi/hidapi.h)

An endpoint must match more than a convenient VID/PID. Record observed usage,
interface/report descriptors, available strings and serial number, then verify
the expected CHECK exchange before presenting it as a compatible device. An
absent or nonunique serial number is possible; do not invent a permanent unit
identity from an ephemeral registry path. Multiple matching devices require
explicit selection.

Give each session a connection generation and **one complete in-flight
transaction**. A Swift actor protects state from data races, but its async
methods can interleave at `await`; actor isolation alone does not make
CHECK/READ/upload indivisible. Reserve a transaction before sending, reject or
queue competing operations, route reports only to that transaction, and release
ownership on terminal outcomes. Guard post-await changes against generation
and operation IDs. [Swift actor reentrancy](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0306-actors.md)

Define timeouts at the whole operation and each reply boundary. Malformed or
short reports are errors. A READ reply has no address echo, so an uncertain
timeout/late report cannot be safely reattributed to a new address merely by
sending another READ. Mark the session unsynchronized and require a tested
resynchronization procedure; a new local operation ID does not magically tag
old bootloader replies. Likewise, do not blindly retry an ambiguous upload
chunk whose ACK carries no offset. The prototype must establish what recovery
the actual bootloader permits.

Unplug, sleep/wake, app quit, and USB re-enumeration are state-machine inputs.
Task cancellation means a request to stop; it is not proof that the device
stopped a destructive operation. Future installation flows need a defined
critical phase, a bounded completion/recovery policy, and an operation record
that survives a crash. Do not automatically resume writes after reconnect.

## Profiles and ordinary-use experience

Store user profiles locally as versioned, inspectable documents, with atomic
replacement, import/export, immutable profile IDs and revisions, explicit units,
and a migration policy. A small library does not need a database or cloud
account initially. Device backups and diagnostic evidence belong in a separate
store with hashes and provenance. Unknown required schema versions should
remain viewable or preservable without becoming installable by accident.

Separate lens metadata from optical calibration and from per-unit mechanism
calibration. Profile display names are not Sony lens IDs. Nominal maximum
aperture is not the current manual aperture. The app cannot observe the user's
aperture or focus ring through the passive adapter. The zoom needs a manually
chosen active focal length; the macro needs an explicit focus-reference setup.
Use the user's inventory unchanged until exact model details are established.

The main flow should be: choose a lens, edit metadata, review the resulting
profile, connect the device in its supported configuration mode, apply through
an available capability, and see a verified result. The UI must distinguish
**saved on this Mac**, **pending for the adapter**, **read back from the
adapter**, and **tested on the camera**. This is useful user information, not
an implementation checklist. An offline edit must never show an adapter as
already updated.

If only the existing bootloader is reachable, profile activation initially
requires installing a prepared custom firmware/configuration image. The app
can make that straightforward, but must describe the actual installation and
verification result. A new management service with atomic configuration writes
would improve the flow if hardware evidence supports it. Keep both behind
capability-driven operations so the UI does not promise unavailable behavior.

Use a conventional sidebar for Lens Library, Device, and Diagnostics; show
firmware updates/recovery as a device operation. Keep advanced optical rows,
controller tuning, and raw traces out of the ordinary metadata form. Expose
calibration provenance and confidence in an advanced view. A diagnostic plot
also needs a readable summary/table/export for users who cannot interpret the
visual chart.

## Distribution and maintenance

Recommend direct distribution of a Developer ID-signed, hardened-runtime,
notarized application with a stapled ticket. Apple documents signing,
timestamp, and notarization requirements; these apply to all shortlisted
frameworks, not just native Swift apps. A released app should work without
Homebrew, Python, Rosetta as an accidental dependency, or a terminal command.
[Apple notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

App Sandbox is required for Mac App Store distribution and is distinct from
Hardened Runtime. Apple's USB entitlement permits a sandboxed app to use USB
access APIs. Test the actual signed/sandboxed build against this HID endpoint;
do not assume generic documentation resolves every access question. There is
no evidence here that this vendor HID device needs a custom driver, a privileged
helper, or Input Monitoring permission. Do not build those components or request
those permissions speculatively.
[Sandbox configuration](https://developer.apple.com/documentation/xcode/configuring-the-macos-app-sandbox),
[USB entitlement](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.device.usb)

Choose the minimum macOS version from the intended machines and supported APIs
before implementation. Test the oldest supported release as well as the current
release. Support Apple Silicon natively; if Intel support is promised, build
and test its actual app and every native-library slice. Cross-compilation alone
does not validate a hardware workflow. A Rust core, Qt plugin, or bundled CLI
must be included in the signing and packaging checks.

Treat Mac app updates and adapter firmware updates as separate operations.
Authenticate release metadata and firmware artifacts on the host, perform
compatibility checks, and verify installed bytes where the bootloader permits.
Host artifact verification is useful even when the stock bootloader cannot
enforce signatures; it does not make that bootloader secure boot. A firmware
CRC/hash is also not proof of trusted origin. Profile-specific image generation
needs an explicitly authenticated base release and validation of the generated
configuration/image, not an arbitrary official-binary offset patch.

Lock dependencies, preserve notices, maintain a module inventory, and separate
normal support bundles from raw personal file paths and optional traces. App
telemetry or cloud accounts are not required by the current product scope.

## Staged prototype and acceptance gates

These are proposed future experiments. None has been executed in this audit.

| Stage | Prototype | Acceptance evidence |
| --- | --- | --- |
| A: Offline native UX | SwiftUI lens library/editor, mocked device session, file import/export, simulated progress/errors | All eight supplied lenses fit the model; keyboard-only and VoiceOver paths can edit/save/export; unknown calibration stays unknown; invalid values are actionable; local edits cannot appear as confirmed device state |
| B: Codec/transport harness | Pure codecs, recorded HID fixtures, deterministic fake clock and scripted transport | Exact 64-byte bootloader payloads and report-ID binding; short/corrupt replies rejected; no transaction interleaving; delayed replies, unplug, timeout, and reconnect cannot confirm the wrong operation |
| C: Read-only adapter session | Native IOHID enumeration, CHECK, bounded READ; no START/DATA command code reachable in this build | Capture descriptor and endpoint properties; repeat reads of established valid regions agree; compare app-region bytes/hash with saved evidence without assuming installed version; reconnect/cancel/sleep behavior documented; no firmware/configuration write |
| D: Packaged read-only build | Signed/notarized app with only discovery and backup workflows | Clean-machine install/launch without developer tools; access works with intended entitlements; backup is atomic and labeled with captured identity/version/hash; UI remains responsive and results are accessible |
| E: Conditional shared core | Same codec vectors through Swift and a pinned Rust or C shared-library boundary | Byte-for-byte parity and error parity; no panics/unowned buffers cross FFI; required architecture builds work; measured maintenance benefit justifies the extra toolchain |
| F: Configuration/update simulation | Capability negotiation and durable operation coordinator against a device emulator | Reject incompatible images/profiles; prepare an exact reviewable installation plan; acknowledged progress differs from read-back verification; interruptions preserve an honest recovery state; writes remain simulated |

Read-only acceptance requires **CHECK and READ alone** on the real adapter.
USB output requests that ask for a read are expected; START and firmware DATA
must be unavailable. Read only ranges established for this bootloader, with
explicit bounds. Preserve the bootloader and stock recovery evidence before
advancing to a later write experiment. The existing stock cache is useful
comparison evidence but is not a complete recovery-path demonstration.

If native UI fails a concrete requirement, implement the same offline profile
and mock-device workflow in the strongest alternative and compare on real Mac
keyboard/VoiceOver workflows, file dialogs, progress readability, packaging,
and maintenance. Do not select a toolkit from screenshots or a Rust-only
preference. The system recommendation remains native presentation with explicit
interfaces; shared-language details should follow the firmware and USB findings.
