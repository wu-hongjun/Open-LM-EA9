# AF 3.0 full-press freeze — October 14, 2026

**Camera acceptance failed; further AF 3.0 trials are held.** The installed
Contax Zeiss 50mm f/1.4 image passed [strict USB verification and a separate
offline readback audit](af-30-upload-2026-10-14.md). That result establishes the
installed bytes, not camera compatibility. No further hardware report, firmware
upload or stock restoration was performed after these failure reports.

## Owner observations and stop instruction

1. “it focuses correctly but freezes the entire camera upon shutter press”
2. “battery removal is required, still on camera, half press triggered the focus,
   full press freezes the camera, no photo was saved.”

The second observation identifies **full press** as the freeze trigger, confirms
half-press focusing, failed shutdown requiring battery removal and no saved
photo. The adapter was still on the camera at that report. Current battery/
power state and motor stop remain unverified. The owner was told to stop,
switch off, remove the battery if unresponsive or motion continues, keep the
camera unpowered and not restart/retry AF 3.0. Moving it back to USB or restoring
stock was not requested as a prerequisite for this investigation.

The initial requested test was A / MF / Pre-AF Off, but actual focus mode,
Pre-AF, exposure settings, physical iris/focus ring and displayed f-number were
not reported. Do not relabel this as a controlled MF capture or AF-S comparison.
Reported focus achievement is preserved; it does not establish optical sharpness,
lock indication, saved exposure or full firmware acceptance. No photograph was
saved, so an EXIF path or repeat shot is not required. The successful USB result
and all earlier AF 2.9 failures remain recorded independently.

## What the offline investigation establishes

The previous capture checks correctly tested suppression of status 06 after a
receive interruption and the `0x0a` raw opener. Their synthetic nine-request
sequence did not compare every request/event ordering with factory behavior.
In particular, treating the received **ID** as the sole capture-opener signal
misses the factory's **phase/interruption** transition.

The [new finite replay](af-30-capture-interruptions-2026-10-14.json) executes the
pinned factory instructions at CS callback `0x53a4`, VD callback `0x5120`, raw
sender `0x5260`, TX-complete callback `0x5188` and release callback `0x5280`.
The connected mode is explicitly seeded to 4, the gate to open, callbacks to
enabled and phase to one of 2/3/5/12/13. It supplies checksum-valid 11-byte init
requests for `0x0a/0x0b/0x1b/0x28/0x19/0x34`, with three sequence values.

All **90 original-instruction cases** latch an interruption, select mode 5 on
VD, schedule the raw sender with nominal delay 10, echo the complete request,
schedule release with nominal delay 100, and return to init mode 1. This
transition is not restricted to `0x0a` under those supplied phases. It is also
not a rule to echo every request in every phase.

A sanitized native probe compiles the **exact frozen AF 3.0 source** from
`62ebd177ad5b7cbc76fbf75ebdfb80db7e59bb85`; production units match its build
manifest. It loads the committed 50mm profile, completes synthetic initialization
and injects each request during the 300 us gap following status 05. All six
cases suppress the old status 06, retaining that valid 3.0 behavior.

| Interrupted request | Factory under seeded interruption | Frozen AF 3.0 |
| --- | --- | --- |
| `0x0a` | Raw request echo after VD, then init mode | Raw request echo after VD; match at this boundary |
| `0x0b` | Same raw-echo/init transition | Stored 11-byte reply before VD; bytes differ, then status resumes |
| `0x1b` | Same raw-echo/init transition | Stored 19-byte reply before VD, then status resumes |
| `0x28` | Same raw-echo/init transition | Stored 44-byte reply before VD, then status resumes |
| `0x19` | Same raw-echo/init transition | Stored 10-byte reply before VD, then status resumes |
| `0x34` | Same raw-echo/init transition | Stored 32-byte reply before VD, then status resumes |

Thus five tested non-`0x0a` IDs have a demonstrated reply/ownership divergence.
This is a concrete reason the incomplete scheduler needs more work. It does
**not** establish that the A7C II sent one of those requests at that phase when
it froze, or that correcting this one gap will resolve every capture problem.

## Boundaries and next implementation work

Original register memory and request bytes are synthetic. Lower DMA RX, UART
and timer operations are cuts; deferred callbacks are invoked explicitly. The
custom probe injects CS callbacks from a host delay shim, with immediate UART
completion and no linked motor or actual main loop. Sanitizers cover native
memory/undefined behavior, not electrical timing or MCU IRQ interleavings.
The generated frames have valid framing/checksums; their full payload grammar
and the actual A7C II shutter traffic remain unrecovered. This does not increase
the semantic-model union or establish whole-factory reconstruction.

The next candidate needs modular phase-driven interruption/echo/init ownership,
with adversarial comparisons across the relevant status phases and both control
and normal traffic. It must preserve the working interruption suppression,
request snapshots, successful-send publication, event tails, bounded shutdown
and homing/fault guards. Capture-side aperture acknowledgement remains a separate
compatibility boundary to audit; this result does not prove aperture caused the
freeze or justify a guessed exposure compensation.

No production firmware, template, prepared candidate or recovery artifact was
changed by this investigation. No new firmware candidate was built or uploaded.
A new candidate must be prepared/tested and uploaded in a separately authorized
step before another camera trial. Require preview/MF capture/shutdown acceptance
before bounded AF-S; do not retry this failed image to obtain missing settings.

Reproduce offline from the repository root, with the pinned Unicorn environment
and full Git history containing the AF 3.0 release commit:

```sh
tools/rea-analysis/venv/bin/python scripts/investigate-af30-capture-interruptions.py --output /new/interruption-check
```

The output path must be new under an existing parent. Only the checksum-pinned
public original application, frozen repository sources, public lens profile and
authored fixtures are used. No device, USB, private calibration or recovery key
is accessed. [The result record](af-30-camera-failure-2026-10-14.json) keeps owner
statements, verified facts and unknowns separate.
