# Official 1.8.0: offline AF and persistence dossier

> Continued in the [whole-firmware reconstruction ledger](whole-firmware-reconstruction.md): corrected function coverage, compiled host models, NVM save behavior, bootloader/USB analysis and complete flash layout. This phase-2 report is retained as a historical checkpoint.

This bounded milestone reconstructs the factory controller and its protocol/state dependencies. It is not a replacement firmware or a hardware validation. No adapter was enumerated, opened, read, driven, or flashed; no updater was launched. Original images were read only. All decompiled code, packet bytes, per-unit values and tool logs remain private.

The most consequential findings are:

- Stock uses **reference-relative, asymmetric wrap arithmetic**, not conventional shortest-distance unwrapping.
- A protocol target becomes signed 16-bit `(target − 4096) × 4`; the upstream map instead anchors its clamped travel at 4144.
- The stock incremental PID retains history and accumulator across stops and retargets. It has a 200 nonzero output floor and ±1280 clamp.
- The timer callback divides by **11**. The recovered TCC1 configuration implies approximately **13.7518 ms** between PID updates at a 48 MHz generator. This is a configuration-derived result, not a measured period; upstream's “11 ms” comment is not established by these bytes.
- The 44-byte persistent record mixes reference, focal length, options and live motion state. Startup restores it **after** sensor initialization and motor stop.
- No enabling write to the homing gate `0x20000530` was found. The block is unreachable under the recovered ordinary initialization/control paths. Remaining unresolved pointer writes prevent an unconditional whole-program proof.

## Evidence and reproducibility

| Input/tool | Identity |
|---|---|
| Official app, base `0x5000`, length 20,172 | SHA-256 `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564` |
| Full-unit flash, used only for private persistence context | SHA-256 `1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01` |
| REA snapshot | `5100a1a1a56b810c8246b8c7ed19ff42c4d9dbe1` |
| Upstream C comparison | `d52ed06cc449918f938e0695fbf29a0c4141f2b2` |
| Phase-2 synthetic analysis ELF | SHA-256 `c4ddce75deb7ce1d850de689dcce34682fd2ba8ebf924f1b977ae1d6739935be` |
| Analysis | REA 6.3.0 / Ghidra 12.1.4, Unicorn 2.1.4, Capstone 5.0.6 |

The synthetic ELF preserves the app's flash bytes and adds an explicitly derived SRAM initializer mirror. It is not flashable. The final import has 233 function dossiers, including timer operation-table targets missing from the 213-function first pass. One intermediate import that seeded interior labels was rejected and retained separately for audit. All REA sessions were explicitly closed.

REA selected `ARM:LE:32:v8`; decompilation alone does not establish Cortex-M0 instruction legality. Original bytes and Thumb-v6M disassembly were used to check important operations. Unicorn was configured for M-class Cortex-M0, but a deliberately unsupported MOVW negative control was accepted. Consequently, its results are **behavioral comparisons, not strict ARMv6-M admission tests**. No peripherals were mapped. Hardware-facing calls were stubbed only where identified below.

Local reproduction from the repository root:

```sh
python3 tools/rea-analysis/phase2_make_elf.py
node tools/rea-analysis/phase2_session.mjs
tools/rea-analysis/venv/bin/python tools/rea-analysis/phase2_accesses.py
tools/rea-analysis/venv/bin/python tools/rea-analysis/phase2_emulate.py
tools/rea-analysis/venv/bin/python tools/rea-analysis/phase2_behavior.py
```

Tool bootstrap is documented in the local `tools/rea-analysis/README.md`. Tools and binary-derived output are intentionally ignored; this public dossier contains descriptions and synthetic examples, not proprietary code or unit calibration values. Private evidence resides in `references/private/rea-analysis/phase2/`.

## Factory AF arithmetic

Confidence here is high for the stated byte behavior: disassembly, recovered data flow, and independent Python models agree. Names are analyst labels, not recovered source symbols.

