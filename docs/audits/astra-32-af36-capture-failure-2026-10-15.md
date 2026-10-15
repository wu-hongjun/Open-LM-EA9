# Astra 32 — actual AF 3.6 capture failure evidence

October 15, 2026. **The recovered trace records a servo wrong-way inhibit and
successful software progress through the shutdown echo and UART-disable
boundary. It does not locate the shutter freeze or prove camera power-off.**
No firmware change or additional camera trial is justified by this analysis.

The owner reports that the A7C II with Contax 50mm f/1.4 cannot take a photo,
the motor moves slightly when focusing, shutter press freezes the camera, and
shutdown does not respond. Actual MF/AF mode, displayed aperture, physical iris,
Pre-AF, exposure mode, half/full-press distinction, and battery-removal history
remain unknown. The earlier requested procedure is not evidence that those
settings were used. The later computer return is not evidence of how power was
removed. Root owns the hardware evidence and owner communication.

This differs from the recorded 3.1 missing-aperture/no-motor result with normal
shutdown. It resembles the reported 3.0 shutter freeze, but only the 3.0 record
explicitly establishes half-press focus, full-press freeze and required battery
removal. Neither history establishes a common cause for 3.6.

## Evidence identity and limits

The [installation record](../evidence/upstream-36-upload-2026-10-15.md)
establishes strict physical-reconnect verification of the 20,480-byte 3.6 image,
SHA-256 `d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`,
including an erased diagnostic area before the requested camera cycle.
This lane independently matched all 46 materialized source files to the exact
build manifest and matched the image digest. It read the private post-camera
decoder only after root confirmed completion of the native read-only backup.
Root reports two matching flash/auxiliary passes and 4,359 CHECK/READ exchanges;
the decoder reports the immutable prefix matches 3.6. Root separately owns
the full comparison outside diagnostics and protected auxiliary regions.

The [sanitized result](../../firmware/upstream-hardening/followup/32-af36-capture-failure/results.json)
records source pins, counts, event names/IDs and bounded conclusions. No real
frames, payload operands, sequence fields, unit identifiers, calibration or
private dump is copied into this report or result.

The recovered v2 area has 13 valid writer-consistent pages, no invalid,
semantically inconsistent or unassociated pages, and three erased pages. Its
single summary is accompanied by all 48 planned retained events: first 24 plus
last 24. There are **6,429 event evictions/omissions**. A complete retained
snapshot does not mean a complete runtime history. The cohort number is an
append-slot token, not an independently established physical boot count.

## What the actual records establish

| Observation | Narrow interpretation |
| --- | --- |
| Summary stage `connected`, handshake flag true | The trace recorded successful handshake progress at some earlier point. These are historical sticky trace fields; shutdown clears the live handshake flag without clearing the trace's historical flag. |
| Summary fault `servo-wrong-way` | The first retained nonterminal inhibit reason is the wrong-way guard. No associated fault time, command, encoder trajectory, target, drive polarity or duty is stored. |
| 1,614 RX frames and 1,618 TX returns; UART error count/status zero | Substantial parser/transmitter activity occurred. Zero recorded errors does not prove every byte arrived or that the camera accepted any reply. |
| Retained tail contains status `0x05/0x06`, RX `0x03/0x04`, then RX init `0x0a`, TX `0x05`, TX `0x0a` | Protocol service was still active late in the retained history. No owner/raw flag or shutter marker establishes which event corresponds to shutter press. |
| TX `0x16`, followed by `shutdown-uart-disabled` | Software returned successfully from the shutdown transmitter, then reached the powerdown callback after UART disable and persisted the trace. It did not remain indefinitely blocked in the servo or a pre-echo wait throughout this recorded endpoint. |

The transmit records are **successful function returns**, not transmit-start
or independent wire observations. A TX return after an RX event can describe
a transmission already underway when the RX interrupt ran. The final `0x0a`
reply length is also not a discriminator: the ordinary table reply is 25 bytes,
and a raw echo can have the same declared length. The retained RX record stores
the padded receive-window length, not a complete request. Do not reconstruct a
raw-vs-ordinary capture transition from these records alone.

## Exact production paths that explain these limits

