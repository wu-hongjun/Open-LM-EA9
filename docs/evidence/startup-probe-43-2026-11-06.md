# Startup probe 4.3.0 on the Sony A7C II

## Installation

At the owner's request, the adapter was updated through its USB cap with
TECHART Update and Open LM-EA9 closed. The source-built native CLI exported
the exact [pinned 4.3.0 image](../../firmware/candidates/4.3.0/README.md).
The original same-unit stock 1.8.0 backup was independently validated before
upload. The read-only preflight matched the exact 4.2.0 application and bound
the two-pass backup to the qualified unit.

The uploader saved the recovery journal before START, acknowledged one START
and 320 pages, and stopped after the last page. The transfer completed at
20:32:05 UTC on November 6. The complete 20,480-byte application SHA-256 is
`58e5eb9578732e6fa8113a28f8b1732a6edc30706333871bbc207ae66e20abac`.
A separate file audit checked the image, source backup, and expected loader
metadata. Raw backups, unit identifiers, and the recovery key remain private.

## Strict verification after reconnect

The owner confirmed a physical USB reconnect. At 20:52:42 UTC, strict native
readback and a separate file audit verified the same unit on a new connection.
Two matching flash and auxiliary passes used 4,359 read exchanges and no writes.
All 20,480 application bytes matched, including the erased 1,024-byte log area.
The expected 58 loader metadata bytes, boot code, saved records, upper flash,
user row, calibration, and device ID matched. The established six loader
scratch bytes at `[0x403a,0x4040)` are outside the planned metadata comparison.

## Camera observation

The owner tested the adapter on the A7C II and reported that it did not
take a photo or focus. Live preview, displayed aperture, and shutdown
behavior are unknown. Shutter and AF-ON use during the test are unverified.
The probe omits motor drive and full capture handling, so these observations
leave the handshake outcome unresolved. The adapter was returned to the cap.

## Log retrieval

The first post-camera attempt found one qualified cap on a fresh USB
connection. A report failed during the first flash pass at 20:55:19 UTC,
after the last displayed progress of 56%. The loader halted the read and
published no backup. No writes were sent.

After the owner physically reconnected, the read stopped before any reports
because the Mac detected no adapter. A later reseat was followed by the same
result in native HID inventory and the macOS USB device tree.

The owner then reconnected the cap and the Mac detected one qualified device.
At 21:01:03 UTC, a scoped native read completed under the existing reconnect
and exclusive-access guards. It bound the connection to the same adapter,
confirmed USB version 4.3.0, and matched the bootloader, loader metadata and
immutable application prefix against the verified pre-camera baseline. Two
reads of the 1,024-byte diagnostic tail matched. The recovery used 594
read-only exchanges and sent no writes. The interrupted full backup remains
incomplete. The scoped read did not recheck upper flash or factory auxiliary
regions after the camera session.

## Decoded trace

Two records passed the version, slot, semantic and CRC checks. The other 14
pages are erased. Times below are probe SysTick milliseconds within each boot.

| Slot | Startup and normal traffic | Terminal result |
| --- | --- | --- |
| 0 | Capabilities and identity replies completed locally. The final 25-byte `0x0A` arrived at 191 ms. Its echo reached UART TXC at 192 ms and released lens CS. A `0x05/0x06` status pair completed, and the first normal receive was a 29-byte `0x03` at 219 ms. | `tx-fault` at 15,822 ms. The record counted 809 VD edges, zero invalid windows, zero drops and zero UART error events. |
| 1 | No body CS rise or fall, valid exchange, or bus-ready flag. The probe saw two VD edges. | `first-close-timeout` at 8,000 ms. The source of this separate recorded boot is unknown. |

**The A7C II reached normal protocol traffic in the recorded camera
session.** The 4.3.0 configuration used stock identity and a UART configured
for 750 kbaud. Receipt of `0x03` after the final echo shows progress beyond
the initial handshake. It does not establish capture, autofocus, or shutdown
compatibility, and the measured result does not identify the difference that
caused the separate 4.2.0 failure.

The terminal transmit fault happened after startup. In the
[transport code](../../firmware/startup-probe/main.c), an init/control reply
or either status packet can reach the same terminal reason. The zero drop
count excludes the pre-TXC abort path for an init/control reply because that
path increments the counter. It leaves a post-TXC init/control failure and
the status transmit failure paths open. The candidate freezes the init
markers after the final echo, so `0x0A` is the last completed *init* exchange
and carries no evidence that it was the later failed packet. The record
cannot distinguish a collision with body CS, a UART wait budget expiring,
or an interrupted post-TXC hold. It carries no evidence that the fault
coincided with shutter input or shutdown.

The next diagnostic boundary is the transmit failure during normal operation.
A follow-up trace needs the failed message ID, whether TXC was reached, and
body CS/VD state at entry, on abort and at lens CS release. Keep the slot 1
no-CS boot separate from this result. Raw reads and connection identifiers
remain private.
