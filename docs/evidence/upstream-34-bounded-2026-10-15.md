# Upstream C 3.4 — bounded coordinates, query flow and fault readiness

**Prepared offline; not uploaded or camera-qualified.** Root integrated
follow-ups 12, 15, 16 and 17 on frozen 3.3, with independent exact-image stack
review 18. The [campaign](../audits/astra-hardening-campaign-2026-10-15.md)
separately records the original eleven completed Astra lanes and follow-ups;
interrupted Astra 12/13 turns are not counted as completed Astra work.
[Machine-readable evidence](upstream-34-bounded-2026-10-15.json).

## Verified changes

The [query lifetime audit](../audits/astra-12-query-2026-10-15.md) reproduced old
answers crossing a session reset, and an unbudgeted worker under replenishment.
3.4 captures epoch/dequeue together, converts outside the lock, rechecks session
and readiness before publication, and limits each pass to four requests.

The [query flow audit](../audits/astra-16-query-flow-2026-10-15.md) reproduced loss
of four of eight admitted queries, or two after a partial tail drain: dequeue
continued when the answer queue was full. The capacity guard now retains those
requests. The existing foreground pump services the bounded worker during servo
and homing; operand conversions require no physical origin and never reenter
pump. Encoded 0x06 FIFO tests and moving-servo/unhomed-pump tests verify retention
and delivery, with ordinary wire output unchanged. Incoming request overload
beyond the finite queue capacity is a separate condition, not unlimited flow.

The [range audit](../audits/astra-15-coordinate-2026-10-15.md) supports checking
software coordinate capacity `[-65536,65536]` before tracker addition. Rejection
retains the previous value and latches existing motor inhibition. The actual
production defocus scale is 8; its high byte remains zero. Together with actual
configurations and bounded endpoints, the certificate closes reviewed main,
servo and predictor arithmetic without expensive 64-bit division or changed
normal control calculations. The earlier partial widening exceeded diagnostic
storage by 644 bytes; it was rejected and remains historical workbench evidence.
This capacity is not an endstop, measured physical range or infinity calibration.

The [composed review](../audits/astra-17-composition-2026-10-15.md) then reproduced
false HOME_READY after coordinate inhibition. The driver stayed inhibited, but
homing could reset the reference and mark ready from a fault-retained reading.
An early inhibited branch in `home_cancel_requested()` now marks HOME_FAILED,
clears pending motion and takes the existing cutoff path. It preserves the
original fault reason and prevents a fresh command from retrying that terminal
attempt. Five fault controls include an entire zero-to-capacity history generated
inside the complete homing function. No-fault homing remains unchanged.

Exactly five of 46 manifest files change from 3.3: encoder C/header, main,
protocol C, and version header. Servo, predictor, optical maps, packet templates,
UART/SPI/motor drivers and diagnostic writer are byte-identical. Capture/shutdown
ownership and the fixed-aperture policy remain as reviewed for 3.3. Shutdown
starts no new park drive. REA original-instruction evidence remains the contract
reference; no factory PID or guessed origin/gain/exposure offset is transplanted.

## Exact candidate and validation

The [3.4 image](../../firmware/candidates/3.4.0/README.md) is 20,480 bytes, SHA-256
`fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9`.
The [manifest](../../firmware/candidates/3.4.0/contax-zeiss-50-f1-4.manifest.json)
pins all sources and build inputs; its SHA-256 is
`8e358720a959a79a4636e1a9310fc23c08af9fa50539396d6946be6194c25a9a`.
Two fresh builds reproduce image, manifest and complete source patch exactly.
Code plus initialized data ends `0x9aec`: 276 bytes before the unchanged 1 KiB
log region, exceeding the required 256-byte margin. Static RAM is 3,076 bytes;
reserved stack remains 8,192 bytes.

The single [offline acceptance runner](../../scripts/test-upstream-bounded.py)
passes on a fresh repeat build:

- Retained 7 commit-race, 65 capture/session/transport and 14 diagnostic cases.
- 147,456 tracker boundary checks, 393,216 unchanged target calculations, 2,646
  predictor cases, fault-history/normal-servo checks; two frozen controls fail.
- 22 query ownership cases with 18 frozen failing controls; 17 query flow cases
  with 18 deliberate before-fix/mutant failures and identical ordinary wire bytes.
- Six final homing cases with five guard-removed failures, plus nine composed
  pump/epoch/capture/shutdown/servo-coordinate cases under ASan/UBSan.
- Nine compiled ARM flash-writer scenarios; actual 3.2/3.3/3.4 prefix acceptance
  and corruption rejection; 25 further version/pin/native-manifest/v2-page checks.
- [Exact compiled stack review](../audits/astra-18-stack34-2026-10-15.md): 138
  functions, 461 call/branch sites, 14 resolved indirect sites, no recursion or
  unbounded frames. Conditional all-vector envelope 1,560 bytes; seven evidence
  guards reject and an exact-budget positive passes.

The stack report pins the originally reviewed ELF/map. Fresh build directories
change non-loadable DWARF/link-map path strings. The acceptance runner permits
only those two container pins to be rebound in a private derived policy, after
requiring the exact published image, raw bytes, manifest and source hashes, plus
normalized disassembly, symbol-table and program-header hashes from the reviewed
ELF. Only the input filename in the objdump file-format header is normalized. All
reviewed addresses, indirect targets, library frames and entry caveats remain;
the analyzer ties ELF load segments to the pinned raw image and rejects changed
edges/cycles. This is separate from changing any executable or released pin.
Physical entry/IRQ state, high-water and execution timing remain unmeasured.

All 53 Swift tests pass, including strict pristine-tail verification, fixed-profile
rejection and the new 3.4 workflow. Registering 3.4 required moving the existing
unsupported-version control to 3.5; the initial old expectation failed and was
corrected without weakening rejection of unknown versions. Signed app
0.17/build 21 and CLI package successfully. Isolated native prepare commands
produce the exact 3.4/3.3/3.2/3.1/3.0 candidates; incompatible 85mm preparation
fails without an output. No app was launched. Old command meanings and all
[52 prior release/recovery/pin artifacts](upstream-34-preserved-2026-10-15.json)
remain exact; the old diagnostic registry entry is unchanged.

## Remaining limits and hardware gate

Finite source/IRQ/peripheral simulations do not establish A7C II stability,
exposure correctness, optical accuracy, mechanical safety or factory parity.
Consecutive target and servo reads can still shift the internal relative servo
target outside advertised optical travel. Extraordinary timer gaps retain an
implementation-defined signed conversion. These are explicitly distinct from
closed arithmetic-overflow cases. Donor optical mapping and stationary homing
need physical calibration. The manual iris position stays Unknown, while the
camera receives nominal f/1.4. REA reconstruction remains partial.

No adapter enumeration/open/report/updater/flash/motor action or canonical
Application Support write occurred. Uploaded 3.2 still awaits owner-confirmed
physical reconnect and strict verification. The pending journal and safety guard
remain untouched. This offline batch does not authorize installation or camera
use. Coordinate a separate operation using the [3.4 procedure](../upstream-bounded-test.md)
after resolving the existing transaction; collect logs after one cycle before
any retry. Original stock recovery and all earlier releases stay available.
