# Firmware correctness audit and offline hardening — October 11, 2026

The frozen AF 2.2 source has concrete command-integrity, interrupt-coordination,
Stop and completion defects. The independent audit reproduced them offline and
corrected current source for a **separate 2.3 hardening candidate**. This is a
software milestone, not camera qualification or a complete factory-firmware
reconstruction. The installed 2.2 image and its bundled digest pin remain frozen.

## Scope and evidence boundary

Reviewed E-mount framing/record handling, homing/servo ownership, command
replacement, fault/shutdown paths, integer ranges, initialization waits and
completion/status reporting. Read the [AF reconciliation](../af-reconciliation.md),
[factory AF dossier](../reverse-engineering/stock-phase2.md),
[host-model contract](../reverse-engineering/stock-host-model.md), and
[whole-firmware ledger](../reverse-engineering/whole-firmware-reconstruction.md).
The pinned REA evidence and native guides require finite claims with explicit
external-action and interrupt boundaries; that distinction is retained here.

No device enumeration, HID open, USB report, updater/app control, user-state
mutation, firmware-image generation or upload occurred in this audit lane.
Host executables and a pre-change source copy were created in a separate
temporary directory. Production edits were explicitly assigned by the parent
after the initial read-only findings. The parent owns versioning, image creation,
app integration, publication and any subsequent hardware plan.

The reviewed pre-change production files match the recorded 2.2
[source manifest](../evidence/af-reconcile-build-manifest-2026-10-10.json).
The bundled 2.2 template remains SHA-256
`e3614dfb8482644ba5b6114b591352669187e8ebd01a1344718f580ca12c3b36`.
The personalized installed image and owner camera observations remain in the
[installation](../evidence/af-22-upload-2026-10-11.md) and
[camera-lifecycle](../evidence/af-22-camera-lifecycle-2026-10-11.md) records.
Normal reported startup, quiet idle and motor shutdown do not exercise the
counterexamples below or establish homing/focus-command movement.

## Findings and corrections

### P1 — Malformed frames could publish motor commands

Pre-change `emount.c:on_cs_edge` checked a six-byte header and `F0`, then used
every non-init class as normal traffic. It did not check the additive checksum
or `55` terminator. A declared frame longer than its received window was clamped
to the window and could still publish a complete record from that prefix.
Examples with a valid-looking Move were accepted despite a corrupted checksum,
missing terminator, class 3, truncated declared length, or nonzero high length
that made the declaration larger than the supplied data.

Current admission requires a full six-byte header plus three-byte trailer,
class 1 or 2, complete declared 16-bit length, `55`, and the correct little-endian
sum of bytes 1 through `length-4`. Trailing **bus-window padding is permitted**
and is neither parsed as records nor included in the checksum. The received
window and declared frame remain separate sizes. Payload guards use the declared
frame size, preventing padding/trailer bytes from becoming metadata operands.
Partial frames publish neither commands nor reply effects.

This validation is deliberate replacement policy. The REA dossier says the
factory consumers themselves do not perform these validations; it does not
justify copying that omission into an experimental motion-capable responder.
The frame layout agrees with the pinned LexOptical implementation and the
factory transmit reconstruction. Strict admission still needs qualification
against complete A7C II traffic, including any unusual valid command forms.

Regressions: hardening scenarios 0–5. The valid 27-byte frame inside a padded
48-byte window passes before and after; all five malformed examples fail the
expected rejection check against frozen 2.2 and pass after correction.

### P1 — ISR command publication and foreground consumption were not atomic

The receive ISR writes a multi-byte `g_cmd`, while the foreground previously
cleared its pending flag and copied individual bytes with interrupts enabled.
An ISR between copies can combine two commands; an ISR between flag/read steps
can also lose or duplicate pending work. `volatile` provides neither snapshot
coherence nor exclusion. Query shifting had the same producer/consumer problem.

Consumption now saves PRIMASK, masks interrupts for the bounded snapshot/queue
shift, and restores the original mask. Deferred publication after restoration
remains pending for the next call. A caller already running masked remains
masked. These sections contain no peripheral wait or transmit.

The init reply ID/request snapshot is consumed coherently too. Normal frames no
longer overwrite request bytes belonging to an unread init reply. A `0x08`
request records its option in the ISR, but aperture packet edits occur in the
foreground reply path, avoiding ISR modification during a packet checksum/send.

