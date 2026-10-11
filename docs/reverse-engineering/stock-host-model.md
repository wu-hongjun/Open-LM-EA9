# Executable stock semantics: bounded host reconstruction

A buildable C11 reconstruction now covers the factory autofocus arithmetic,
controller callback, focus-command state machine, reply dispatch, frame formatting
metadata/menu updates, handshake scheduling decisions, settings orchestration and
bounded main-loop scenarios. This is a useful executable
part of a firmware reconstruction, **not a reconstruction of the entire image**.
It uses the official 1.8.0 binary as its behavioral reference, not the experimental
upstream C controller. All execution is offline on the host.

The original application SHA-256 is
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
The phase-2 REA function dossiers, original instructions and the
[factory AF dossier](stock-phase2.md) establish address and field provenance.
The REA evidence guide's finite-claim principle applies: matching declared cases
does not establish whole-firmware equivalence.

## Implemented contract

| Stock entry | Host semantics |
|---|---|
| `0x8cc0` | Store raw sample; signed 16-bit subtraction, asymmetric wrap using 16383, arithmetic shift, protocol position |
| `0x8dd4` | Target-to-count conversion, narrowing, direction, timeout reset, enable flags; retained PID history |
| `0x8d20` | Direction-dependent signed speed thresholds and truncating division |
| `0x8bfc` | Incremental PID, history shifts, 32-bit wrapping products/sums, signed division, floor and clamp |
| `0x8d94` | Completion latch and target crossing |
| `0x8e28` | Stop software state; an event stands for register effects |
| `0x8fc8` | Velocity history, speed/PID composition, two ordered driver events |
| `0x8a2c` | Timeout counter, callback divider, velocity bookkeeping and controller invocation |
| `0x5308` | Flags and length-selected target extraction from existing RX storage |
| `0x5a94` | Scan-state progression, clamped first target, unbounded retained second target |
| `0x5b98` | Stop-command state progression and response fields |
| `0x5c08` | Absolute-target state progression and response fields |
| `0x5cc8` | Stop-before-dispatch and pending-command handling |
| `0x5a2c` | Response-event byte and length updates |
| `0x51d4` | Low length byte, terminator, checksum and send events |
| `0x66b8` | Aperture conversion with zero-extended 16-bit return |
| `0x567c` | Focal-dependent step ladder |
| `0x56cc`, `0x5510` | Menu focal/options selection and dirty flag |
| `0x8a8c` | Boot metadata writes including shared immediate/address dependencies |
| `0x5d2c` | Gated focal updates to reply 28 and status 05 |
| `0x58a4` | All reply-dispatch IDs, mode/class gates and associated RAM changes |
| `0x5120`, `0x5188`, `0x51ac` | Frame synchronization, transmit callback and protocol reset |
| `0x5238`, `0x5260`, `0x5274`, `0x5280` | Status sends, length reset and scheduled phase decisions |
| `0x52e8`, `0x53a4` | Received flags and rising/falling pin-edge phase handling |
| `0x54b8`, `0x54d8` | Event fields and conditional status 06 send |
| `0x5dd4` | Dispatcher, focus handling and focal-update ordering |
| `0x5d68`, `0x5da8` | NVM call sequence and dirty reference persistence |
| `0x8ae4` | Restore a caller-supplied 44-byte record, focal and lower-bound updates |
| `0x5e00` | Main-state gates, homing/park sequencing, sample bookkeeping, save and bounded shutdown |

The model retains a byte-addressed 2 KiB SRAM image. It writes exactly the known
fields, preserving unrelated bytes. A separate 44-byte settings schema has
compile-time size/offset assertions. Explicit unsigned wrapping and signed
conversion helpers avoid relying on host signed overflow or implementation-defined
narrowing. No original per-unit settings are embedded. Zero initialization is a
synthetic harness convenience, not a claim about stock startup.

The implementation and test harness are local analysis artifacts under
`tools/rea-analysis/reconstruction/` (intentionally ignored by repository policy):
`stock_model.c`, `stock_model.h`, `validate.py`, `validate_protocol.py`, `validate_application.py`, and `README.md`. The model exposes
an event sink for stop and final motor-driver calls; it contains no MMIO or
hardware access. Build products, source hashes and detailed results stay under
`references/private/rea-analysis/phase3/host-model/`.

## Differential evidence

**24,991 cases/steps passed** against original Thumb instructions across 38
modeled entries. The core suite contributes 8,882:

- 600 seeded synthetic-state cases for each of 14 routine entries: 8,400 total.
- 174 explicit speed thresholds, sensor seams and PID overflow cases.
- A composed target request followed by 302 timer callbacks: 303 steps.
- A five-step scan progression with caller-injected completion.

