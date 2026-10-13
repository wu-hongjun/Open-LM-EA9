# AF 2.9 focus/capture failure — October 12, 2026

**Camera acceptance failed; further AF 2.9 trials are held.** The owner reports
that focus is achieved, but trying to take a photograph immediately freezes the
camera. Switching off did not recover it; battery removal was required. The
adapter remains on the camera. These observations fail capture and shutdown
acceptance regardless of the unreported focus/exposure settings.

## Owner observations

1. “it achieves focus but immediately freezes the camera when trying to take a photo.”
2. “I had to remove the battery, it is still on the camera”

Focus achievement is an owner observation. The actual focus mode, focus-lock
indicator, latency, hunting, saved image and sharpness are unverified; this is
not a controlled AF-S pass. The intended initial cycle used A/MF/Pre-AF Off,
EV 0/Auto ISO and physical f/1.4/focus infinity. Those requested settings are not
confirmed observations. The exact half-press/full-press onset, preview before
capture, displayed aperture, physical iris position, motor stop and saved-photo
exposure remain unknown. No repeat is needed to accept the failure.

The owner was instructed to stop, switch off and remove the battery if
unresponsive, then not restart or retry. Battery removal was subsequently
confirmed. Keep power removed while taking the adapter off the camera. No
further camera attempt, USB operation, restoration or replacement upload was
performed in this investigation.

## Preserved installation evidence

[Upload and strict reconnect verification](af-29-upload-2026-10-12.md) remain
successful for transaction `E7434D17-4224-4EAD-A76F-BF8AE959B30F`, image SHA-256
`c5fac2eeb7b8c26833b37555f25598352c850f224dba1d091379c09cd9a6ffc3`.
Both complete flash/auxiliary read passes and the separate offline audit
matched the pinned image/profile, known metadata and protected data. This
establishes the installed bytes, not camera compatibility. The original stock
recovery bundle, fresh pre-upload stock backup and previous failed candidates
are preserved. Stock has not been restored after this AF 2.9 failure.

Release diagnostics do not write flash. Battery removal loses volatile runtime
state, so a later cap backup cannot recover the failed bus exchange, UART error
or interrupt timing. No live A7C II capture traffic is available. The observed
focus response does not establish that the 2.8 fault cause is resolved.

## Capture-time protocol investigation

Upstream's pinned protocol research documents an a9 II shutter-time init-class
sequence: `0a 0b 1b 28 19 19 28 0b 0a`. It also describes strict request/response
for init class. Its full aperture request payload is explicitly unresolved.
This is a useful investigation target, not the owner's captured A7C II traffic:
see [upstream 0x1b](../../references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x1B.md)
and [session structure](../../references/upstream/weiziqian/E-mount-protocol-RE/README.md).

[The new offline probe](../../scripts/investigate-capture-boundary.py) compares
actual custom responder code with original stock instructions at a finite
receive-window boundary. [Sanitized evidence](af-29-capture-boundary-2026-10-12.json)
records these results:

- Original stock: with initialized mode 4, phase 3 and callbacks explicitly
  seeded, the actual CS-rise callback `0x53a4` sets the phase interlock. The
  actual delayed status06 sender `0x54d8` then sends nothing. A closed-window
  positive control sends one 48-byte status06.
- Custom: after synthetic initialization, a supplied CS rise followed by a VD
  callback and foreground poll sends both status05 and status06 while the
  receive window remains open. Closed-window status service also works.
- In a second ordering, CS rises in the gap after status05 has completed. The
  custom responder still sends status06. This is the more direct comparison to
  the factory delayed-status06 boundary above.
- All nine synthetic capture requests are serviced in strict request/response
  order, including the fixed f/1.4 aperture reply. Every transmitted frame has
  a valid length, checksum and terminator. This does not reproduce the freeze.
- A single receive-window guard inserted only into an ignored host copy
  suppresses the open-window sends while preserving closed-window service and
  all nine replies. **It still sends status06 when the window opens during the
  inter-frame gap.** An entrance-only guard is therefore insufficient even for
  these finite fixtures. Production firmware and the pinned image are unchanged.

The original fixtures cut lower UART/RX setup helpers and use dummy registers;
the custom probe supplies immediate transmission and callbacks, including a
CS rise at the host delay boundary in the 300 us status gap. It does not
run the complete main loop, real sensor/motor service, concurrent IRQs, physical
timing, full capture request grammar or camera. ASan/UBSan passed. The guard
control validates sensitivity to the scheduling difference and exposes the
remaining inter-frame ordering gap; it is **not** a
qualified firmware patch or full factory phase-machine implementation.

An earlier singleton reply-slot concern is not classified as a demonstrated
legal-traffic bug: feeding several unanswered init requests would violate the
documented strict request/response contract. Without actual traffic or factory
admission evidence, adding a FIFO alone is not a justified capture fix.

## Next firmware gate

Prioritize modular capture-time arbitration and the recovered factory receive/
transmit interlock. Cover requests arriving during status05, the inter-message
gap and status06; distinguish final boot initialization from later 0x0a capture
exchanges; preserve exact request snapshots, bounded timing and successful-send
ownership. Require the same healthy link to service shutdown from every phase.
Use original-instruction phase transitions as the baseline and add adversarial
event-order fixtures before building another candidate. No gain, aperture/EV
correction, motor-fault reset or unbounded retry is justified by this report.

Any replacement requires offline regression, a separate authorized upload,
physical cap reconnect and strict byte verification, then loaded-lens display/
saved-exposure/lifecycle acceptance before a bounded AF-S/capture test. No
replacement image is declared ready by this investigation. Factory parity
remains unqualified.

Raw local state snapshots and probe products remain under ignored private
evidence directories. Only sanitized observations, counts, hashes and contracts
are committed. See [the structured camera result](af-29-camera-failure-2026-10-12.json).
