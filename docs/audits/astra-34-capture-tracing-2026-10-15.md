# Astra 34 — AF3.7 capture ownership observation proposal

October 15, 2026. **Offline observation work is staged and its synthetic checks
pass. This does not fix or locate the reported AF3.6 capture hang, establish
factory parity, or qualify a camera trial.** Root owns integration, the final
image size/stack gates, decoder acceptance and any later hardware authorization.

This lane read the [actual failure audit](astra-32-af36-capture-failure-2026-10-15.md)
and [closed campaign record](../evidence/firmware-hardening-final-2026-10-15.md).
The exact base is `artifacts/private/handoff36-repeat`, equal to the published
3.6 manifest; all 46 manifest source pins and the image digest were verified
before and after the source-bound tests. AF3.6 image SHA-256 is
`d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`.
Base `emount.c` is
`57fe9dfe08068db6a2f4596faf27371b74881f84573b79facca4d728cd349d41`;
the staged instrumented file is
`2e469f4a7f30e93ad4431bb2505ebc5ba5a0d1c66644a04c0dc34fcb49f5aa59`.

## Delivered scope

The [applicator](../../firmware/upstream-hardening/followup/34-capture-tracing/apply.py)
requires the exact base `emount.c`, accepts only a private `src` directory, and
refuses to mutate `handoff36-repeat`. It modifies only the copied `emount.c`.
The [RAM helper](../../firmware/upstream-hardening/followup/34-capture-tracing/trace.inc)
uses lane35's `st_note` API and event IDs 11–18, and lane33's
`st_motion_completion` API. The production source, release files, protected
upper flash and the diagnostic range are unchanged by this lane.

| Boundary | What the new observation establishes |
| --- | --- |
| CS rise, after `em_owner_cs` | Whether the status phase caused the incoming window to become a raw capture window; no unparsed frame is copied. |
| Init request offer | Opcode, request sequence, full session generation, raw/ordinary classification, queue admission or rejection, and active/pending ownership state. Session opening is recorded after the existing generation increment. |
| Foreground take/retry | Immutable request selected for control service and active slot. A repeated take can be a retry; this is not an independent receive. |
| TX START | Admission succeeded inside the existing mask, immediately before lens CS assertion and `em_uart_send`. This is a software commitment boundary, not a measured first UART bit. |
| TX RETURN | `em_uart_send` succeeded and the existing hold/release path finished. Identity, owner flags and session are saved at START and reused here even when RX executes during the transmission. A failed send has START without RETURN. |
| Control completion | Send result, raw/ordinary owner, current pending/status state and whether the original session still owns completion. Failed or stale requests cannot be mistaken for a successful readiness publication. |
| Capture phase end | The foreground phase was cleared; RAW records the then-sampled capture latch. This local phase-end event is not an atomic snapshot of every owner field. |
| Shutdown admission | Accepted init `0x16`, after the existing readiness revocation, cancellation and GPIO-only inhibition. This branch still returns before ordinary `ST_RX`. |
| Motion event queue | Capacity admission or full-queue rejection, followed separately by successful return of a status transmission carrying the snapshotted event code/parameter. Main-level attempted/suppressed publication belongs to lane33. |

The motion queue marker is recorded inside the existing publication lock before
the bounded queue insertion; it means queue capacity admitted the event. Its
later `ST_MC_TX_RETURN` means successful software transmission return, not
camera receipt. The event code/parameter are captured when the status tail is
constructed, so a session/shutdown IRQ cannot relabel an earlier transmission
using the later queue contents. No raw whole frame or payload is added to new
public records.

No protocol template, transmitted byte, action order, cancellation rule,
callback, original lock/unlock boundary, time/work budget, or hardware read was
changed. Added trace calls execute bounded RAM work and read the existing
`millis()` clock. Calls inside existing masks increase masked execution time;
software parity does not establish physical interrupt latency or wire timing.
Flash writes remain solely in lane35's explicitly allowed terminal flush/tail
paths, outside bus/ISR tracing.

## Schema and interpretation

All owner events store full wrapping session32 as `length | operand << 16`.
The event `id` is opcode, `seq` is sequence, and `cls` is the flag byte. These
fields have new meanings for kinds 11–18; they are not v2 length/operand fields.

| Bit | Meaning |
| --- | --- |
| `0x01` RAW | Captured raw request, or sampled capture latch for CS/phase. |
| `0x02` CONTROL | Control owner for TAKE/START/RETURN. **For COMPLETE only**, original session still equals current session. |
| `0x04` SHUTDOWN | Shutdown already requested at the observation. START/RETURN keep the value from admission. |
| `0x08` PHASE | Status phase active. |
| `0x10` SLOT | Active slot is one; absence means slot zero. This is not a globally unique request number. |
| `0x20` PENDING | Pending request present. |
| `0x40` STATUS | Status publication enabled. |
| `0x80` RESULT | OFFER: admitted. COMPLETE: successful send return. SHUTDOWN_ADMIT: accepted. Unused for other kinds. |

