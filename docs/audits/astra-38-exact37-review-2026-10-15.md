# Astra 38 — exact AF3.7 composition, stack, and IRQ review

October 15, 2026. The exact `artifacts/private/targeted37c` image has a
**1,516-byte conservative conditional software stack bound**, with an
8,192-byte linker reservation. The independently reviewed control-source
transformations, callback graph, flash-write gates, and emitted startup/IRQ
ordering pass. No production change was required by this review. This is not
camera qualification, a shutter remedy, factory parity, physical timing
equivalence, or a measured stack high-water result.

This review covers the final composition of lanes
[33](astra-33-motion-tracing-2026-10-15.md),
[34](astra-34-capture-tracing-2026-10-15.md),
[35](astra-35-targeted-trace-2026-10-15.md),
[36](astra-36-trace-footprint-2026-10-15.md), and
[37](astra-37-packet-initializer-2026-10-15.md). Root owns integration,
publication, and separately authorized installation. The original campaign
remains closed. This lane used only offline files and tools, with no device
enumeration/open, HID/USB report, updater/app launch, hardware motor operation,
canonical Application Support access, flash, or commit.

## Exact inputs and independently derived evidence

| `targeted37c` input | SHA-256 |
| --- | --- |
| Image | `6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5` |
| ELF | `f7ae647169d14b81495e14c6b061372ed1f135c4fc904e4b1ff2f338d79a873a` |
| Map | `4350407df694867e350ac2ae8f8742592a1d35185b8968202a75b90bc6964604` |
| Manifest | `15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b` |
| Raw load bytes | `94fea24bcd3d7a22c75a84c5d7995e9e4fddc81fa676dfe010b3ea3112e54ba8` |

The [runner](../../firmware/upstream-hardening/followup/38-exact37-review/run.py)
accepts `--build` and an explicit immutable
[policy](../../firmware/upstream-hardening/followup/38-exact37-review/policy.json).
It checks ELF load segments against raw bytes, raw bytes against the image,
manifest/image identity, all **49 source hashes**, all **149 static compiler
frame records**, **153 linked function bodies**, **515 compiled call or
inter-function branch sites**, and **12 register-indirect sites**. Every linked
body enters the graph, including unreachable bodies. Unknown calls, frames,
targets, recursive components, and dynamic compiler frames fail closed.

The graph parser is an explicit derivative of the frozen lane29 analyzer. The
runner verifies its exact source transformation: only default build path,
source count 46→49, and static RAM 3,064→3,044 change. Its parser, full inventory
checks, library requirements, cycle checks, image binding, and bound arithmetic
are retained. This does not reuse the old address policy: all emitted 3.7
callback sites, literal words, library bodies, critical bodies, masks, paths,
and source transformations were examined and recorded anew. The new
[semantic checks](../../firmware/upstream-hardening/followup/38-exact37-review/semantics.py)
test instruction ordering beyond the graph parser.

The load image ends at **`0x9ab8`**, leaving **328 bytes** before `0x9c00`,
72 bytes above the required 256-byte floor. The diagnostic range remains
`[0x9c00,0xa000)`, sixteen 64-byte pages. Static data ends at `0x20000be4`;
a separately checked four-byte alignment gap precedes stack
`[0x20000be8,0x20002be8)`. Stack reservation is not a runtime guard.

## Control-source composition and wire limits

The [composition verifier](../../firmware/upstream-hardening/followup/38-exact37-review/composition.py)
implements an explicit, inspected inverse of the observation additions. It
removes only the reviewed helper block, trace statements and trace locals,
then reverses the observed `admitted`, `ready`, and `focus_invalid` expression
rewrites. Every removal has an exact anchor or statement-count requirement.
The remaining C tokens equal the pinned 3.6 sources:

| Source | Original tokens | Result |
| --- | ---: | --- |
| `main.c` | 6,295 | Equal |
| `servo.c` | 1,972 | Equal |
| `emount.c` | 6,866 | Equal |

The runner rechecks all 46 frozen base source hashes as well. Thirteen source
paths differ from 3.6: ten modified files and three added trace files; none is
removed. The firmware-version header changes only BCD `0x36`→`0x37`.
**That identity response intentionally differs on the wire.** Other protocol
construction, checksum, framing, admission, cancellation, callback, motor,
gain, guard, timeout, and queue expressions survive the inverse unchanged.
Packet initializer equivalence and compiled restoration are separately
established in lane37; this audit includes its actual startup stack path.

Token equality after those explicit transformations is a source-level control
check, not whole-program equivalence. Added `millis()` reads, RAM operations,
mask duration, code placement, and terminal flash time can affect asynchronous
schedules. The earlier synthetic parity suites cover their supplied schedules;
neither those suites nor this static audit establishes physical byte timing,
camera receipt, or behavior under every interrupt ordering.

