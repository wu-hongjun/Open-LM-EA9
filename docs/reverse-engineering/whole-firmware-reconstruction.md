# Whole firmware reconstruction ledger

**We have a mapped factory image, substantial reconstructed behavior and executable host models; we do not yet have a complete, buildable reconstruction of the factory firmware.** The separate upstream C replacement candidates do build, but that does not establish factory equivalence. See the [October 15 status](status-2026-10-15.md). This ledger distinguishes original-byte preservation, recovered code layout, semantic reconstruction, and finite behavioral validation. Research date: October 10, 2026 (America/New_York). All new work is offline; no device enumeration, USB reports, updater execution, flashing, or motor operation was performed.

## October 12 sensor/origin extension

The [new isolated extension](../../research/stock-1.8/extensions/2026-10-12/README.md)
adds bounded models of `0x89a4`, `0x8c64` and `0x8c80`, validated by 68,648
original-instruction cases/steps and a detected byte-order mutation. It executes
original valid SPI HAL wrappers, cuts lower peripherals explicitly, and traces
eight original main prefixes through first foreground poll. The application
semantic-model union is now **41 routine entries**; the original 38-entry suite
and its results remain intact. This adds sensor byte order and initialization/
restore-origin evidence, not physical calibration or complete firmware coverage.
Read [the new findings and precise limits](stock-re-progress-2026-10-12.md).

## Baseline and complete flash scope

The retained 128 KiB original unit dump has SHA-256 `1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`. The official 1.8.0 application is exactly 20,172 bytes, linked at `0x5000`, with SHA-256 `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`. The first 16 KiB boot region has SHA-256 `8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895`.

All ends below are inclusive. This is the layout of the retained original unit, not a statement that every byte is executed or that every header field is understood.

| Physical flash region | Bytes | Observed classification and interpretation limit |
|---|---:|---|
| `0x00000–0x03fff` | 16,384 | Bootloader region; code, vectors, constants, descriptors and padding |
| `0x04000–0x0403f` | 64 | Boot/updater metadata record; unit values remain private |
| `0x04040–0x040ff` | 192 | All `0xff` |
| `0x04100–0x0412b` | 44 | Persisted application settings/live-state record; unit values remain private |
| `0x0412c–0x04fff` | 3,796 | All `0xff`; the first remainder is in the settings erase row |
| `0x05000–0x09ecb` | 20,172 | **Exact official application**, byte-for-byte |
| `0x09ecc–0x09fff` | 308 | All zero |
| `0x0a000–0x0a07f` | 128 | Retained prefix/header; lifecycle and field meanings unresolved |
| `0x0a080–0x0ef4b` | 20,172 | **Second exact copy of the official application**, including vectors linked for `0x5000` |
| `0x0ef4c–0x0f07f` | 308 | All zero |
| `0x0f080–0x1ffff` | 69,504 | All `0xff` |

The duplicate is established by full byte equality and the same application SHA-256, not a visual resemblance. It adds no different application instruction corpus. Its preceding 128 bytes are not equal to the 64-byte metadata record at `0x4000` under either aligned half. The `0xa000–0xf07f` region has SHA-256 `a20ea14da1366d727b7fdbaf88269e4d565145719c2f85352b7cbfb35f86f897`. Calling it an active backup, recovery image, or stale upload would require additional evidence. A bounded aligned-word search of boot/app bytes found no literal `0xa000`, `0xa040`, or `0xa080`; that does not exclude address construction, indirect access, or an external updater's use.

## Code recovery and discovery coverage

The [application inventory](whole-app-inventory.csv) now contains **235 instruction-bearing functions**, 7,352 distinct instruction starts, and 14,756 bytes in exact inclusive function bodies. No function-body bytes overlap. Each function has an analyst-assigned subsystem/local role and source evidence ID. These names are interpretations, not recovered original source identifiers.

The corrected import matters. Phase 1 found 213 functions. Phase 2 retained 233 dossiers, but its `0x99c4` dossier was a one-byte placeholder with zero instructions. A section-aware import corrected that 12-byte fini stub and recovered two six-byte division wrappers at `0x930c` and `0x94e0`. The final **235** is therefore a checked instruction-bearing count, not a count of successful-looking decompiler responses. Historical phase-2 files are preserved rather than silently rewritten.