| Address | Reconstructed behavior |
|---|---|
| `0x89a4` | Sensor transaction returns the top 14 bits of two received bytes, big-endian. Electrical validity/error signaling remains unverified. |
| `0x8cc0` | Store raw sample; compute `d = s16(raw − reference)`. If reference <8192 and d>10000, replace d with `16383−d`; otherwise, if reference ≥8192 and d<0, add 16383. Store signed 32-bit d and 16-bit `(d >> 2)+4096`. The shift is arithmetic. |
| `0x8dd4` | Arm timeout and PID, clear completion and two counters, set `target = s16((s16(protocol_target)−4096)*4)`. Latch direction 1/2/3 for current relative position below/above/equal target. Does not clamp or reset PID state. |
| `0x8d20` | Direction 1: error >600 →250, >300 →100, >100 →50, otherwise signed truncation toward zero of error/2. Direction 2 uses symmetric negative thresholds; all other directions return zero. Direction is latched, not recomputed from error each update. |
| `0x8fc8` | Measured velocity is `s16(relative − previous_relative)` per PID invocation; previous position is updated even while PID is disabled. If enabled, position error is narrowed to s16, fed to `0x8d20`, then measured velocity is subtracted and passed as signed 32-bit PID error. |
| `0x8bfc` | Update incremental accumulator with `500*(e−old) + 150*e + 300*(e−2*old+old2)`, retaining low 32 bits. Update histories. Signed-divide accumulator by 200, truncating toward zero. Nonzero quotients with magnitude <200 become ±200; clamp to ±1280. Accumulator itself remains unclamped. |
| `0x8d94` | Return existing nonzero completion; otherwise direction 1 completes at relative ≥target, direction 2 at relative ≤target, other directions immediately complete. No velocity, dwell, tolerance or stall test. |
| `0x8e28` | Disable PMUXEN on PA08/09/18/19, set PA19 output high; clear PID/timeout enables and boundary flag; set completion. Does not reset PID accumulator/history or establish physical stop. |

The PID block starts at RAM `0x200004c0`; coefficients occupy words 0–2, current error word 3, histories words 4–5, limit/floor/divisor words 10–12 and accumulator word 13. Its ROM initializer is at flash `0x9e94`. This block lies immediately **after**, not within, the persisted 44 bytes. The signed drive result is at RAM `0x2000063c`; positive values call `0x8e88` and `0x8f28`, zero/negative values call `0x8ed8` and `0x8f78` with negated low 16 bits. Physical coil polarity and brake/coast behavior require circuit or trace evidence.

Some synthetic counterexamples clarify why stock must not be rewritten as a standard modulo unwrap:

| Raw | Reference | Stock relative | Stock protocol | Conventional shortest signed relative |
|---:|---:|---:|---:|---:|
| 16383 | 0 | 0 | 4096 | −1 |
| 10000 | 0 | 10000 | 6596 | −6384 |
| 10001 | 0 | 6382 | 5691 | −6383 |
| 0 | 8192 | 8191 | 6143 | −8192 |
| 0 | 16383 | 0 | 4096 | 1 |

These are synthetic fixtures, not physical calibration. Protocol target 4144 becomes stock count 192; 5632 becomes 6144; 12288 wraps to −32768. Clamp policy belongs to callers, not `0x8dd4`.

## Cadence, stop and command transitions

`0x65ac` initializes the TCC1 descriptor at `0x200008e8`. `0x658c` enables its APBC clock and routes GCLK0 (CLKCTRL `0x401a`). Configuration lookup `0x834c` selects the record at RAM `0x20000414` (hardware `0x42002400`, IRQ16). `0x8378` writes CTRLA `0x300` (DIV8), WAVE 0 (normal frequency) and PER 7500 directly. GCLK setup `0x770c` selects DFLL48M for generator 0 with divisor 1. IRQ `0x86e0` reaches `0x8306`, clears the overflow flag and invokes the callback installed by `0x6090`.

Under the nominal 48 MHz clock, overflow period is `(7500+1)*8/48 MHz = 1.2501667 ms`. The callback `0x8a2c` calls the PID path when the **old** divider equals 10, then resets it: every 11 callbacks, nominal 13.751833 ms. The main loop samples the sensor when callback-set work flag `0x20000604` is observed; multiple interrupts can coalesce into one sample. PID uses the latest main-loop sample rather than triggering its own SPI read. ISR latency, main-loop blocking and actual DFLL rate have not been measured.

An armed timeout begins at zero and increments until it is already 300; stop is called on the **301st callback**. Depending on the command's phase relative to the next overflow, elapsed nominal time is about 375.05–376.30 ms. This timeout has no separate error outcome: stop sets the same completion flag as ordinary completion. The PID divider is not reset on target replacement. PWM setup `0x904c → 0x6b5c → 0x8674` writes period parameter 2560 directly to PERB; neither the denominator convention in upstream duty comments nor physical output percentage is a measured result here.