Regressions: scenarios 6, 11–13. Deterministic deferred-interrupt hooks check
coherent first-command/query values, retained following Stop/query, restored
preexisting mask, and intact init request bytes after a normal frame. This is
synthetic interrupt scheduling, not measurement of ISR duration, UART overrun
margin or every possible hardware ordering. The old-source negative controls
fail those contracts; an actual torn command on the owner's adapter was not
observed or claimed.

### P1 — Stop could wait for a retarget cap or restart stale queued work

The servo only invokes its retarget hook while below `retarget_max` and outside
reversal braking. The old abort hook did not consume newly received commands.
After the cap, an explicit Stop could therefore sit unread until a leg completed
or timed out. Separately, outer dispatch ran a handed-forward command before
checking newer received work, allowing stale motion to start ahead of Stop.

The abort hook now consumes a command not handled by normal retargeting. Stop
ends the owner and discards handed-forward work; other commands end the owner
and wait for normal dispatch. Dispatch consumes newer received work first,
superseding the older handoff. Existing servo release/brake and bounded-loop
policies remain in force.

Regressions: scenario 10 uses an exhausted retarget budget and delivers Stop
during actual simulated motion; scenario 14 supplies a stale Move handoff and a
newer Stop and checks that no motion leg begins. No real stopping latency or
loaded-lens overrun is established by these checks.

### P2 — Outer fault guards discarded Stop despite the completion policy

The completion helper allows idle Stop acknowledgement after a motion fault,
but the old outer main-loop guards discarded all commands before `focus_exec`
could apply that policy. A valid Stop therefore had no event after a latched
stall, despite the documented behavior.

The production `focus_service` boundary passes commands to `focus_exec`, which
handles Stop first and independently rejects motion while unhomed, faulted or
shutting down. The fault is retained. Faults that inhibit homing before the
ordinary focus-service stage also reach this boundary. A failed UART/peripheral
still cannot be promised a physically delivered acknowledgement: event
eligibility and transport health are separate facts.

Regression: scenario 7 verifies an actual emitted Stop tail in the simulated bus
after a sticky motion fault, with no drive and no fault clearing.

### P2 — Sustained query publication could starve focus/Stop dispatch

The foreground query responder drained with `while (em_take_query(...))`.
Although the receive queue holds only four entries, an ISR can publish a new
query after every atomic pop. The loop could therefore remain live indefinitely
and prevent the following `focus_service` call from consuming a pending Stop.

Query answering now consumes at most `EM_QUERY_Q` (four) entries per invocation.
It preserves FIFO order and leaves later publications pending for the next
foreground pass. The queue capacity bounds work per call; it does not establish
elapsed time, interrupt latency or a physical stopping guarantee.

Regression: scenario 17 initializes a full queue, continuously rearms a
deferred interrupt to refill it after each pop and publishes Stop on the first
refill. The responder returns after exactly four pops with the producer still
armed. Stop then reaches actual `focus_service` without starting motion. Wire
answers for both the original and retained next-pass batches remain in FIFO
order. Undoing only this loop bound in a temporary copy attempts a fifth refill
and fails the test's guard; the producer does not merely run dry after four.

### P2 — A Move replacing Scan/Drive could complete as the old operation

All legs inherited the Move retarget callback. A Move received during Scan or
Drive could change the servo target in place while the caller continued to
report Scan/Drive completion. Scan could also continue its second leg after the
camera had already replaced the operation. Pure completion-helper tests cannot
detect that ownership mismatch.

Scan/Drive owners now unwind on a new command. The replacement is handed to
normal dispatch, and the old owner emits no success event. Ordinary Move-family
retargeting remains in place. The latest Move-family kind updates diagnostic
ownership; all such kinds still share the Move completion tag.

Regressions: scenarios 8–9 include actual `main.c` and the servo, inject Move
during Scan/Drive, require idle scan state/no old success tail, then require the
replacement's Move tail after it completes. These are software events, not
observed Sony Scan/Drive traffic or optical focus.

### P2 — Velocity history advanced per foreground poll instead of body frame

`focus_report_at` previously shifted seven velocity samples on every report,
including repeated polls inside a single camera frame. That contradicted its
stated per-frame first-difference policy and could replace the history many
times before one status transmission.

History now advances once for a newly observed body VD edge, using the previous
frame's saved position. Scenario 15 checks repeated reports within one edge
leave history unchanged and the next edge records the frame-to-frame delta.
The pinned protocol study establishes this encoding on Yongnuo; identical Sony
field semantics remain probable. Coalesced/missed VD edges and the physical
sample/transmit phase remain unqualified. This change follows the candidate's
declared policy, not a recovered factory-controller claim.