Every byte of the official application is placed into an explicit layout category:

| Category | Bytes |
|---|---:|
| Vector table | 180 |
| Provider function bodies containing instructions | 14,756 |
| PC-relative literal pools | 2,672 |
| Reviewed jump/bit tables | 472 |
| Other read-only strings and driver configuration | 592 |
| CRT function-pointer arrays | 8 |
| RAM data initializers | 1,272 |
| Alignment candidates | 216 |
| Two isolated return halfwords, not proven function entries | 4 |
| **Total** | **20,172** |

This closes the explicit application layout checklist under the stated classification assumptions. It does **not** prove that all data fields, aliases, execution paths or peripheral effects have been reconstructed. In particular, the broad read-only configuration category is not a claim that every struct member has a verified name. The isolated returns at `0x9312` and `0x94e6` have no established entry reference.

The saved application reference graph leaves 33 indirect call sites without provider-resolved flow targets. Static registration traces supply existing-function candidates for 23. The other ten involve optional/unregistered callbacks, zero targets, or generic HAL task callbacks replaced before normal application timer start. No positive candidate introduces a function outside the 235-function set. These are bounded initialization traces, not whole-program memory-alias proofs.

The separate [boot inventory](stock-boot-inventory.csv) contains **145 instruction-bearing functions** and 11,698 bytes in exact function bodies. The [boot reconstruction](stock-boot-reconstruction.md) explains its startup, USB/HID and update protocol. Together there are 380 recovered code entries across the two unique code corpora; that count is not a semantic-completeness percentage, and the duplicate application is not counted twice.

## What is reconstructed and executable

| Area | Current result | Remaining boundary |
|---|---|---|
| Factory AF arithmetic and commands | [Exact arithmetic/state dossier](stock-phase2.md); [buildable C11 host model](stock-host-model.md) for 38 original routine entries across AF, focus commands, replies, metadata and application orchestration | Motor mechanics, genuine sensing, MMIO effects and interrupt interleavings are outside the host contract |
| Initialization protocol and metadata | Dispatch, fixed-offset receive extraction, dynamic reply overwrites, focal menu and timing callbacks recovered | Handshake phase decisions and one connected nine-step fixture are modeled; timer execution is caller-supplied and DMA/camera timing remains unmodeled |
| Settings and NVM | [44-byte schema](stock-settings-schema.csv), executable restore/save orchestration and a compiled C row/lock/page model | Synthetic complete-success flash backend only; real busy/error/power-loss states and some field meanings remain unknown |
| Reset, clocks and peripheral drivers | Reset copy/clear ranges, board order, driver descriptors, callback bindings and register configuration recovered | Not a substitute SDK; electrical rates/polarities, asynchronous peripheral behavior and exact original build version remain unverified |
| Bootloader | [Update/HID and nine standard-request handlers](stock-boot-reconstruction.md) have an independent Python host model; [nine descriptor/core helpers](stock-usb-model.md) have another bounded model | Whole USB peripheral state machine, control-transfer corner cases and recovery/power-loss behavior still need full closure |
| Upper retained region | Duplicate official application identified exactly | Prefix/header purpose, writer and lifetime remain unresolved |
| Main-loop, homing and park | Software gates, ordered external-action events, sample bookkeeping and bounded shutdown scenarios modeled | Fixed sensor per call; PA3 low at both shutdown reads; supplied wake after WFI; no arbitrary interleavings or reachability proof for the homing gate |
| Working firmware image | Exact original images retained; host reconstruction sources build locally | **No reconstructed replacement image or factory metadata patch was produced** |

The host model is an explicit reconstruction of declared functions. It retains byte-addressed RAM, models integer wrapping/narrowing, and emits events for selected external actions. A private 380-entry annotated corpus supplies analyst names and provenance for the decompiler views. Automatically generated pseudocode remains analysis evidence; it is not being presented as compilable original source or a finished firmware project. The authored host models are separate implementations with declared executable contracts.

## Tests and the limits of their claims

