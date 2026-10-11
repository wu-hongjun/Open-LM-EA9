# Management-mode entry proposal

October 10, 2026. Design proposal following the measured USB-cap investigation.
No bootloader patch, custom firmware upload or application launch has been
performed. The product stack remains a candidate decision.

Current equipment is USB only. Reconnect repeatability and unchanged flash
are now evidenced, while independent recovery and electrical measurements
remain pending. See [the USB-only boundary](usb-only-next-steps.md) for the
development work that can proceed with the existing connection.

## Decision and alternatives

Prefer evaluating a **small launch extension to the existing bootloader** for
the original USB cap, after qualifying independent recovery. This is the
shortest proposed path to a service that edits profiles without rewriting the
whole application. It follows the demonstrated stock startup gate; an
application USB driver alone cannot pass that gate.

| Approach | What must change | Evidence still needed |
| --- | --- | --- |
| Stock loader and image-embedded profiles | Host prepares a recognized custom application containing the selected profile bundle | Camera firmware, uploader erase footprint and complete install/read-back qualification; every settings change remains an image update |
| Small bootloader launch extension, preferred investigation | An explicit capability/launch handler and deferred main-loop handoff; custom application gains a management lifecycle | Independent restoration, patch space/control-flow review, USB cleanup, reset behavior and motor-disabled execution |
| Alternate cap/mode arrangement | Measured wiring selects application startup while retaining USB data/power; application can distinguish this mode | Cap continuity, PA23 levels/source impedance, a reliable mode signal, power behavior and absence of output contention |
| Replacement bootloader | New update, recovery and application-entry implementation | Much broader bootloader qualification, power-loss behavior and restore testing; unnecessary for the first entry experiment |

Measured flash protection being disabled makes a launch extension conceivable.
It does not establish that an update transport can safely modify the bootloader:
the stock START route targets metadata at `0x4000` and application bytes at
`0x5000`. It is not a demonstrated arbitrary bootloader programmer.

## Preserved layout and responsibilities

Preserve vectors at zero, the stock metadata area at `0x4000`, and application
vectors at `0x5000`. Do not move the application entry point for the first
experiment. The original loader's upload state machine remains separate from
management entry. Preserve original loader bytes and hashes for restoration.

Any extension space must be established from the full dump, reachability,
literal/data references and erase-row boundaries. Bytes equal to `0xFF` alone
do not prove a region can be reused. Do not overwrite metadata, calibration,
user-row fuses or historical upper-flash data during this experiment.

The bootloader owns cold-boot recovery, capability discovery, vector validation
and the handoff. The application owns USB descriptors, management requests,
profiles and diagnostics. The host owns disconnect/reconnect handling and
confirmation that the device actually reached the requested mode.

## Proposed entry sequence

1. USB cold boot continues to select the loader. Normal camera boot continues
   to follow its application path. Neither path automatically launches a
   management service merely because the host opened HID.
2. A modified loader advertises an explicit extension version and capabilities.
   The host never guesses a launch opcode on an unmodified device. Existing
   CHECK version metadata does not identify extension support.
3. A bounded launch request is admitted only in idle state, after capability
   discovery and validation of the application manifest and vector pair. Reject
   malformed reports, an upload in progress, an invalid stack pointer, a
   non-Thumb/out-of-range reset vector or an incompatible application.
4. The USB interrupt handler records a pending request and supplies a bounded
   acknowledgement. A replacement for the `0x26F0` main-loop wait processes
   that request after the IN transfer completes. Do not branch to application
   startup from inside the OUT interrupt handler.
5. Quiesce USB transfers, detach, disable/clear owned interrupts and DMA, stop
   peripherals as required, and create a validated management-mode handoff.
   Set the application vector table and stack only within a reviewed assembly
   boundary; the handoff must not return through the loader's old C stack.
6. Application startup consumes the mode indication before clearing its RAM
   state or applying camera GPIO defaults. In management mode it leaves motor
   outputs inactive, keeps PA23 as an input, and deliberately initializes USB
   pins, clocks, calibration, buffers and interrupts.
7. The custom service enumerates with an explicit management identity and
   protocol version. The Mac matches the physical device and confirms its
   capabilities. A timeout is a failed entry, not a successful mode change.
8. A power cycle returns to the loader's recovery default. Define any later
   service-to-loader reset path separately and test it through a full reset.

No command numbers, mailbox addresses, descriptor IDs or timeout constants are
allocated here. Those are implementation choices requiring a memory/linker
map and lifecycle prototype. A mailbox must occupy a reserved RAM region that
both images exclude from initialization; a reset-based alternative must account
for reset cause and retention. Neither can be assumed from the current images.

## First executable qualification

Use a management-only application with no motor initialization. Its initial
operations should be HELLO/capabilities, firmware/build identity, read-only
profile/status and a bounded diagnostic counter. Profile persistence and
firmware update remain later capabilities, admitted only after erase boundaries
and failure behavior are established.

Acceptance requires reproducible cold boot into recovery, explicit service
entry, correct detach/re-enumeration, repeated host close/reopen, cable removal,
malformed request rejection, and proof that motor/PA23 outputs remain inactive.
Test USB suspend/resume and the revision-specific clock errata. Record exact
source/build hashes, binary layout and device traces for every experiment.

Before bootloader changes, locate and measure the SWD/reset/supply connection,
identify the probe and tool policy, and demonstrate repeatable independent
read access without erase/unlock. Restoration qualification is a separate
controlled write experiment with a verified backup. No restoration experiment
was performed in this read-only run.

## Consequences for the product

The Mac app should model **loader**, **management service** and **camera mode**
as distinct states. Show profile editing as a local operation until the selected
device advertises a settings-write capability. Report the device-confirmed
profile separately from pending edits. Offer a backup/export workflow using the
measured loader READ transport before implementing installation.

Keep transport, wire codec, profile model and firmware lifecycle independent.
Swift IOHID with SwiftUI/AppKit remains the preferred Mac prototype; Rust
`no_std` remains the firmware candidate with C as a fallback. The bootloader
extension can use a small separate implementation without forcing the app and
firmware to share a language. Select the stack after a motor-disabled USB
prototype and camera timing/resource measurements.

See [the original investigation](usb-cap-investigation.md),
[the read-only follow-up](usb-cap-followup.md), and
[the system recommendation](system-design-recommendation.md).