### P2 — Oversized shutdown requests could park without a valid echo

The old shutdown path invoked park before checking whether the complete request
fit its 16-byte echo snapshot. A checksum-valid longer init `0x16` could therefore
cause a park and then return without an acknowledgement.

It now checks the full snapshot bounds before park. Scenario 16 verifies an
unsupported 32-byte shutdown request produces neither park nor acknowledgement.
The inherited valid shutdown echo/park/repeated-request tests still pass.

### P2 — Core clock, EIC and USART reset waits had no finite bound

Runtime sensor, ADC, PWM and transmit waits already had fault bounds, but DFLL/
GCLK initialization, EIC clock/reset/enable synchronization and USART reset still
contained unconditional spins. With a held register condition these could
strand startup indefinitely.

AF builds now use the sticky I/O fault and GPIO-only emergency release. Core
clock and common GCLK waits use a **100,000-poll ceiling without reading elapsed
milliseconds**. Before SysTick initialization, no millisecond timing authority
exists; the poll ceiling is not a calibrated duration. A core-clock failure
returns and main enters an intentional inhibited idle path before timing,
protocol or homing. EIC/USART waits after normal time-base setup use the existing
deadline plus finite poll fallback. Failed setup stops before interrupt enable
or further dependent configuration where tested. Successful register values and
configuration ordering are retained.

The actual drivers are compiled against DFP-shaped register memory in 11
startup scenarios: DFLL readiness, GCLK synchronization, EIC clock/reset/enable,
USART reset/config synchronization, frozen ticks, preserved masked IRQ state,
the successful configuration sequence and UART clock-route failure. Held inputs
in eight selected old-source cases exceed a 0.3-second **host harness budget**;
this is evidence of an unbounded software loop under those inputs, not measured
hardware wait duration. Every corresponding new driver path returns with coils
detached and later drive/brake/attach attempts inhibited. The memory-backed
register harness supplies reset/sync transitions explicitly; it is not a model
of electrical peripheral behavior.

## Independent verification performed

- **83 ordinary offline invocations across 17 test executables passed**: framing,
  inherited servo/distance/prediction/mapping tests, 65,927 bounded target cases,
  I/O waits, reference/completion policy, 13 actual-main lifecycle scenarios,
  18 hardening scenarios, 11 existing driver-fault cases, two frozen-tick delay
  cases, 11 initialization cases, seven metadata profiles and seven hardened
  AF 2.3 profiles.
- **57 AddressSanitizer + UndefinedBehaviorSanitizer invocations passed**:
  18 hardening, 13 actual-main lifecycle, 11 initialization, one framing suite
  and the same 14 profile cases.
  Sanitizers used `-fsanitize=address,undefined -fno-sanitize-recover=all` with
  `-std=gnu99 -Wall -Wextra -O1`.
- Against the captured frozen 2.2 sources, **16 of the original 17 hardening
  scenarios fail their intended contract**, while the valid padded-frame case
  passes. The negative harness supplies the exact previous outer-dispatch
  sequence because that code had not yet been extracted into `focus_service`.
  The added query-fairness scenario separately fails when only its new loop
  bound is removed from the hardened source.
- Existing fake frame builders were corrected to write genuine checksums and
  to allocate two payload bytes before the three-byte trailer. Deliberately
  partial/corrupt fixtures remain partial/corrupt and use the raw bus helper.
  The new checksum rejection tests would be hidden by a shim that silently
  repaired every received frame; the shim does not do that.
- The cross-language profile fixture's inbound init requests were corrected to
  include a checksum too. Each of the 14 profile cases checks all 256 single-byte
  profile corruptions, emitted focal length/aperture/name, handshake replies,
  periodic status, checksums and preservation of the optical rows. The seven
  hardened fixtures were generated by the parent, verified against their image
  digests and required to carry version 2.3.0 and the hardened template digest
  `8996767bfc8e8625739e1c7619a54db1dd0b8da8150526b9afa4c9a490434e88`.
- `git diff --check` passed for the owned firmware changes. The common-section
  alignment warning from the host linker is unchanged and not a sanitizer
  diagnostic.

The root's integrated test runner owns fixture generation, distribution tests,
firmware link/map verification and the separate 2.3 digest manifest. This audit
lane read those prepared profiles and did not produce a flashable binary. The
parent separately reports that its full `scripts/test-firmware.py --af` passed;
the independently recorded counts above come from this lane's temporary host
executables.

### Reproduction inputs

