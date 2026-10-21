# AF 4.1 — separate installation and crash-log procedure

AF 4.1 upload and strict complete-image/protected-data verification passed on
October 21 after owner-confirmed physical reconnect. The
[installation record](evidence/upstream-41-upload-2026-10-21.md) tracks these
completed gates. Camera compatibility remains unqualified. The next step is the
setup part of one camera cycle: confirm actual MF, live preview and quiet idle
before asking for the single photo/shutdown. No camera result is assumed.

[Candidate and pins](../firmware/candidates/4.1.0/README.md) ·
[Implementation and limits](evidence/upstream-41-crash-diagnostics-2026-10-21.md).

## Installation gate

A later explicit upload request must confirm the USB cap, camera disconnected,
TECHART Update and Open LM-EA9 closed. Resolve any pending transaction through the
existing guarded workflow; never edit a journal, reconnect marker or safety lock
by hand. App 0.24.0/build 33 provides the explicit4.1 experimental action and keeps
ordinary4.0 installation disabled. Lens-library edits cannot personalize this
fixed-profile image.

`prepare-crash-upstream` selects only 4.1; `apply-crash-upstream` selects the same
pinned bytes through the existing fresh two-pass backup, stock qualification,
durable upload journal and reconnect guard. Historical commands keep their original
images. Never use apply, inventory, inspect or verify as an offline build check.
The state-directory option does not isolate the canonical hardware guard/lock.

After upload, stop sending reports until the owner physically unplugs/reconnects
and explicitly confirms. Strict verification must compare the entire 20,480-byte
application including the pristine 1024-byte diagnostic tail, known metadata and
protected flash/auxiliary windows against the prior backup. Use only established
metadata scratch exclusions. Independently audit saved files before camera use.
A decoded log or matching version is not installation verification.

## One owner-coordinated cycle, after verification

The test prompt requests one cycle and captures actual menu settings in two
steps within that same power cycle. First confirm actual MF, preview and idle
without shutter/AF-ON input; only after review request the single photo/shutdown.
Do not restart for the second step.
The prior owner's word AUTO does not establish exposure or focus mode. With the
A7C II off and its USB cable disconnected, mount the LM-EA9, C/Y-to-M converter and
50mm f/1.4; physical focus infinity and physical iris f/1.4. Switch on without
shutter/AF-ON input. Check live preview, brightness and aperture, expected f/1.4.
Use powered-on menus to set still-photo A, EV 0/Auto ISO, **separately confirmed MF**,
and Pre-AF Off if available. Do not restart for setup.

Wait ten seconds after movement stops. Only if preview/aperture/motor behavior is
normal and MF is confirmed, take **one** photo; otherwise skip it. Switch off once,
leave it off and do not try AF-S or restart. Record saved-file status, exposure,
preview, displayed aperture, movement/idle, actual settings and shutdown; unknown
settings remain unknown. A subsequent AF test needs review of this cycle and logs.

For grinding, repeated stop impacts, abnormal continuous drive, or a frozen body,
stop input and switch off. Remove the battery if unresponsive or motion continues;
do not keep a moving fault powered to obtain logs. There is no guaranteed log if
power is removed before the watchdog/reset append. A quiet CPU stall may yield a
watchdog record after approximately four seconds, but this timing is unmeasured,
the camera may remain frozen, and a camera-only stall can keep the firmware health
loop running. Do not repeat a failed attempt to fill missing observations.

After the camera is off/unpowered and motor stopped, return the adapter to its
USB cap, physically reconnect with both apps closed, and explicitly confirm. A
crash-latched adapter intentionally will not initialize its motor or camera
protocol on another boot. Preserve evidence before considering recovery. No
automatic re-home, reset loop, erase, reflash or stock restoration is provided.

## Read-only retrieval and interpretation

Use the existing guarded two-pass backup and save raw data privately. Compare
against the verified installation: only `[0x9c00,0xa000)` may differ. Protected
flash and auxiliary data must match. Decode saved files offline with:

```
python3 scripts/decode-startup-diagnostics.py PRIVATE_BACKUP --output NEW_PRIVATE_JSON
```

The registry independently binds the complete4.1 image, manifest and immutable
prefix. Type5 is a standalone boot record, not an ordinary summary, physical boot
counter, complete camera exchange or shutdown acknowledgment. A zero-payload
baseline proves that a valid boot record was programmed; it does not prove
append returned or normal initialization completed. A recovered record preserves
the last validated foreground summary and reset-cause bits; SYST is not unique to
HardFault. No exact PC/LR, motion snapshot or event history is retained in that page.
UART byte/error/status, pins and buffered/planned counts may be zero or stale until
terminal flush; do not interpret them as measured zero activity.

A CRC-invalid occupied page latches storage damage. CRC-valid crash records latch
future boots. No later records are trusted past either barrier. Earlier ordinary
summary/motion/event/footer pages retain their version-bound association rules.
Missing records, a baseline only, or erased storage cannot establish a fault's
location or absence. Preserve raw output and document evidence before changing
firmware; restoring an image clears the diagnostic tail and therefore its latch.