The constant `st_note` macro routes summary-only events directly to
`st_summary`, and retained kinds to `st_record` with the existing v3 field
packing. The discarded summary arguments in this composition are values or
existing buffer reads, not state-mutating calls. `em_trace` packs opcode,
flags, and owning sequence into the same identity word and the full session
into the payload. `em_trace_owner` only computes identity/current owner flags
and calls that RAM helper. This inspection agrees with lane36's packing tests.

No wrong-fault-coordinate or mutable TX-return identity blocker was found.
`st_motion_sample` receives the already-read `pos`/`now`; `st_motion_leg` updates
that sample's guard-interpreted state after rebase/retarget handling. The first
`st_motion_finish` runs before inhibition and the final encoder read; a frozen
first wrong-way/runaway record rejects later overwrite. The shared summary may
record a later terminal fault independently. Completion disposition records a
software attempt, suppression, queue result, or TX return; it is not successful
motion or shutter completion. An unfrozen record is a latest observation, not
a globally unique command ledger.

TX session/identity/flags are captured inside the existing admission mask and
reused at RETURN. A control response keeps the owning request sequence even
when its template has another wire sequence. `em_owner_cancel` does not change
the active slot or overwrite its request; IRQ offers target the inactive slot.
Foreground is the sole take/active-slot transition, so the live control request
remains stable through RX/session/shutdown interruption. The status event code
and parameter are saved while constructing the tail and reused after successful
return. Phase-end flags are explicitly a local observation, not an atomic
snapshot. These identity facts still depend on intact state and valid control
flow; repeated sequences, slot reuse, wrapping sessions, missing events, and
evictions preclude arbitrary joins across retained slices.

## Actual indirect calls and callback provenance

| Emitted site | Caller → reviewed target |
| --- | --- |
| `0x50c4`, `0x50ec` | Clone runtime → none; equal endpoints and zero weak literals |
| `0x56c6` | `em_shutdown_ack` → `powerdown_signal` |
| `0x5754` | `on_cs_edge` → `motion_shutdown_inhibit` |
| `0x69b8`, `0x69cc` | `EIC_Handler` → `on_cs_edge`, then `on_vd_edge` |
| `0x7266` | `servo_move_from` → `focus_retarget`, cfg+52 |
| `0x733c` | `servo_move_from` → `focus_abort`, cfg+56 |
| `0x74a8`, `0x7672` | `servo_move_from` → `pump`, cfg+48 |
| `0x96f8` | libc → none; empty preinit array |
| `0x9702` | libc → `frame_dummy` |

The source's abort checks share one emitted callback site in this build;
there are twelve sites, not the fourteen in 3.6. At `0x717a`, cfg from r2 is
retained in r4. Retarget receives `&nt` at sp+84; pump receives the existing
position or `out->end`. There is no opaque callback `ctx`/handle parameter to
invent: the original signatures use those arguments or globals. The linked
`STOCK` object at `0x9a40` has Thumb pointers at offsets 48/52/56 to pump
`0x7ef1`, retarget `0x7fc5`, and abort `0x7e09`. Local `sweep`/`drv` copies
change only scalar cruise/stop settings; the original callbacks remain.

Main's literal pointers at `0x8824/0x8828`, emitted registration calls, setter
storage addresses, and later loads bind powerdown/inhibit to their actual
targets. `em_init` installs CS/VD at `0x5fa2`; EIC callback loads use
`g_cs_edge`/`g_vd_edge`, not an assumed address from an older build. The two EIC
callbacks are sequential. No callback reenters the servo. The relative servo
wrapper and diagnostic PARK callback are not linked in this release.

Preinit is empty at `0x9a9c`. Init `[0x9a9c,0x9aa0)` holds `0x5129`, Thumb
`frame_dummy`. Clone endpoints are all `0x9ab0`; weak callback words are zero.
The policy binds these words to symbols and exact compiled bodies.

## Library and compiler frames

All seventeen linked runtime bodies lacking `.su` records have explicit
reviewed charges and full-body digests. No library defaults to zero.

| Runtime bodies | Local bytes each | Emitted evidence |
| --- | ---: | --- |
| Clone register/deregister, global destructors, frame_dummy | 8 | Two-word pushes and matching returns |
| Thumb signed/unsigned switch helpers | 4 | One-word push at `0x9388` / `0x939c`, restored before adjusted-LR return |
| Unsigned/signed division | 8 | Divide-zero pushes at `0x94b0` / `0x9686`; idiv0 path included |
| Division modulus wrappers, idiv0 | 0 | Branch wrappers or leaf; division target charged separately |
| memmove / memcpy | 8 | Two-word pushes at `0x969c` / `0x971a` |
| memset | 0 | Leaf byte loop, no stack writes |
| libc initialization | 16 | Four-word push at `0x96d0`; reviewed array targets |
| `_init` / `_fini` | 24 | Six-word pushes at `0x9a90` / `0x9aa0`, restored before return |