The protocol/metadata suite adds 5,900:

- 600 seeded cases for each of six metadata/menu routines: 3,600 total.
- Every reply ID under four mode/class gates: 1,024 cases.
- Every menu high byte with four low-byte choices: 1,024 cases.
- Every frame length from 4 through 255: 252 cases.

The application suite adds 10,209:

- 600 cases for each of 14 handshake/pump/persistence entries: 8,400 total.
- 600 independent synthetic settings restores.
- 1,200 main-state combinations, including enabled homing gates, park flags,
  shutdown stages, sample bookkeeping and dirty saves.
- A nine-step connected handshake fixture with caller-supplied callback execution.

Every comparison checks all 2,048 modeled RAM bytes. Pure result routines also
compare return values; motor-related routines compare ordered driver events.
Random states intentionally include stale fields, invalid command states,
reversed limits and values outside normal sensor ranges. These characterize
instruction behavior; they do not assert that such states occur physically.
The scan fixture demonstrates that a clamped first target does not clamp the
retained second target.

A negative control changes the wrap constant from 16383 to 16384. The same
original-instruction comparison detects the resulting mismatch. A second negative
control changes only the immediate at `0x8aa6` from `0x18` to `0x10` in an
emulator memory copy. The ordinary model disagrees; a dependency-preserving model
reproduces the collateral address changes exactly. No input image is written.
This confirms that the immediate serves both descriptor values and later store
addresses; replacing only its apparent metadata meaning is incorrect.

The aperture oracle also exposed a decompiler ambiguity: `0x66b8` returns its
16-bit result zero-extended in the register, even where pseudocode labels it a
signed short. The executable model follows the original instructions. Compilation
uses C11 with `-Wall -Wextra -Werror -pedantic`. A separate UndefinedBehaviorSanitizer
smoke run completed 380,000 routine calls without diagnostics; that run checks
host language behavior, not firmware equivalence. Validation is reproducible via:

```sh
tools/rea-analysis/venv/bin/python tools/rea-analysis/reconstruction/validate_application.py
```

The oracle executes the original stop register instructions against two dummy
RAM-backed register pages. These have no hardware behavior. The four final
motor-driver functions are stubbed and their arguments recorded; the original
arithmetic, command routines, stop software writes and timer logic execute.
Unicorn's selected Cortex-M0 model accepted an unsupported Thumb-2 MOVW in the
earlier negative control, so this is not proof of ARMv6-M instruction legality.
The tests are finite evidence rather than formal equivalence or measured timing.

## Remaining reconstruction work

This model does not implement reset/startup, the complete initialized data image,
bootloader, the actual flash driver, full interrupt/peripheral register behavior,
physical sensing, lens mechanics or transport DMA. Timer scheduling decisions
are emitted as events; a real-time scheduler and arbitrary ISR interleavings are
not reconstructed. Settings restore copies caller-supplied synthetic records;
persistence emits the actual unlock/write/lock call sequence with its constant
arguments, without programming flash or asserting success. NVM oracle stubs
return `-7`, confirming that these application callers ignore failure statuses.

The main-state model covers the gated homing and park branches, but does not
establish that the homing gate can normally become enabled or that a requested
position is physically safe. Each call uses a fixed caller-supplied sensor value.
Shutdown tests supply PA3 low at both reads, then explicitly simulate wake by
skipping the original WFI after recording an event. Held-high input polling,
changes during delays, actual sleep and wake interrupts remain unknown. This is
a declared finite input scenario, not a new timeout or a claim that stock's
polling loops always terminate. Critical-section helpers are stubbed; tests do
not establish atomicity under interrupt races.

The frame API accepts lengths 4–255 and buffers wholly within modeled RAM;
metadata pointer inputs must also refer to modeled RAM. These are host-interface
bounds, not validations performed by stock firmware. Out-of-domain pointers,
lengths and peripheral send effects remain outside the contract. The menu
argument is a RAM offset, whereas the original routine takes a full pointer.
Transmit events record length; the caller retains the frame offset and bytes.

PID tests use the factory denominator 200 and normal positive floor/clamp
parameters. The C model explicitly reports unsupported division by zero;
it does not claim to reproduce the original divide helper's zero-denominator
behavior. The optional event sink must not mutate RAM during a call. Actual
ISR interleavings and peripheral timing are outside the current contract.

A next useful expansion is an explicit scheduler plus transport/flash interfaces,
then differential tests of reset-to-handshake across interrupt interleavings.
That requires clearly modeled external inputs rather than treating successful
isolated arithmetic tests as proof of a complete device implementation.
