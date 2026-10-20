# AF 3.8 — drive-phase homing fault and blocked further photos

**Camera acceptance failed; further 3.8 trials are held.** The owner reports
hunting, apparent focus for one photo, then a motor reset and no further photos.
**Shutdown was normal.** This attempt is not recorded as another camera freeze
or battery-required recovery. A fresh read-only backup identifies
`home-drive-unsettled` (17), with code and protected data unchanged. The physical
homing cause and later shutter-block cause remain unresolved.

[Sanitized receipt](upstream-38-camera-failure-2026-10-20.json) ·
[Verified installation](upstream-38-upload-2026-10-19.md) ·
[Candidate](../../firmware/candidates/3.8.0/README.md) ·
[Offline homing repair](upstream-38-readiness-2026-10-19.md).

## Owner observations and read-only retrieval

The owner confirmed return to the USB cap with both apps closed and authorized
retrieval, analysis, documentation, commit and push. The first report was
truncated; a retrospective clarification established no further photos after
the reset, normal shutdown and **AUTO exposure mode**. Actual MF/AF-S/AF-C,
Pre-AF, aperture/exposure values and whether the first photo file was saved
remain unverified. No image/EXIF was inspected and no extra camera attempt was
requested. This cannot be labeled a controlled MF lifecycle test or AF-S
comparison. AUTO exposure does not identify focus mode.

Preflight verified the unchanged signed reader CLI (app 0.21.0/build 27, SHA-256
`1d993380476f6d7797398d2304f36ea0a6f162a45bb7db73762f13db25194d9c`),
image/verified journal, no competing updater/app/CLI and one qualified adapter
on a new unblocked connection. Inventory sent no reports. One native
`backup PRIVATE/after-camera.ea9backup --idle` completed two matching 131,072-byte
flash reads and two auxiliary passes: 4,359 CHECK/READ exchanges, exit 0 at
**2026-10-20T13:23:55.658809+00:00 UTC** (**09:23:55 America/New_York**).
No write, erase, upload, restore or retry was sent.

An independent filesystem audit checked all backup files, sizes/digests, boot
identity, MCU geometry, same-unit binding and the prior pristine readback.
Exactly 896 bytes changed: the fourteen diagnostic pages in slots 0–13. Every
flash byte outside `[0x9c00,0xa000)`, user row, calibration and device-ID window
is unchanged. Canonical pending/applied/firmware-observation records and the
blocked-connection set are unchanged. No state or safety marker was manually
edited. All 49 reconstructed source digests and all 136 inventoried historical
release/recovery artifacts still match, including original stock recovery.

Post-camera full-flash SHA-256:
`479e95c3ff4d3954d75af2afaffb6199846da016ffe9c32ea254b0344594173d`.
The historical pristine installation remains verified as recorded; this
post-camera backup allows diagnostic differences and is not a new full-image
installation verification. Raw dumps, unit identifiers, frames and operands
remain private.

## What the retained cohort establishes

The registry-bound decoder finds 14 valid pages, zero torn/invalid, inconsistent
or unassociated pages, and two erased pages. The one writer-consistent cohort
contains a complete planned snapshot: all 32 planned focused events and three
motion chunks. There are zero capacity omissions, but 35 older focused events
were evicted and 9,424 routine observations were filtered/summarized. Complete
means the retained plan survived, not that the whole bus history was captured.
The cohort identifier is an append-location identifier, not a physical boot count.

The summary records 1,180 received frames, 1,182 local TX returns, zero reported
UART errors, handshake observed, and the UART-disable boundary. Its retained
fault is **drive-phase homing failure 17**. This distinguishes the branch from
settle failure 18 and shared work-budget exhaustion 19. In the pinned source,
`motor_home()` did not establish its drive-stillness qualification before the
300-SysTick-unit cap: at least 40 units of drive and 40 of qualifying stillness,
with a six-count stillness threshold and a final deadline recheck. A pump that
returns after the deadline can produce this result too. These are software
quantities; the logs contain neither the fault occurrence time nor the homing
encoder trajectory. They do not identify noise, end-stop arrival, stiction,
polarity, pump duration or physical elapsed time.