| Trigger / gate | Stock transition |
|---|---|
| Focus receive `0x5308`, declared length !=`0x16` | Set stop/restart flag, remember previous kind, take new kind from length byte. Length `0x1b` copies two targets; `0x24` copies only the first, retaining the old second target. |
| Main protocol pump `0x5cc8`, restart flag | Reset command state to 0 and stop before processing pending command. Dispatch `0x1b → 0x5c08`, `0x24 → 0x5a94`, `0x17 → 0x5b98`. |
| Absolute-like `0x5c08`, state 0 | Clamp first signed target to advertised unsigned limits; set boundary flag; start target, state 1. On completion create event `0x1d`, state 2; on subsequent service stop and enter state 10. |
| Scan-like `0x5a94` | State 0 reports progress `0x10`, then state 1 clamps first target and starts it. State 2 completion starts retained second target **without the same clamp**. State 4 waits, state 5 publishes event `0x24`, then state 10. State 6 has a separate three-counter stop path; ordinary entry to that state is unresolved. |
| Stop-like `0x5b98` | Stop, issue event depending on prior kind (`0x24` or `0x1b`), then event `0x1c`. |
| Repeated RX byte 9=`0x81` | `0x5308` asserts flag `0x52a` on the eleventh occurrence; another value clears count/flag. `0x5e00` uses a one-shot latch at `0x390` to start the advertised lower target. Meaning of this camera bit remains uncertain. |
| Shutdown ID `0x16` at `0x58a4` | Set shutdown request/state0. `0x5e00` optionally targets advertised lower bound if persisted park option is nonzero; wait for completion, acknowledge using RX buffer, delay, disable UART, wait for input condition, enter sleep. Completion may be timeout-derived. No newly observed reference update in the ordinary park path. |
| Homing gate `0x530` | If nonzero: drive both negative channels at800, delay300, stop, delay500, sample/reference/sample, persist and clear gate. Delays `0x66fc → 0x72f4 → 0x8250` use 48000 core ticks per requested unit, nominal milliseconds. No ordinary enabling writer was found. |

All abbreviated RAM addresses in this table have base `0x20000000`.

## Persistence and alias assessment

See [the complete 44-byte field table](stock-settings-schema.csv). Unknown bytes are explicitly retained rather than assigned speculative meanings. The live record is RAM `0x20000494..0x200004bf`, backed by flash `0x4100..0x412b`. The official app file begins at `0x5000`, so this per-unit record is **not contained in an app-only update**.

`0x8ae4` restores eleven words and copies focal offset `0x26` into active RAM `0x680`; it also establishes the advertised lower bound 4144. Main `0x8b70` initializes sensor/reference (`0x8c80`), starts timer callback, stops motor, delays, and only then restores the persistent record. Thus boot-time “safe defaults” do not establish the restored armed/direction/completion values. No magic/version/checksum/range validation is visible in this restore routine.

`0x5d68` writes the full 44 bytes through the NVM abstraction. `0x5da8` clears dirty flag `0x608`, sets reference from current sample, and writes. The ordinary dirty branch in `0x5e00` instead copies active focal to offset `0x26` and writes **without replacing reference**. Aperture-coded menu `0x56cc` sets dirty via `0x5510`. The homing block uses the reference-changing path. Exact power-loss atomicity and the underlying NVM row-preservation behavior have not been validated.

The alias pass propagates constants through original instructions, merges CFG paths conservatively, kills volatile registers at calls, accounts for LDM/STM widths and follows recovered switch destinations. It resolved 1,784 memory accesses, including 83 to the settings record, leaving 603 unresolved pointer-based accesses. It found only a gate read at `0x5e34` and clear at `0x5eae`, in addition to startup BSS clearing. RX DMA is armed for 255 bytes at `0x20000694`, not near the homing gate. This is stronger than literal cross-references alone, but is not interprocedural pointer analysis or proof against arbitrary corruption. Treat homing as **unreachable in recovered normal paths**, not as an invitation to force its gate.

## Input framing and overwrite dependencies

A correction to the first-pass label: the general reply dispatcher is **`0x58a4`**. `0x56cc` handles the aperture-coded focal/options menu.

`0x58a4` requires initialized mode1 and RX byte3=2, then bounds byte5 to ≤`0x5a` before the 91-entry jump table at `0x95f8`. It does not itself validate F0, terminator, checksum, declared length versus actual received length, or minimum payload size. DMA reception arms 255 bytes; the recovered consumers use fixed offsets and declared-length branches, without a received-count argument. This establishes consumer behavior, not a hardware exploit or a complete transport proof. The receive buffer is not cleared by `0x5308`; short/partial transport deliveries can leave old bytes for these consumers unless another layer supplies a guarantee not yet established.

