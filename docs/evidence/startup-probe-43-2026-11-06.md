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

The upload is awaiting the owner's physical reconnect. Strict verification
must pass before the camera test. There are no 4.3.0 camera observations or
logs yet.