The failed path leaves reference readiness false, inhibits motion and prevents
normal focus execution until reboot. That source behavior explains a path to
unresponsive focus after the fault; it does not prove why the body blocked the
shutter. The 144-byte servo collector is entirely zero and writer-consistent:
no instrumented AF-servo move was initialized in this cohort. Homing drives
outside that collector, so this does not contradict the owner's motor movement.
Owner-perceived optical focus and a reported photo do not prove that the normal
AF controller acquired focus. The phase marker does not locate the observed
motor reset in time.

3.8's operand-query liveness fix remains source-bound and passes its offline
controls. These retained logs do not observe enough query detail to independently
prove the repair on hardware. No motor guard, timeout or controller was changed
for this investigation.

## Capture ownership and shutdown

Four ordinary owners and one raw owner were accepted/taken/completed with
successful local sends in the retained valid session. All six TX START/RETURN
pairs match immutable identity/flags/session: four ordinary, one raw and one
shutdown. There is no unmatched retained START or RETURN.

The raw-classified request uses the **readiness type**. Its local echo completes
with the same session, then disables periodic status; no later ordinary
readiness owner is retained before shutdown. The explicit shutdown admission
occurs one software tick after that raw completion. This places the retained
exchange close to the shutdown path, not necessarily at the first shutter
press. Raw classification is a software ownership decision, not proof that a
photo was captured. Local TX return is not camera acceptance. The records cannot
map the owner-observed first photo/reset or later shutter attempt to a particular
wire exchange.

A fresh bounded original-stock-instruction probe changes only the existing
[Astra43 factory replay](../../firmware/upstream-hardening/followup/43-capture-status/factory_replay.py)'s
synthetic raw request to readiness type. Across seven capture/re-arm cycles,
raw readiness echo still returns to initialization/silent mode; ordinary
readiness afterward re-arms connected status. The original stock application,
oracle/config and lane04 inputs remain pinned. The private adapter suppresses
only the historical public receipt write and records its own digest. This
confirms the prior raw-echo policy under the supplied state; it does not prove
physical scheduling, boot reachability, all caller behavior or camera parity.
Automatically treating raw readiness as ordinary readiness is not justified by
this trace alone.

Shutdown acknowledgement returned locally, followed by UART disable, VD timeout
and the PA23 software-write boundary. No 100 ms tail-return footer is present,
although two append slots remain. That absence cannot distinguish power removal,
interrupted delay, a failed append or another terminal interruption, and does
not prove a shutdown hang. The owner's normal shutdown is a separate observation;
PA23 breadcrumbs do not measure pin voltage or body power state.

## Disposition and next discriminator

Keep this image held and the adapter on the USB cap. Two free pages cannot
retain another full event/motion snapshot; no repeat camera test is requested.
No firmware was changed or flashed and no stock restoration was performed.
The next offline investigation should distinguish drive-phase deadline crossing
from failure to establish encoder stillness, using bounded phase/workload
instrumentation without relaxing reference or motor guards. The raw-readiness
classification/caller path remains a separate bounded comparison; it must not
be identified as the first shutter event without evidence.

App 0.21.1/build 28 records the 3.8 hold, disables ordinary 3.8 installation from
other versions, and preserves read-only backup/recovery access, explicit
historical CLI meanings and every firmware pin. The prior signed app/CLI are
retained privately. Packaging/signature and host-test results are in the receipt;
the app is not launched and canonical state is not manually changed.

Physical homing, sustained capture, optical AF and factory parity remain
unachieved. This investigation narrows the homing branch and preserves a fuller
trace; it does not establish a new firmware remedy.
