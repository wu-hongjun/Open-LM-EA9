# AF 4.1 — delayed capture, logs preserved, owner requested stock

**Camera acceptance failed; further 4.1 trials are held.** The owner reports an
approximately one-minute delay from pressing the shutter until a photo was taken,
a freeze, and successful shutdown afterward. The owner confirms the photo file
was saved, returned the adapter to the computer, and explicitly requested stock
restoration. Actual MF/AF, Pre-AF, exposure settings, aperture/preview and motor
behavior remain unverified. No extra camera attempt is requested.

[Sanitized receipt](upstream-41-camera-failure-2026-10-21.json) ·
[Strict installation record](upstream-41-upload-2026-10-21.md) ·
[Original-stock recovery](stock-18-af41-recovery-2026-10-21.md).

## Preserved read-only evidence

The 4.1 installation had passed strict full-image/protected-data verification.
One guarded native backup completed at **2026-10-22T01:48:27.531260+00:00 UTC**
(October 21 local), before any restoration. The unchanged signed reader,
SHA256 `2f24feab2fd010a5950d144ae24e31288fe2589248caaae439b438db609b14bc`,
used a new qualified USB-cap connection with both apps absent by process check.
Two matching 131,072-byte flash passes and two auxiliary passes completed:
4,359 CHECK/READ exchanges, no writes or retry. The owner’s return statement and
qualified descriptor/new connection establish the return context; no missing
focus setting is inferred from the requested setup instructions.

Independent filesystem checks validate every file size/digest, boot code, MCU,
geometry, unit binding and version. Code and all flash outside the 1K diagnostic
tail are unchanged, as are user row, calibration and device-ID windows. Canonical
journal, applied setting, firmware observation, stock qualification, library and
blocked-connection membership remained unchanged during retrieval.

Before camera flash SHA256:
`9dd187a9259879010d59ce4cca6d1aaff562b8d2a02b688524ce8a6d6da1f9f0`.
After camera flash SHA256:
`490aee27c5dcfb639f62a5108b346ec1bfa430ce911e4bb1b80d23a2d59ff7b5`.
There are 1,023 changed bytes, all within `[0x9c00,0xa000)`. All 16 diagnostic
pages are valid and associated with no semantic inconsistencies. Storage is full.
All 49 source pins, 156 release/recovery/pin artifacts, registry entries and original
stock recovery remain exact. Raw dumps, keys, identifiers and real frames stay private.

## What the trace establishes

Five standalone boot records occupy slots 0, 1, 2, 3 and 14. Each records raw reset
cause 1 (power-on), with no recovered foreground checkpoint. These are programmed
boot boundaries; their append cohorts are not a physical cycle counter and do not
identify who or what caused a reset. No WDT/SYST recovery record survives. Their
absence does not prove the watchdog was functional, nonfunctional or never fired.

The slot-4 summary records a completed handshake, 228 received frames and 230
local TX returns, no sticky fault, and UART disabled during shutdown. Its sealed
snapshot is at 2,355 software milliseconds. It retains 16 events from 32 buffered,
with 35 earlier ring evictions and 16 capacity omissions; the retained window is
incomplete camera traffic. There is one accepted raw-capture offer, one shutdown
admission, and three TX starts / three TX returns. These local software observations
are not body acknowledgments or proof of which shutter attempt produced the file.
The three motion pages are complete but contain no initialized normal-servo move;
that does not exclude homing or other movement outside that collector.

Two later footers record VD-timeout and the PA23-write boundary at 2,856 software
milliseconds. There is no tail-delay-return footer. A timeout, missing footer or
pin-write breadcrumb alone does not prove physical power removal or a camera hang.

The final slot-15 summary records **`cs-rise-wait`** at 8,000 software milliseconds,
stage 8, before handshake: zero received frames/TX returns and one UART error.
It has room for its summary only; its one buffered event and terminal footer do
not fit. This is concrete evidence of a bounded startup chip-select-rise wait
failure in that recorded boot. It does not establish the earlier one-minute shutter
root cause. Software ticks across different boot cohorts cannot be added into
that owner-reported wall time or mapped to a specific shutter press.

The full tail is itself a limit: the candidate intentionally prevents another
normal application start when a baseline cannot be appended. That may affect
later use, but these records do not establish whether exhaustion caused the first
reported delay. The owner’s shutter input occurred before MF setup was confirmed;
this is not relabeled a controlled MF cycle or AF-S test.

## Disposition

No further custom-firmware camera test is requested. At the owner’s explicit
request, the original same-unit stock 1.8.0 restoration and strict complete-slot /
protected-data verification passed after physical reconnect. The completed
[recovery record](stock-18-af41-recovery-2026-10-21.md) retains the evidence. The camera backup was
preserved first and the native uploader saved another matching fresh backup before
START. Stock restoration does not diagnose the custom runtime failure or resolve
previous stock aperture/exposure limitations.

App 0.24.1/build 34 marks 4.1 held and disables its ordinary installation from any
installed version. Read-only backup/recovery and historical explicit command/image
pins remain. Five intended assertions fail against the old app; the fix passes
all 53 named Swift tests and signed packaging without launch. The signed reader
is byte-identical, and the prior signed app/CLI/bundles are preserved privately.
No firmware source, image, journal or safety rule was edited to bypass this failure.