Normal focus handling is fixed-layout, not a general record-stream parser. The phase machine and frame-sync edges decide when to invoke it. In particular, a `0x24` length retains target2 from an earlier `0x1b`, confirmed by original-instruction fixtures. Upstream's broader focus record parser must not be described as recovered stock behavior.

Reply IDs recovered: `01,07,08,09,0a,0b,0c,0d,10,19,1b,28,32,34,3d,3f,4c,5a`; shutdown is `16`. Response `1b` echoes request bytes and applies menu side effects before transmit. `0x51d4` rewrites low length and `55` terminator, sums bytes1 through length−4 inclusive and writes the low16-bit checksum at length−3. Static checksums will be overwritten during send.

## Pinned upstream C: what changes the controller

| Area | Official stock | Pinned upstream C |
|---|---|---|
| Encoder | Asymmetric fixed-reference arithmetic above | `abs_encoder_position` uses shortest signed reference distance; `abs_encoder_track` integrates shortest successive deltas modulo16384. Its comment equating that to `0x8cc0` is inaccurate. |
| Position map | `(target−4096)*4`, signed16 narrowing; caller-specific clamps | `focus_map.c` clamps to0..5952 and anchors protocol4144 at count0. This differs by192 counts from stock at the lower bound, independently of physical calibration. |
| Control law | Direction-latched stepped desired speed and incremental PID | `servo.c` uses error-proportional speed, measured elapsed time, feed-forward with acceleration term, proportional velocity correction and climbing boost. The `STOCK` configuration name in `main.c` does not make this the factory algorithm. |
| Cadence | 11 TCC1 overflows; nominal13.75ms from recovered config | Polled control after≥5ms; uses actual elapsed milliseconds. |
| Completion/guards | Position crossing or common timeout completion | Position+speed+dwell arrival, stall, wrong-way120, runaway600, per-leg/total timeouts, reversal handling. |
| Retarget | Stop/restart command state; target setter preserves PID memory | Replaces target within servo loop, uses deadband/retarget cap, optional reversal brake and rebasing. |
| Origin/homing | Restores persisted reference; ordinary enabling homing writer absent | `motor_home` deliberately establishes a new physical zero; upstream comments explicitly identify this as an experiment. |
| Park | Persisted option; target advertised lower limit; stock timeout | Separate PARK servo configuration and `g_homed` gate. |
| Protocol/optics | Fixed offsets/length cases and copied lens tables | Broader command parsing, focus-distance mapping/prediction and software policy. These require separate validation. |

This comparison supports an opt-in experimental candidate, not a claim of stock-equivalent AF. Neither firmware's code proves encoder counts/mm, physical end stops, coil polarity, friction, reversal safety, camera optical expectations, or behavior with the actual lens. Upstream's hardware observations are claims from that source, not measurements repeated here.

## Validation milestone and remaining evidence

1,870 original-instruction cases/steps pass independent model assertions: speed155, PID1004, target conversion60, sensor wrap110, completion225, timer callback302, fixed-layout extraction12 and retarget preservation2. PID tests include deterministic random full-width states and overflow. Sensor reads, stop and PID callees are stubbed only in the respective isolation tests; other tested routines run the original instructions and original signed division helper. These are arithmetic/state tests, not emulated camera sessions or motor tests.

Eleven additional explicit PID examples (including the quotient-zero/floor boundary and history stores) pass and are published in [the synthetic fixture table](stock-af-fixtures.csv). They are separate from the 1,870-case suite above.

Private annotated pseudocode is in `reconstructed-af.md`; all233 raw dossiers remain alongside it. Remaining highest-value work is: complete interprocedural write/alias closure; establish actual TCC1 time base from trusted traces; validate response/focus layouts against recorded camera exchanges; inspect NVM row handling/power-loss behavior; and obtain physical origin, travel, polarity and lens optical calibration under a separately authorized hardware plan.

The non-flashable patch assessment is in [stock-metadata-patch-feasibility.md](stock-metadata-patch-feasibility.md). No patched firmware was created. Metadata byte edits are plausible, but a coherent, stock-preserving 50mm f/1.4 patch is **not yet justified** because runtime overwrites, unit settings, camera-driven menu policy and optical tables must be resolved together.