The new `hosttest/test_af_hardening.c` uses the same source dependencies and
`EA9_SIM_MOTOR`, `EA9_NO_LOG`, section/dead-strip flags as `test_af_lifecycle`, plus
`EA9_HOST_IRQ_TEST`. Run numeric scenarios **0–17**. The conditional host CMSIS
hooks are confined to the synthetic test header.

The new `hosttest/mmio/test_startup.c` links `io_guard.c`, `motor.c`, `clock.c`,
`em_eic.c` and `em_uart.c` with `EA9_AF_BUILD`, the same SAMD21 DFP/CMSIS includes
and forced `hosttest/mmio/registers.h` as the existing driver tests. Run numeric
scenarios **0–10**. The register header redirects all touched clock, NVM, EIC,
UART and GPIO addresses and NVIC calls to host memory; no device MMIO is mapped.
Add the sanitizer flags above for the separately checked sanitizer variants.

The profile tests link `firmware/tests/test_profile.c`, the host shim,
`emount.c`, `emount_packets.c` and `lens_profile.c`. The metadata test uses the
default address/version; the AF test additionally defines
`EM_FW_VERSION_BCD=0x23u` and `EA9_PROFILE_ADDRESS=0x9f00u`. Pass each existing
prepared image path as the sole test argument. These host tests read only the
256-byte profile row; they execute the current source's decoder/transmitter,
not Thumb instructions from the supplied image.

## What remains unknown or deliberately different

REA recovered stock's asymmetric reference-relative wrap, signed/narrowing
arithmetic, incremental integer PID, retained history, fixed callback cadence,
NVM orchestration and many protocol/boot routines. This lane reviewed that
documented evidence; it did not independently reexecute all original Thumb
oracle cases or certify every reconstruction. Its finite host contracts exclude
complete peripheral behavior, arbitrary ISR interleavings and parts of reset/
DMA/USB scheduling. Static inventories and byte partitions are not semantic
coverage percentages or proof of a buildable original source tree.

The replacement retains upstream velocity/feedforward/boost tuning, shortest-
delta tracking and experimental post-handshake homing. The ordinary enabling
writer for stock's homing gate is unresolved; the replacement neither enables
that stock gate nor imports factory live state. The 192-count coordinate bridge
is explicit arithmetic, not a physical calibration. A stationary sensor value
can satisfy a settle window without proving a genuine connected sensor or end
stop. Direction, counts per millimeter, loaded friction, stopping distance,
control gaps and A7C II packet timing still need physical qualification.

No new overflow defect was found in the bounded command translation exercised:
relative/defocus products widen before clamping to 0–5952, and the no-target
sentinel is rejected. This does not prove arbitrary full-width tracker or
controller state safe. Long-term encoder plausibility and corrupted sensor
streams remain outside the synthetic mechanism's electrical model.

Event/query queues are finite and currently discard excess publications.
Acceptable camera burst size, overflow reporting and recovery semantics remain
unqualified. The deterministic interrupt hooks prove only the declared
interleavings; measured critical-section latency and actual UART error handling
under simultaneous camera edges remain outstanding.

Homing, Stop, park, AF-S lock and original-photo sharpness must be qualified with
the 50mm f/1.4 and converter before considering AF-C/video or other lens loads.
The original same-unit 1.8.0 backup remains the recovery authority; an AF-to-stock
hardware restoration round trip and the purpose of the retained upper prefix/
duplicate are still unqualified. No new firmware should be called factory-
equivalent or physically validated on the strength of these host tests.

## Reviewed pre-change source identity

| File under `firmware/ea9/src` | Frozen 2.2 SHA-256 |
| --- | --- |
| `emount.c` | `800653e5ea0d7880d02aa75893e02081289b7180ce8b62cc3dd9e79e3da6c4ef` |
| `main.c` | `fce56cdbc33199a8fcbba2e656472e4311672c930bb7ea0e4636b6774f8ad704` |
| `clock.c` | `650c3fde1d016593804d3990de015a12f0a879147b8d73e6c0bc7b03559e6346` |
| `em_eic.c` | `2f1c50c83f3b9277dcd7907453a6962cbd7b7f8fa28026845dbcb0ab729b8b48` |
| `em_uart.c` | `ebc5ad79da3d7f469b107247c37e7282b1e0ce64439372bcfaa3fca9ef4f0cb2` |
| `io_guard.c` | `038eddeca80fbe71d3dbe301c6cadb4cd7869196c52f4f5a437fe81be168a357` |
| `io_guard.h` | `f3a524087b6bfaf179a37a0338f61d8ba7376cc300dc573df536a105fd16d819` |