`ST_OWNER_CS=11` is rising only, identity zero. `ST_OWNER_OFFER=12` and
`ST_OWNER_TAKE=13` use the request opcode/sequence. `ST_TX_START=14` and
`ST_TX_RETURN=15` use the sent opcode and **owning request sequence for control
transmissions**, because ordinary template replies can carry a different wire
sequence. Status and shutdown transmissions use their snapshot wire sequence.
`ST_SHUTDOWN_ADMIT=16` carries the shutdown request identity and fixed accepted
shutdown flags. `ST_OWNER_COMPLETE=17` uses the original request/session;
its STATUS and same-session bits explain readiness publication or suppression.
`ST_OWNER_PHASE=18` has identity zero: begin is PHASE|STATUS, end is RAW if the
capture latch remains set, otherwise zero.

Session/sequence/opcode/slot plus ordered admission and take events identify
ownership within a retained slice. Sequence and slot can repeat, and session
wraps; missing records are not a license to join unrelated events. Neither a
raw opener nor any event here is an independently observed shutter press.

Lane35 owns the filter exactly once. It omits nonraw owner CS/phase events and
noncontrol, nonshutdown START/RETURN events from the focused ring, while legacy
`ST_TX` continues to count all successful returns. Its latest-32 ring and
explicit filtered/evicted counts remain bounded. Ordinary status traffic
therefore cannot by itself evict the capture opener. A long sequence of
retained control events can still evict older observations; a complete retained
slice is not a complete runtime history.

## Verification and limits

The [source-bound test results](../../firmware/upstream-hardening/followup/34-capture-tracing/results.json)
record ten scenarios compiled with ASan/UBSan against the actual `emount.c`,
`em_owner.c`, `em_frame.c`, `em_shutdown.c`, and packet table. These cover
ordinary/raw opcode `0x0a` with equal 25-byte replies; session or shutdown RX
during an in-flight TX; first-wins pending ownership; full 32-bit session
identity; failed TX and retry; shutdown without ordinary RX logging; two-entry
event queue admission/drop and tail return; and phase begin/end.

All ten proposed observation assertions pass; the exact frozen source fails
all ten missing-observation controls. A mutant that rereads the current session
at TX RETURN fails the RX-in-flight identity assertion, and one that omits the
raw bit fails the raw-versus-ordinary assertion. For every scenario, tracing
on/off and frozen/proposed sources produce matching synthetic wire bytes,
CS assertion observations, callback counts, queue overflow/session/readiness
state, final GPIO writes and clock effects. The harness uses an ABI-compatible
collector for detailed assertions; it is not a claim about the storage core.
A test-only session setter is excluded from the production ARM object.

The separate [retention results](../../firmware/upstream-hardening/followup/34-capture-tracing/retention-results.json)
link the actual lane35 core/writer and lane33 motion storage. A synthetic raw
opener, ordinary recovery opener, **100 normal RX/status cycles**, and shutdown
retain 22 focused events with zero evictions, filter 1,226 events, and preserve
all 205 successful-return counts. Raw/ordinary identity, interrupted phase end,
raw START/RETURN and shutdown admission/RETURN remain in CRC-valid serialized
pages. The conditional-filter removal control fails specifically because that
evidence is absent. Assertions permit no flash read/write during the active
bus interval; only the 16 pre-bus initialization page reads occur before it.
This checks software boundaries using a host flash array, not hardware timing.

ARM compilation uses the base manifest's exact compiler flags, including
`-Os` for `emount`. The object text grows **554 bytes** (4,321 to 4,875), with
no object data/BSS change (3/1,604 bytes respectively). `em_transmit`'s compiler
frame grows 304 to 312 bytes; the new `em_trace` helper has a 40-byte frame and
`em_trace_flags` a 12-byte frame. `em_poll` remains 56 and `em_pump_status` 40.
These are object/compiler-frame measurements, not final linked layout or a
whole-program stack bound. Base margin is only 268 bytes with a 256-byte release
floor: this lane cannot fit by itself and needs at least 542 bytes of offsetting
savings before accounting for the other lanes and link effects. Root must check
the final composed image and physical stack/IRQ/timing limits remain unmeasured.

Reproduce the ten cases and object measurements with
`python3 firmware/upstream-hardening/followup/34-capture-tracing/run.py --output artifacts/private/NEW-DIRECTORY`.
Reproduce current lane composition with
`python3 firmware/upstream-hardening/followup/34-capture-tracing/run_retention.py --output artifacts/private/NEW-DIRECTORY`.
Bind retention to a final private candidate with
`run_retention.py --source artifacts/private/CANDIDATE --output artifacts/private/NEW-DIRECTORY`;
that form checks the expected instrumented `emount.c` digest, verifies a manifest
when present, uses that candidate's actual core/motion source, and records all
source pins. Output directories must not exist. Public results contain only
synthetic metadata and digests.

No hardware enumeration/open, USB/HID, flash, motor, updater/application launch,
or canonical Application Support access occurred. Instruction searches stayed
within explicit ancestors and repository paths. This lane wrote only its
followup directory, this audit, and private disposable build/test outputs; it
made no commits or release overwrite.
