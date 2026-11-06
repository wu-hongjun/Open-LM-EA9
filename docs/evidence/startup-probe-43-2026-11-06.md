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
result in native HID inventory and the macOS USB device tree. No additional
camera test was requested. The handshake log remains unread, so there is no
evidence of whether a record was written or where startup stopped.
