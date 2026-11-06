# A7C II compatibility: November upstream trial

The owner reports that the verified November build did not work on the A7C II.
The [maintainer's open compatibility issue](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/issues/1)
explicitly reports incomplete initial handshake on the A7C II, A7 IV and A7 V.
It gives no failing packet, logic trace, or confirmed fix. The owner's latest
failure report establishes a failed camera trial; it does not by itself locate
that attempt in the handshake, capture, AF or shutdown sequence.

The [USB readback](../evidence/upstream-november-trial-2026-11-06.md) verified
the exact `e054db9` application and protected data. It did not observe the
E-mount link. This release has no persisted startup trace. Neither repeating
the USB readback nor adjusting the motor gains can identify where that attempt
stopped. No USB access, new camera attempt, firmware change or restoration was
performed for this investigation.

## Reproduced on exact application source

The [probe](../../firmware/upstream-hardening/followup/58-november-handshake/run.py)
checks the pinned image/manifest and all built source hashes before compiling
the real protocol, packet tables and optical-file units with the upstream
host shim. Two independent materialized builds produced identical
[results](../../firmware/upstream-hardening/followup/58-november-handshake/results.json)
under AddressSanitizer and UndefinedBehaviorSanitizer. Pins, UART delivery and
time are supplied by the shim; no body-side validation or electrical timing
is simulated. The reports do not contain a real camera frame.

| Boundary | Observed in the replay | Diagnostic value |
| --- | --- | --- |
| First receive window | A complete, valid `0x01` already buffered when startup observes body CS high gets cleared by `em_uart_rx_reset()`. The identical packet delivered after that reset gets a reply. A later retry also gets a reply. | If there is no `0x01` response, check the power/pin sequence and whether the first UART bytes precede that reset. The [3.2 startup work](../evidence/upstream-32-startup-diagnostic-2026-10-15.md) had already reproduced this class of loss in the earlier upstream build. |
| `0x0C` speed negotiation | The trial replies `01` at 750 kbaud and requests the switch to 1.5 Mbaud even when the expected body CS rise or fall never arrives. The waits expire without communicating success/failure to the caller. | If the last valid reply is `0x0C`, check both sides' CS transition and decode `0x0B` at the negotiated rate. Stock's `00` reply stays at 750 kbaud. The faster switch is a new difference from the earlier stock-speed line; it cannot explain all older failures. |
| Final `0x0A` and status | A six-byte `0x0A` header lacking a valid frame trailer is queued. The echo handler rejects the invalid length, but `em_poll()` sets the handshake flag and sends `0x05/0x06` on the next sync. A valid final request is echoed byte-for-byte in the control. | A software “handshake done” bit can be false confidence. Check the valid echo on the wire and the body's subsequent traffic. |

The [protocol project's A7 IV sequence](https://github.com/weiziqian/E-mount-protocol-RE/blob/faded04cebd84afb43cc9dcadf6eebe115aacd49/README.md#the-a7-iv-firmware-most-steps-are-optional)
selects optional requests from both parties' advertised capabilities. With
the candidate's advertised bits and a supplied good speed-change pulse, the
control emits framed replies to all 11 requested init IDs, including `0x3F`
and `0x3D`, then a status pair with nominal f/1.8. That is evidence against a
missing handler in **that supplied sequence**. It does not establish that the
A7C II sends the same sequence, accepts all reply fields, or sees those
replies by its deadline. `0x2B` is an [adapter re-identification exchange](https://github.com/weiziqian/E-mount-protocol-RE/blob/faded04cebd84afb43cc9dcadf6eebe115aacd49/docs/msg_0x2B.md),
absent from the documented initial sequence. Its removal in
[e054db9](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/commit/e054db90cfae5d67fac67a7e0db4bb100f5893ae)
does not by itself address either startup boundary.

Stock and the trial also take different identity paths. The trial reports a
native-style class and third-party ID `0xC540`; stock reports adapter class
and ID `0x00EA`. The author's [A7 IV lens ID analysis](https://github.com/weiziqian/E-mount-protocol-RE/blob/faded04cebd84afb43cc9dcadf6eebe115aacd49/docs/lens_id.md)
shows that third-party IDs change how that body interprets init data and which
requests it makes. That makes identity an experimental variable, not proof
of an A7C II blacklist. The [stock-speed exchange](https://github.com/weiziqian/E-mount-protocol-RE/blob/faded04cebd84afb43cc9dcadf6eebe115aacd49/docs/msg_0x0C.md)
and stock identity should be kept together for a clean comparison.

## What would locate the actual fault

The A7C II is capable of using this adapter hardware. Stock has captured on
it; the [earlier motor-disabled application](../evidence/camera-50-metadata-2026-10-10.md)
also saved a photo with correct lens metadata. The
[4.1 trace](../evidence/upstream-41-camera-failure-2026-10-21.md) captured one
startup CS-rise timeout and, in a separate cohort, valid-looking progress
through normal traffic. This supports investigating startup and later capture
as separate failures rather than assuming every freeze has one cause.

The next discriminating evidence is the **first exchange that differs from
working stock on the same A7C II**. A passive trace from power-on should cover
body/lens CS, VD and both UART directions through `0x01`, `0x0C/0x0B`, final
`0x0A` and first `0x05/0x06`, with actual clock rates and elapsed time. If
`0x0A` and status really complete, move the investigation to the first capture
and re-arm boundary instead. No old failure needs to be repeated just to
collect the camera settings.

With only the USB cap, the closest substitute is a separately authorized
motor-disabled startup probe with a bounded, nonblocking diagnostic record.
Keep stock identity and 750 kbaud in the first comparison. Measure the last
valid RX, TX completion and readiness before enabling either native identity
or the high-speed exchange. The persisted record must never be required for
boot; [4.1's full diagnostic storage could prevent startup](firmware-reassessment-2026-10-23.md).
The [4.3.0 startup probe](../../firmware/candidates/4.3.0/README.md) implements
that experiment. Its offline evidence separates validated RX, local TXC and
CS release, and the first normal RX. The A7C II boundary still needs a camera
observation.

Reproduce after materializing the pinned build using the
[November builder](../../scripts/build-upstream-november-trial.py):

```sh
python3 firmware/upstream-hardening/followup/58-november-handshake/run.py \
  --checkout CHECKOUT --build PINNED_BUILD --output artifacts/private/november-handshake-replay
```