The switch helper call sites are `0x58e6`, `0x5938`, and `0x7f6e`. Their
bounded 7/7/4-entry byte tables branch to local points in `on_cs_edge` or
`focus_cmd_target` after restoring the helper's saved word. These are not
additional callback targets. Library digests bind the human instruction review;
a digest alone is not independent proof of a frame charge.

The longest compiled foreground chain, with each local frame, is:

```text
Reset_Handler 16 → main 88 → focus_exec 104 → focus_run.isra.0 104
→ servo_move_from 128 → pump 8 → em_poll 40 → em_pump_status 40
→ em_transmit 296 → delay_us 16 → st_fail 24 → st_flush 112
→ append 96 → st_write_page 28 = 1,100 bytes
```

The new initializer is 24 bytes: a five-word push plus one saved high-register
word. Reset+initializer is **40 bytes**. Reset+libc+`_init` is **56 bytes**;
neither path remains live alongside main descendants. Lane37's finite emitted
instruction fixture independently reports those same startup depths. The
reset frame itself remains live through main and is included above.

| Other checked structural path | Bytes including reset |
| --- | ---: |
| Servo→pump→query→either coordinate/distance conversion | 528 |
| Servo→pump→predictor→division | 480 |
| Inlined homing→pump→query→either conversion | 192 |
| Inlined homing→pump→predictor→division | 144 |

The runner checks every adjacent edge. Sequential calls use a maximum of
descendants; repeated pump passes do not accumulate frames. Tail branches
conservatively charge caller plus target frames. Structural paths need not all
be simultaneously feasible.

## NVM, interrupt ordering, and conditional envelope

`st_summary` has a 24-byte frame and `st_record` 32 bytes. Both save the prior
PRIMASK through `st_lock` and restore it with `st_unlock`. At `0x8d18` the lock
reads PRIMASK then masks; at `0x8d20` unlock writes the saved value. Nested
trace calls inside existing masks therefore do not unmask the outer critical
section. `st_fail` permanently masks configurable interrupts before cutoff.
The full emitted mask inventory contains only those reviewed operations.

The compiled caller gate for `st_flush` and `st_terminal` contains only
`powerdown_signal` and `st_fail`. `append` is called only by flush/terminal;
it alone calls `st_write_page`. `st_read_page` is called by `st_init` and
`append`. Descendant checks reject NVM/flush/fail reachability from EIC,
SERCOM1, SysTick, ordinary summary/record, or motion completion. Startup's
sixteen page reads precede ordinary bus initialization. `allowed=0` returns
before sealing or NVM access; append consumes the next slot before attempting
the write and never retries. Terminal append requires the initial seal.

The actual failure path masks at `0x8e56`, clears four motor PMUX enables,
writes DIRCLR at `0x8e80` and OUTSET at `0x8e86`, then first reads the clock at
`0x8e88` and logs at `0x8e94`. Flash begins only later. The shutdown path
disables UART at `0x7bea`, records shutdown, and flushes at `0x7c2e`; the VD
terminal record precedes PA23 store `0x7c5e`, its terminal record follows, and
the final footer follows the existing 100-ms delay. A write observation is not
measured pin voltage, and a returned delay is not a measured elapsed duration.
Shutdown admission already cancels ownership/readiness and invokes the
GPIO-only inhibit before its new admission trace and before returning past
ordinary RX logging. Nonterminal software inhibits remain RAM-only.

EIC setup writes IRQ4 disable at `0x68c0`, DSB/ISB at `0x68c2/0x68c6`, then
callback storage. Every explored handoff suffix calls either rescue
`on_cs_edge` or RX reset before `em_eic_start`; its IRQ4 enable store is
`0x6988`. EIC priority setup at `0x694a..0x695a` replaces the IRQ4 priority byte
with `0x40` (priority 1). All 45 vector words are checked: EIC, SERCOM1,
SysTick, reset, reserved zero slots, and default aliases, including NVMCTRL.

| Bound | Bytes |
| --- | ---: |
| Foreground including reset | 1,100 |
| EIC software chain | 168 |
| SERCOM1 software chain | 32 |
| SysTick / default-handler local frame | 0 |
| Foreground plus reset-like priority IRQ envelope | 1,372 |
| Foreground plus three active IRQ chains | 1,408 |
| Foreground plus all configurable levels, HardFault, NMI | **1,516** |

