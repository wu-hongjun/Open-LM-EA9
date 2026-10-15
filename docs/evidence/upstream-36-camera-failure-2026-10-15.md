# Upstream AF 3.6 — A7C II capture and shutdown failure

**Camera acceptance failed; further 3.6 camera trials are held.** The complete
3.6 image had passed strict physical-reconnect verification and an independent
offline audit before camera use. That USB result remains valid; it did not
establish camera compatibility. [Installation record](upstream-36-upload-2026-10-15.md).
[Sanitized evidence](upstream-36-camera-failure-2026-10-15.json).

## Owner observation and known limits

The owner reports inability to take a photo, slight motor movement when trying
to focus, a frozen camera on shutter press and shutdown nonresponse. This fails
capture and shutdown acceptance. The actual MF/AF setting, Pre-AF, aperture
display, half/full-press stage, saved-file status, physical ring settings and
battery removal were not confirmed. Motor movement does not establish focus
lock or optical accuracy. The reported result cannot be labeled a completed
controlled MF exposure test or AF-S comparison.

The owner was asked to stop, remove the battery if unresponsive, and not retry
or restart for missing details. The owner then reported reconnecting the lens
to the computer. In the existing cap-return context root interpreted that as
the adapter returned to its USB update cap; native read-only backup found a new
qualified connection to the same unit. Camera power-off/battery action itself
remains an unverified owner observation.

## Which implementation this is

3.6 uses the pinned [weiziqian upstream C implementation](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9)
at `d52ed06cc449918f938e0695fbf29a0c4141f2b2`, with our separately reviewed
source hardening and fixed lens/build/version configuration. It retains the
upstream controller, gains, maps and aperture policy. It is a modified upstream
fork, not an unmodified upstream binary and not the earlier recovered factory
PID wrapper. The [3.6 manifest](../../firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json)
and [release evidence](upstream-36-handoff-2026-10-15.md) bind its provenance.
The separate [direct 3.1 baseline](upstream-31-camera-failure-2026-10-14.md)
previously failed with aperture `--` and blocked shutter, while shutdown worked.
No Rust firmware was involved in either image.

## Read-only evidence after the failed cycle

The reviewed app0.19/build23 CLI saved a fresh native backup: 131,072 flash
bytes, two matching flash/auxiliary passes and 4,359 CHECK/READ exchanges, with
no upload, erase, restore or retry. An independent offline audit validates every
file against its size/digest manifest and compares the same unit's strict
pre-camera readback. **All changes are confined to `[0x9c00,0xa000)` diagnostic
storage.** All other flash, user row, calibration and device-ID data match.
The immutable 3.6 application prefix matches. A changed diagnostic tail is
expected and does not constitute a new pristine-image verification.

The offline decoder finds **13 valid pages, zero invalid or semantically
inconsistent pages, and three erased pages**. One writer-consistent snapshot
retains all **48 planned first/last events**, with **6,429 evictions**; it is
not a complete history. Summary state is connected with the handshake flag set,
zero reported UART errors and the first sticky fault **`servo-wrong-way`**.
These are software breadcrumbs, not camera-side acknowledgements or electrical
measurements. CRC/writer consistency is not authentication.

The retained endpoint includes a successful-return shutdown echo followed by
the UART-disable/flush marker. Therefore this snapshot reached that software
boundary; it did not remain indefinitely in servo or pre-echo shutdown work
at its endpoint. The marker precedes later PA23 work and does **not** prove
that the body received the reply, that PA23 completed or that the camera powered
off. The owner-reported camera hang remains a failure.

The wrong-way reason records the first sticky motor inhibit, with no fault-time
sensor/target/duty samples. It can account for subsequent inhibited motion,
but its timing relative to shutter press and its physical cause are unresolved.
It does not justify reversing motor polarity, importing a saved factory origin,
retuning gains or declaring it the capture-freeze cause. The limited retained
history does not reconstruct the complete shutter exchange.

Raw dumps, unit identity, camera frames/operands and full decoded records remain
private. Public evidence contains sanitized names, counts, digests and limits.

## Disposition

Hold further 3.6 camera trials. App guidance now shows this known
failure and disables ordinary 3.6 installation while retaining backup and recovery
access. Existing firmware images, pins and original stock recovery remain exact.
Astra32 independently reviews the surviving trace and exact production call sites;
any later fix requires a concrete discriminating test and a new candidate version.
No additional flash or stock restoration follows from this observation.

## Host hold and remaining observation boundary

App **0.19.1/build24** is built and signed with the hold. The existing workflow
test fails against the prior app in three intended assertions, then all **53
Swift tests** pass after the change. The old app/CLI/bundles are preserved
privately. The packaged CLI remains byte-identical to the reviewed 0.19 CLI;
its hash is `781231a3e6b6ef29e442cef982f92e4eb158d805ac315d226bf112eeb332d394`.
No transport, image-builder or firmware bytes changed.

[Astra32's independent review](../audits/astra-32-af36-capture-failure-2026-10-15.md)
confirms that v2 seals its snapshot before flushing: a later shutdown-tail fault
cannot update that record. Absence of a later fault does not prove the tail
completed. Current source also suppresses motion-completion publication after
inhibition; whether the body was waiting on completion is unproved. These limits
require a narrower observation plan before another firmware remedy claim.