| Evidence set | Checked scope | Result |
|---|---|---:|
| Earlier AF model fixtures | Original arithmetic, sensor seams, target/completion, callback and extraction behavior | 1,870 cases/steps plus 11 explicit PID fixtures |
| C11 host application model | Thirty-eight routine entries; every modeled RAM byte, relevant return values and ordered events; bounded handshake/main-state scenarios | 24,991 cases/steps passed |
| NVM instruction fixtures | Lock/count decisions, row preservation, odd reads, page/command sequence and ignored errors | 26 cases passed |
| Compiled NVM C model | App and boot lock/write/merge/erase decisions, page loading and neighbor-preservation negative control | 1,514 original-instruction comparisons; 65 independent oracle checks; one negative control |
| Boot callback `0x257c` | Command pairs, malformed magic, callback status, upload mode and ignored callee errors | 66,565 cases passed |
| Independent boot/HID host model | Report handler, HID request handler and descriptor-transfer wrapper; returns, lower 1,680 RAM bytes and ordered events | 65,542 report cases and 12,288 HID cases passed |
| Boot standard-request host model | Nine additional request/feature handlers; return values, 12 KiB RAM and injected service calls | 6,912 cases passed |
| USB descriptor/core helpers | Nine entries; descriptor traversal, endpoint lookup, lists, copy/fill and exceptional outcomes | 4,691 comparisons matched, including 19 expected assertion traps, three bounded nontermination outcomes and one mapped-memory fault |

These suites overlap in routine coverage and use different definitions of a case or step. Adding their counts would not produce a meaningful firmware coverage percentage. The host model's deliberately wrong sensor-wrap mutation was detected. Its separate 380,000-call UndefinedBehaviorSanitizer run checks host-language behavior, not instruction equivalence.

Original Thumb instructions run in host emulation. Hardware-facing boundaries use explicitly recorded stubs or dummy register/flash memory. Main-state cases hold the sensor input fixed for each invocation, hold PA3 low during shutdown polling, and explicitly supply a wake by skipping WFI after recording it. The USB helper suite distinguishes expected traps/faults/budget exhaustion from successful returns. These finite contracts must travel with the model outputs. There is no physical NVM programming, camera, sensor or motor behind those tests. Unicorn accepted an unsupported MOVW negative control despite Cortex-M0 selection, so passing tests do not establish ARMv6-M instruction legality. The C PID contract uses the factory denominator and normal floor/clamp parameters; division-by-zero equivalence is explicitly excluded.

## Findings that affect a faithful reconstruction

- **Timing is nominal.** TCC1's configuration has prescaler 8 and PER 7500; at nominal 48 MHz, `(7500+1)*8/48 MHz` is 1.2501667 ms. The callback's old-divider comparison yields one PID update every 11 callbacks, nominally 13.751833 ms. DFLLCTRL `0x82` selects open-loop operation, so neither interval is a measured or guaranteed physical rate. Main-loop sample flags can coalesce, and PID consumes the latest foreground sample.
- **Stock is not the upstream experimental controller.** Stock uses asymmetric reference-relative wrapping with 16383, incremental integer PID, retained history across retargets, and fixed callback cadence. The pinned upstream implementation differs in unwrap, control design and scheduling. Porting upstream source is not reconstruction of the factory algorithm.
- **Boot and app clocks differ.** Boot GEN0 uses OSC8M and USB GEN2 uses DFLL48M with USB recovery enabled (`0xa2`). The app GEN0 uses DFLL48M with `0x82`. Reusing an app timing assumption for boot code would be incorrect.
- **Persistence is more than configuration.** The saved record includes live motion state as well as reference/focal/options. Restore occurs after initial sensor setup and motor stop. Unknown bytes and per-unit values cannot safely be replaced by invented defaults.
- **The save wrapper's apparent unlock/lock operations fail.** It passes count 1 to lower routines requiring 256; the errors are ignored. The middle write is lock-state dependent and rewrites the full 256-byte row through a RAM merge. A faithful model must preserve this behavior rather than silently correcting it.
- **A simple metadata byte patch is not yet defensible.** Runtime overwrites, aperture constants reused in address calculations, saved focal state, optical tables and camera expectations remain relevant. The [patch assessment](stock-metadata-patch-feasibility.md) is a dependency dossier, not a flashable patch.

## Evidence and reproducibility