The EIC maximum is `16+72+24+24+32` through owner trace helpers. The largest
envelope is `1100+168+32+6×36`: four configurable ARMv6-M levels, HardFault and
NMI, eight core words plus one possible alignment word per exception. Default
vectors have zero local frames. Same/lower priority pending interrupts and
tail chaining do not recursively grow the stack. This bound deliberately does
not subtract overlap excluded by PRIMASK or EIC priority, and thus overcharges
the deepest masked failure path. Conditional arithmetic headroom is 6,676
bytes; it does not establish an interrupt-latency guarantee.

## Entry assumptions and physical unknowns

The original PA23-low boot path statically loads application MSP and selects
application VTOR before calling reset. The new packet call at `0x5186` follows
BSS clearing and precedes reset's VTOR rewrite at `0x5196`. **Boot may already
have selected app VTOR at that point.** The initializer does not establish IRQ
quiescence; it inherits it. Audit37's reset fixtures preserve PRIMASK and do
not schedule asynchronous exceptions.

Ordinary entry requires privileged thread mode, CONTROL=0 selecting MSP,
PRIMASK=0, no active exception, valid callback/configuration memory, and valid
ARMv6-M control flow. Boot preserves priorities and non-reset interrupt state.
Its NVMCTRL IRQ5 enable is paired with reset-zero peripheral INTEN under the
ordinary reset assumptions; unexpected delivered IRQ5 resolves to the default
loop. UART/SysTick priorities are not explicitly set by this application.
Inherited enabled/pending/active state, vector-transition arrivals, NMI and
HardFault during transition, and stacking failure remain unverified. The boot
MSP/VTOR transition remains unmasked and lacks handoff DSB/ISB; the later EIC
barriers do not change that fact.

No physical high-water, guard/canary, ISR duration, NVM latency, motor-rest,
encoder/optical response, factory equivalence, or camera behavior was measured.
The model excludes memory corruption, bootloader execution on its previous
stack, and failure of exception stacking itself. Missing or torn records
cannot prove no fault or successful capture/shutdown. The core's bounded work
and flash-page bounds do not imply calibrated wall-clock deadlines.

## Reproduction and rejection controls

```sh
python3 firmware/upstream-hardening/followup/38-exact37-review/run.py \
  --build artifacts/private/targeted37c \
  --policy firmware/upstream-hardening/followup/38-exact37-review/policy.json \
  --output artifacts/private/astra38-recheck.json \
  --guards-output artifacts/private/astra38-recheck-guards.json
```

The [result](../../firmware/upstream-hardening/followup/38-exact37-review/result.json)
and [guard output](../../firmware/upstream-hardening/followup/38-exact37-review/guards.json)
record **41 rejected controls and one accepted exact-bound control**. Rejections
include unknown indirect/library/frame/target evidence, recursion, incorrect
callback owner/target, input pins, library charges/bodies, raw words, source,
dynamic/changed compiler frames, ELF/raw/image mismatch, layout/inventory,
missing caveats, insufficient budget, EIC disable/barriers/enable/priority,
rescue/reset bypass, missing deferred start, NVM vector rebinding, STOCK
misbinding, omitted emergency/UART cutoff, omitted PA23/packet initialization,
missing NVM admission, broken PRIMASK restoration, mutable TX session, changed
motor-pump argument, changed wire terminator, changed terminal delay, and an
unconditional safety claim. Exactly 1,516 budget bytes passes.

Instruction/source semantic controls operate on in-memory copies to reach the
inner semantic checks; file controls use disposable private copies. Only the
ELF/raw and raw/image inner comparison controls refresh their copied outer
file pin. They do not rebuild firmware or modify frozen inputs. The runner
rechecks pristine inputs after controls and never updates policy pins. A new
container-path-only ELF/map reproduction requires root to separately establish
normalized disassembly, symbols, program-header and load-byte equality and
record derived container pins; it cannot silently replace this audit's policy.

| Review artifact | SHA-256 |
| --- | --- |
| `audit.py` | `ff226db7c6c1aee09ba8d7bcde05c948f56ff082754334fe9b111a5b44e7ab72` |
| `run.py` | `30ff760ab3761b821bf1465c6a00bb75e6bef0a362e5d3892259d3ef6617c7f8` |
| `semantics.py` | `2ab04e770a933c02ac64994133516f97c66300dc283377e6058264500f02d11c` |
| `composition.py` | `9e4c4b58f037677a9debb8f2964817f2f977c9dad47de0762af7f21cf9fe488b` |
| `policy.json` | `82630cd4205588457c1f0ec5ab3089561ac0d78b4de8bf392a68fa62ab165fd2` |
| `result.json` | `f4292d4001e23341a32d29668320cbba27411c4bfd659a6a647317cbf6784229` |
| `guards.json` | `4aa9b5255f5151cdc8824701ce7117f5a5f9a8af8ac83b7d7c870380564a03db` |
