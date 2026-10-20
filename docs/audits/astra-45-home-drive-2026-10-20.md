# Astra45 — drive-phase homing discriminator

The exact AF3.8 caller workload reproduces several **different causes of fault
17 under supplied inputs**, but does not establish a causal defect that safely
justifies changing homing policy. The lane therefore adds a bounded, failed-home
snapshot for AF3.9. It does not increase drive time/duty, force readiness, restore
an unverified saved origin, retry a failed home or claim to fix shutter blocking.

The [new camera evidence](../evidence/upstream-38-camera-failure-2026-10-20.md)
reports hunting, apparent focus for one photo, a motor reset and no further
photos, with normal shutdown and AUTO exposure. Actual focus mode and whether
the file was saved are unknown. Fault 17 identifies drive-phase qualification
failure, but the old all-zero servo collector contains no homing trajectory or
fault time. Raw-readiness completion one tick before shutdown cannot be mapped
to the first shutter attempt.

The [REA origin policy](../reverse-engineering/stock-phase2.md) identifies a
persisted stock reference and an optional 300/500-unit homing block whose
ordinary enabling writer remains unresolved. Pinned upstream `motor_home()`
implements an explicit replacement policy. Neither source warrants forcing the
stock gate, assuming a persisted reference is valid, or changing polarity,
noise bounds or the 300-unit drive deadline. Lane47 independently investigates
peripheral/clock and factory-origin contracts; lane46 owns subsequent blocked
motion-request observations. Root owns release-only ADC telemetry removal and
final composition.

## Source-bound workload findings

The [runner](../../firmware/upstream-hardening/followup/45-home-drive/run.py)
checks all 49 frozen AF3.8 source pins, manifest/image identity and host shim
before and after. It extracts exact home, stillness, cancellation, service,
query, pump and foreground bodies, and links real protocol/frame/owner/shutdown,
optical-conversion and trace modules. The production encoder tracker executes
against scripted raw hardware readings. The actual `em_uart_send()` polling
body executes with synthetic ready-register reads; SPI/ADC and motor boundaries
remain simulated. Thus this extends lane42's stubbed track/UART boundaries,
without claiming electrical timing or execution of every peripheral initializer.

Time advances through an explicit **test-only post-pump scheduler hook**. That
hook also schedules RX/VD traffic. The ADC mock only counts calls, so baseline
and candidate receive the same external schedule even when the final release
omits ADC telemetry. The private UART register hook can separately advance the
clock while DRE or TXC is not ready. This models a returning peripheral wait;
it is not a measured duration on the owner's adapter.

Seventeen workload scenarios execute against both frozen AF3.8 and the snapshot
proposal. They include stationary feedback, clock wrap, travel ending at ticks
200/259/260, six/seven-count threshold patterns, sustained four-query batches,
ordinary UART readiness, continuing drive/settle motion, returning pumps that
cross each deadline, delayed actual UART DRE/TXC loops, frozen clock and a shared
drive/settle iteration budget. The baseline honors its current conservative
reference policy in every scenario. Representative results:

| Supplied input | Result under existing policy | New snapshot distinction |
| --- | --- | --- |
| Stationary feedback | Ready after 40 drive + 40 settle ticks | No failure record |
| Travel ends at tick 200 | Ready at tick 280 | No failure record |
| Travel ends at tick 259 | Ready at tick 339 | No failure record |
| Travel ends at tick 260 | Drive fails at tick 300 | Last threshold movement at tick 260; last iteration starts 299 |
| Continuing drive movement | Drive fails at tick 300 | Last threshold position changes through tick 300 |
| Alternating seven-count samples after grace interval | Drive fails at tick 300 | Small threshold displacement with recent threshold time |
| UART DRE wait crosses drive deadline | Drive fails after tick 301 | Initial/threshold positions unchanged; last iteration starts tick 0 |
| UART TXC wait crosses settle deadline | Settle fails after tick 541 total | Drive-qualified flag; settle starts tick 40 and last iteration starts 40 |
| Frozen clock / drive then frozen settle | Budget fault, 999,999 completed pumps | Shared poll counter 1,000,000; drive-qualified flag distinguishes phase |

These are discriminating **synthetic explanations**, not identification of the
physical cause. A mechanism that arrives too late to demonstrate 40 units of
stillness before the cap correctly remains unreferenced. A delayed returning
pump also cannot retroactively prove stillness. No failing baseline safety
contract justifies a behavioral homing fix here.

Every failed-home case retains the AF3.8 operand-query repair: subsequent queries
receive answers while the motor stays inhibited, readiness remains false, no
origin is reset and no normal focus runs. Session changes discard in-flight
answers; shutdown produces its local acknowledgement. The servo collector's
first 112 bytes remain uninitialized in this failure-only path.

## Failure snapshot and exact transformation

The pinned [applicator](../../firmware/upstream-hardening/followup/45-home-drive/apply.py)
changes only `main.c`. It captures each existing loop-condition `millis()` result
in a local and retains it when the loop body is entered. It adds **no hot-path
clock read, encoder read or ADC conversion**. At the existing failed label, after
`motor_inhibit()` has already executed emergency GPIO release and deferred work
has been cleared, it writes the following 32 bytes at motion-collector offset
112. The existing cutoff fallthrough remains in place.