This investigation follows the pinned local [REA skill](../../references/upstream/morluto/rea/.agents/skills/reverse-engineer-anything/SKILL.md), [native guide](../../references/upstream/morluto/rea/.agents/skills/reverse-engineer-anything/references/native-and-artifacts.md), and [evidence/verification guide](../../references/upstream/morluto/rea/.agents/skills/reverse-engineer-anything/references/evidence-workflows.md): immutable input identity, exact inclusive bodies, explicit observations versus inferences, retained limitations, finite reconstruction claims and closed owned sessions.

The corrected boot analysis ELF is `6ce9bb156694b18724515d34438927e1fe3868dfea6b6b48203993892d2d2510`. The corrected application analysis ELF is a derived, non-flashable container, SHA-256 `caa437c4cd57d7b70a6c6d15c9eedc6e27c4712029cf545affe8e49df428eeb1`. Representative final evidence IDs:

| Claim | Original address | REA evidence ID |
|---|---|---|
| Reset/data/BSS sequence | `0x6144` | `ev_8c45b5a328112c62e2fdac9cef13024ffc64117dc378b1180ebbe0c36cf96f13` |
| Motion callback divider | `0x8a2c` | `ev_2cde0a159158ea51f5be5ea6f7a97128b886d93af76d9feffab6edd6ea10d6a5` |
| TCC register initialization | `0x8378` | `ev_38a7c3341bfef477d33e2cd83d7dbd6a7dc42bccb5376bab4f720ea61fd8a875` |
| DFLL setup | `0x81b8` | `ev_b8f8d407a23e876bd33ae6b2cac1a3e9e609599246a0bfa36628fd4c343a3e1c` |
| Corrected fini stub | `0x99c4` | `ev_f6180c6683b13c0a4eabbf1e7cf15b2d4b0e607033a36efd936b60523a06c637` |
| Settings save wrapper | `0x5d68` | `ev_d212bd430c10c6c3a336d70264a9549ec1f48b082ce9dbc2c41e77aeeb6ed5be` |
| Row merge/write | `0x78c8` | `ev_a0d11894aab950d8935f7ba6890a09db95590950d4aad18ced1c8c5ea39bffe6` |
| Boot update callback | `0x257c` | `ev_c24707b0cec8c8a3b9720bfbddd65829f56193ffcfdd6a3b3fe612c9cdea46c2` |

Raw dossiers, pseudocode, source hashes, fixture results, full-flash classification checks and review findings remain under `references/private/rea-analysis/phase3/`. Public tables disclose addresses and interpretations, not per-unit calibration or binary payloads. The application C/header and finite validators are now tracked under [`research/stock-1.8/`](../../research/stock-1.8/README.md); [the Oct 11 public reproduction](../evidence/stock-model-reproduction-2026-10-11.md) reran 24,991 comparisons across 38 routine entries and ten input/output guard tests. Earlier ignored sources and the separate boot/NVM/USB model tools remain preserved under `tools/rea-analysis/`; those other suites have not been promoted by this change. A public application model does not close the remaining whole-firmware boundaries.

## Required work before claiming an entire reconstruction

1. Resolve provisional boot code/padding/pointer categories, the upper prefix and remaining callback/alias targets under a written execution model. The 380-entry static corpus and byte partitions are already recorded; do not repeat discovery merely to inflate counts.
2. Integrate the existing application, NVM and boot/USB models behind shared memory and event interfaces. Extend the bounded handshake, restore/save, park/homing and shutdown cases to reset-to-handshake and focus/stop/park sequences with changing inputs. Replace caller-supplied callback execution with an explicit scheduler rather than treating the already-modeled phase decisions as physical timing.
3. Model peripheral state and interrupt ordering sufficiently to state which races, polling waits, DMA counts and failure paths are equivalent. Preserve the distinction between memory-backed test registers and hardware semantics.
4. Recover or explicitly replace every required data/configuration object and boundary, with per-unit inputs kept separate. Produce a freestanding build and compare observable behavior before calling it a replacement firmware.
5. Any physical validation needs a separately scoped hardware plan addressing calibration, travel, polarity, timing, optics and recovery. Nothing in this offline reconstruction authorizes deployment or supplies those measurements.