In pinned `servo.c:316`, with the reversal-rebase guard inactive, position more
than 120 encoder counts behind the leg start in the requested direction selects
`SERVO_WRONG_WAY`. At `servo.c:456`, that outcome calls
`st_inhibit_fault(ST_SERVO_WRONG_WAY)` and sticky `motor_inhibit()`. This is a
software observation about the supplied encoder coordinates, not a measurement
that establishes reversed physical wiring or a motor polarity defect.

`startup_trace.c:132` stores the first nonterminal inhibit reason in the RAM
summary only. It emits no timestamped event and performs no flash write. A later
terminal `ST_FAULT` before the flush would overwrite the summary fault; the recorded wrong-way
value plus the shutdown marker is consistent with nonterminal inhibition
followed by continued protocol service. The trace cannot date the inhibit
relative to shutter press or identify which motion command triggered it.

Once motor inhibition is set, `main.c:1180` treats motion ownership as invalid.
`focus_run()` returns aborted after the servo; `focus_event()` suppresses
completion publication for invalid motion, and subsequent `focus_exec()` calls
decline to move. This is a concrete route from the recorded guard to stopped
drive and absent motion-completion events. **Whether the camera was waiting for
such an event is unproven**: actual focus mode, release condition and command
records are unavailable. Preserve the inhibit; do not turn this observation
into a proposal to weaken the guard or invent successful completion.

The servo pumps `em_poll()` during its loop. It also has time/work bounds and
shutdown cancellation. A valid init `0x16` is admitted independently of the
ordinary mailbox in `emount.c:727`, revokes readiness, cancels ordinary ownership
and immediately calls GPIO-only motor inhibition. This branch returns before
ordinary `ST_RX` logging. Therefore missing RX `0x16` is expected on this path
and does not contradict the recorded TX `0x16`.

`em_shutdown_ack()` at `emount.c:394` does not park: it echoes the retained
request, sets OFF only after `em_transmit()` succeeds, then calls
`powerdown_signal()`. In `main.c:866` that callback delays 50 ticks, disables
UART, notes shutdown, and flushes. Only afterward does it wait for two low VD
samples (bounded by 500 ticks), set PA23 and delay 100 ticks. **The persisted
marker precedes the PA23 write.** This firmware does not record the later
boundary and does not perform the factory WFI tail. The separately completed
[lane 31 comparison](astra-31-factory-shutdown-tail-2026-10-15.md) describes
those differences; none is newly proven to cause this camera failure.

`st_flush()` seals its v2 snapshot before writing. Thus a later fault or stall
after this successful flush would not create a second updated summary in the
same run. Absence of a later fault is not evidence that the post-flush tail
completed. The camera's reported shutdown nonresponse remains valid even though
the adapter software reached its UART-disable boundary.

## Next evidence milestone

The actual capture hang is **not located**. The new evidence narrows the next
work to two independently observable boundaries:

1. Recover a concrete failing motion trace: accepted command/target, leg start,
   time-ordered encoder coordinates, requested drive sign, retarget/rebase state,
   guard crossing and completion publication. Bind it to the actual shutter
   event and known camera mode. This can distinguish a real feedback-direction
   problem, a stale/incorrect coordinate or retarget interpretation, and camera
   waiting after deliberate motor inhibition. Existing v2 records cannot supply
   these missing fields; no gain/polarity/guard change follows yet.
2. Recover the shutdown boundary after the recorded UART disable: independently
   observed reply delivery, VD behavior, PA23 transition and camera power state.
   This distinguishes a camera protocol wait from failure to reach the later
   firmware/electrical tail. The current marker cannot make that distinction.

These are requirements for a separately reviewed observation plan, not a request
to repeat the failed image. First preserve the completed backup and obtain the
owner's already-observed settings and press/power sequence without a retrial.
Any future instrumentation must retain the motor cutoff, finite waits and
diagnostic storage contract. A concrete trace or reproduction must precede a
firmware remedy claim.

This lane performed read-only source/evidence analysis and wrote only its new
audit and sanitized result. No new synthetic execution was needed; earlier
capture, shutdown, serializer and factory suites are not counted again. No
device enumeration/open, USB/HID, flash, motor or updater/app launch occurred.
An initial overly broad `AGENTS.md` filename search traversed home/Git paths
before being interrupted with no output; no canonical state file contents were
opened or used. Subsequent reads stayed within explicit instruction paths and
the repository source/evidence paths authorized for this lane.
