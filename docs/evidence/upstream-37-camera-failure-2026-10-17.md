# AF 3.7 — A7C II camera failure and retained traces

**Camera acceptance failed; further 3.7 camera trials are held.** The owner
reports some motor movement, failure to achieve focus, and one photo taken
followed by a freeze. A read-only backup preserves the diagnostics. The prior
[strict installation verification](upstream-37-upload-2026-10-17.md) remains a
valid pre-camera result; it did not establish camera compatibility.

[Sanitized machine-readable evidence](upstream-37-camera-failure-2026-10-17.json) ·
[Independent Astra reviews](../audits/astra-40-41-af37-camera-trace-2026-10-17.md)

**October 19 follow-up:** the owner independently repeated the trial and reports
two photos before another freeze. A fresh read-only backup adds a second
`home-failed` summary and VD-timeout footer in the final two free pages. Details
for that later cohort were omitted for capacity; the older trace below remains
separate. [Repeat-cycle evidence and full-storage limit](upstream-37-repeat-camera-failure-2026-10-19.md).

## Owner observations and remaining unknowns

The first response was “Still very janky, I reconnected the adapter to the
computer.” The owner then clarified: “some motor movement, but did not achieve
focus, one photo was taken and then freeze.” No further test was requested.
Actual MF/AF mode, Pre-AF, aperture/exposure settings, whether a photo file saved,
its exposure, exact shutter stage, shutdown outcome and battery removal remain
unverified. Requested settings are not treated as observed settings. This was
not a completed controlled MF exposure test or AF-S comparison.

In the existing cap-return context, the response confirms returning to the USB
cap with the updater/app closed. Preflight found no competing processes, one
qualified adapter and a fresh unblocked connection. The backup confirms the same
unit on a new connection. Camera shutdown/battery actions are not inferred from
the cap return or from firmware breadcrumbs.

## Read-only backup and independent comparison

The signed app0.20.0/build25 native CLI saved 131,072 flash bytes with two matching
flash passes, two auxiliary passes and 4,359 CHECK/READ exchanges. It exited 0 at
**2026-10-17T17:34:38.197797+00:00 UTC**. No upload, erase, restore or retry
occurred. Post-camera flash SHA-256:
`1cab0426a0f96cd10c3a18747e380609d1f7d8806349bb499f49794f99a5691f`.

The independent filesystem audit checks every backup size/digest, boot identity,
MCU geometry, same-unit binding and the exact strict pre-camera readback. All
896 changed flash bytes are within `[0x9c00,0xa000)` diagnostic storage. All flash
outside that area, the immutable 3.7 code prefix, user row, calibration and
device-ID data match. The installed 3.7 image/manifest and every one of the 131
historically inventoried release/recovery/pin files remain unchanged.

The native operation leaves the pending/applied/firmware-observation files
unchanged. The canonical blocked-connection **set** is unchanged; native JSON
serialization reordered its entries. An initial private audit compared those
JSON bytes, reported the mismatch, and was retained. The corrected audit compares
set semantics and separately records the serialization-only change. No journal
or safety marker was manually edited. Decoder prefix matching is diagnostic
identification, not a replacement for strict pristine-image installation checks.

## What the retained trace establishes

The pinned offline decoder finds **14 valid pages, zero invalid, inconsistent or
unassociated pages, and two erased pages**. One writer-consistent snapshot has
all **32 planned focused events** and all three motion chunks. It evicted 35
earlier events and filtered/summarized 8,592 observations; the complete retained
window is not the complete camera history. Summary state is connected with the
handshake flag set, zero reported UART errors and first sticky fault
**`home-failed`**.

The homing marker has several possible software failure branches: drive-phase
deadline/stillness failure, settle-phase deadline/stillness failure, or the
shared iteration budget. This trace does not distinguish them. The marker's
occurrence time and homing trajectory were not retained. After this failure,
the source inhibits motion, leaves reference readiness false and refuses a
homing retry. That is consistent with subsequent lack of achieved autofocus;
it does not establish the physical cause or the cause of the camera freeze.

The motion structure is all zero. Homing drives the motor directly and does not
initialize the instrumented AF servo/deadband collector. Therefore this is
compatible with the reported movement; it does not mean no motor movement
occurred. No wrong-way servo snapshot was recorded in this retained cohort.

Four ordinary owners and one raw capture owner are accepted, taken and
successfully completed in the still-current session. All six retained TX
START/RETURN pairs match immutable identities and flags: four ordinary replies,
one raw echo and one shutdown echo. Raw completion precedes shutdown admission,
the shutdown echo returns, and the UART-disable boundary is retained. This
window shows neither raw echo nor shutdown acknowledgement locally pending.
“Raw capture” is the firmware classification, not a verified shutter stage;
local TX return does not prove camera receipt or acceptance.

The terminal chain retains **VD-timeout**, then **PA23-write-reached**. There is
no tail-delay-return footer. Two erased pages rule out simple log-capacity
exhaustion; interruption, power loss or failed persistence can still omit the
footer. These records do not prove a delay hang, changed pin voltage, completed
camera shutdown or a saved photo. The owner-reported freeze remains a failure.

## Host hold, validation and disposition

App **0.20.1/build26** now labels installed 3.7 as held and blocks ordinary 3.7
installation, while retaining read-only backup/recovery access and historical
CLI/image meanings. The existing production-workflow regression rejects the
previous app in four intended assertions; after the hold change, all **53 Swift
tests pass**. Offline packaging/signature verification passes. The app was not
launched and canonical user state was not modified by the host tests/build.
The CLI remains byte-identical to the readback CLI, SHA-256
`b9c9f77f80ef80e0fd59c97de0d878d62ef68fd5a30b7d1fe4995479a4cf8e67`.
The previous signed app/CLI/resources are preserved privately.

Astra40 and Astra41 independently verify all 49 source hashes and review homing
and capture/shutdown respectively. Neither establishes a new causal defect or
a justified motor-polarity/timeout/guard change. Their next offline discriminators
are exact-source homing under communication workload and a replay of post-echo
status/shutdown ordering. These experiments are proposed, not claimed executed.

Keep the adapter on its cap; do not repeat the failed 3.7 camera trial. No new
firmware was flashed or stock restoration performed. Raw dumps, unit identifiers,
camera operands and complete decoded records remain private. Any behavioral
remedy requires a separate candidate/version and its own evidence and hardware
gates; stable capture, autofocus, shutdown and factory parity remain unachieved.