| Tail offset | Encoding | Meaning |
| --- | --- | --- |
| 0 | u8 `0x39` | AF3.9 failed-home snapshot tag |
| 1 | u8 | Existing failure reason 17, 18 or 19 |
| 2 | u8 flags | Bit 0: drive qualification succeeded; all other bits zero |
| 3 | u8 | Initially zero; reserved for lane46's saturated count of later inhibited motion requests |
| 4 | u32 | Current phase start tick |
| 8 | u32 | Tick sampled after inhibition/cutoff |
| 12 | i32 | Existing pre-drive `before` position |
| 16 | i32 | Existing `still.at`, the latest threshold-reference position |
| 20 | u32 | Existing `still.t`, threshold-reference timestamp |
| 24 | u32 | Existing shared drive/settle poll counter |
| 28 | u32 | Start tick of the latest entered loop iteration |

Fields are little-endian on SAMD21. The header word is stored after the payload;
byte 3 is zero at initial publication. The writer uses GNU `may_alias` word
access, supported by the pinned GCC/Clang toolchains, because the backing member
is declared as a byte array. This avoids an effective-type violation without
changing the production structure or API. The added field lifetime and stores
have CPU cost; identical sensor/tick call counts do not prove identical physical
latency.

The last-iteration field starts at phase start if no loop body is entered. Its
interval includes communication, ADC when enabled, cancellation checks and
stillness evaluation; it is **not UART time, maximum pump duration or a sample
ring**. `still.at/t` are initialized by the phase's existing first sample and
then change only when the accumulated six-count threshold is crossed. They are
not necessarily the final raw reading. A zero total poll count identifies no
entered drive iteration; for budget exhaustion the final entered iteration may
fail before calling the pump. The snapshot records these existing quantities
without changing their interpretation.

Failure-only storage is deliberate: failed homes never enter normal servo
execution. The existing servo initializer may clear the reserved tail when a
later servo begins; no such call is admitted after this sticky failure. Early
cancellation and encoder-overflow exits do not fabricate a phase-17 snapshot.
Historical AF3.8 motion decoding must continue requiring zero reserved bytes;
root's AF3.9 decoder owns the version-specific extension.

## Verification and footprint

The isolated suite has 42 executions: 17 unchanged-baseline cases, 17 snapshot
cases and eight negative controls. Baseline and snapshot runs must have identical
home outcomes, synthetic durations, pump counts, raw encoder-read counts and
protocol outputs. The observation includes one additional clock read only after
motor inhibition. Assertions check all snapshot header fields and representative
positions/times/counters, including the late-arrival versus long-UART distinction.

Seven controls fail at their designated assertion: absent snapshot on frozen
AF3.8, a false last-iteration timestamp, removed drive or settle deadline
rechecks, removed inhibition, a reset shared poll counter, and a raised
stillness threshold. An eighth adds an encoder read in the snapshot writer;
its C assertions may pass, but the runner's exact read-count comparison rejects
it. No unrelated crash counts as a successful control. Host execution uses
ASan and UBSan. [Isolated results](../../firmware/upstream-hardening/followup/45-home-drive/isolated-results.json).

The [full ARM measurement](../../firmware/upstream-hardening/followup/45-home-drive/measurement.json)
rebuilds every production unit. Frozen AF3.8 reproduces image SHA-256
`8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`.
The isolated snapshot adds **84 bytes**, moving code plus initialized-data end
from 39,600 to 39,684, leaving **252 bytes**, below the required 256-byte margin.
Static RAM remains 3,044 bytes. **The isolated overlay is not an installable
candidate.** Final composition must independently recover space, reproduce its
own image and pass the unchanged size floor. Root applies lanes45,46,48 in order;
no size guard is relaxed.

`--candidate PRIVATE_BUILD` additionally verifies an AF3.9 manifest, image, all
source pins and shim before/after. It clones that exact final source without
reapplying overlays. Its ADC-independent schedule requires the same home/pump/
encoder/protocol outcomes as frozen AF3.8 and checks zero ADC samples in the
release candidate. The observation matrices and controls still execute against
that final source. Final composition receipts are owned by root.

```sh
python3 firmware/upstream-hardening/followup/45-home-drive/run.py --output artifacts/private/astra45-new-isolated
python3 firmware/upstream-hardening/followup/45-home-drive/measure.py --output artifacts/private/astra45-new-measurement
python3 firmware/upstream-hardening/followup/45-home-drive/run.py --candidate artifacts/private/FINAL39 --output artifacts/private/astra45-new-final
```

All work is offline. This lane accesses no device, app, USB/HID transport,
canonical state or live motor and performs no Git mutation. Historical sources,
releases, pins, recovery material and prior test receipts remain unchanged.
The next record can distinguish more software conditions, but physical homing,
optical focus, sustained capture and the reported shutter block remain
unqualified until separate evidence supports a causal fix.

## Final AF 3.9 integration

The exact composed image `87b84a83…03fa44` passes the same42 executions with
all49 source pins verified before/after. Release ADC samples are zero while
supplied home/pump/encoder/wire outcomes match frozen3.8. Root's accepted
45→46→48 composition leaves632 bytes of margin and3040 bytes static RAM;
the isolated252-byte margin is not the released footprint. The
[integrated receipt](../evidence/upstream-39-homing-2026-10-20.json) and
[compiled review](astra-af39-compiled-acceptance-2026-10-20.md) bind final identity
and limits. No physical homing or shutter remedy is established.
