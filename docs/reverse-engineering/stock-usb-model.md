# Boot USB descriptor and core host reconstruction

This is an authored Python reconstruction of nine CPU-side routines from the original bootloader, checked against the original Thumb instructions. It does not implement a complete USB driver or access a physical USB device. Boot input SHA-256: `8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895`.

The source is `tools/rea-analysis/usb_reconstruction/usb_model.py`, with the reproducible harness in `validate.py`. Private JSON records fixture outcomes, source hash, original ranges and REA evidence. Published evidence IDs below identify the exact provider dossiers; suggested names are reconstructed roles, not original symbols.

## Coverage and evidence

| Entry / inclusive bytes | Reconstructed role | Cases | REA evidence ID |
|---|---|---:|---|
| `0x32c0..0x32dd` | Find descriptor by type | 1105 | `ev_716ad5908bef54f9164c1c8017b8e3893ce78b291a6250e5a29238ad330cd8dd` |
| `0x32de..0x3301` | Find endpoint before next interface | 703 | `ev_2d613cfcf4c02c5e3749d2bbf5c7e48288d5e2f58acbb88764808218772a4488` |
| `0x3304..0x3343` | Find configuration by value | 315 | `ev_c503b2ae128321cf5e915753805cfc0da411884aac0b8cf172baf71f6892f645` |
| `0x3348..0x3379` | Find string by index | 711 | `ev_a15cb262d7957a87c539f5692617b2df27da6c8b69e3e010fdcc1c79ff5b42a3` |
| `0x684..0x6b9` | HAL endpoint slot lookup | 1006 | `ev_132f4f011c206ce85ab2ce6b2e93696045ae2e5c798bd64e0f432ae3141fa4db` |
| `0xc34..0xc49` | Intrusive list membership | 211 | `ev_911c07a6be8eb91b28ea80cfa9d1b45e40d9f7e3f91a94d7da73b5378c7769ad` |
| `0xc4c..0xc7f` | Intrusive list append | 40 | `ev_fb510ef3377ddf783e615aec830eba25dfd5c93302e8b57db1867cd0656912a2` |
| `0x3528..0x3539` | Forward byte copy | 300 | `ev_956726192245b25fcd11cab62233a155a4afb6112af0765c9f06cc6a6df75631` |
| `0x353a..0x3549` | Byte fill | 300 | `ev_d13b512e9e54fa875eaaefda91b109eac24639f10eabb60c9ff62d39307b97fc` |

**4,691 differential cases passed**, including 19 expected assertion traps, three bounded nontermination outcomes, and one expected mapped-memory fault. All remaining cases returned with matching outputs; mutation routines also matched watched memory. A deliberately incorrect stricter descriptor parser diverged on an explicit counterexample, establishing that the checks distinguish stock behavior from a plausible rewrite.

## Descriptor semantics retained exactly

`0x32c0` checks whether the cursor is below the logical end, then requires `bLength >= 2`. It reads the descriptor type and returns a matching pointer. It does **not** require the entire descriptor—or even both header bytes—to fit below the end. Otherwise it advances by the one-byte length. A zero or one-byte length returns null; it does not loop.

`0x32de` applies the same cursor/length checks, stops with null when it encounters interface type 4, and returns endpoint type 5. This models endpoint scanning inside an interface without imposing additional descriptor-structure validation.

`0x3304` first finds configuration type 2. It checks `bLength >= 2`, type 2, and the configuration value at offset 5. For a nonmatching value it advances by little-endian `wTotalLength` at offsets 2 and 3. That advance is independent of `bLength`. Consequently a descriptor with `bLength=9`, type 2, and `wTotalLength=0` returns immediately for a matching value but loops indefinitely for a nonmatching value. The original instruction run reaches the harness budget; the model reports the same outcome. The unchanged cursor, immutable input, and repeated branch separately establish the nonprogress mechanism. Neither implementation is silently repaired.

`0x3348` repeatedly finds type-3 string descriptors and increments an unsigned eight-bit index. The requested argument is compared at full register width. Inputs above 255 cannot match the local counter; tests cover 300 descriptors and indices 255, 256, 300 and the maximum unsigned word. Descriptor traversal still ends at the logical bound or a malformed short header.

Pointer increments use unsigned 32-bit wrapping in the model. Tested arenas are synthetic RAM and bounded arrays; this is not a proof for every possible address wrap, unmapped flash access, or USB descriptor supplied by external hardware.

### Bounds counterexample and negative control

With logical range `[p,p+1)`, memory containing a two-byte header declaring length 255 and matching type 5 is accepted by `0x32c0`: it returns `p`. A mutant parser that rejects `p+bLength > end` returns null. The comparison explicitly detects that difference. A separate case places the first header byte at the final mapped RAM byte; reading the type then produces an emulator memory fault, also predicted by the model.

These are helper-level findings. They do not establish an externally exploitable transport path or whether the shipped descriptor tables contain malformed values.

## Endpoint and core helpers

`0x684` scans thirteen slots of 32 bytes beginning at RAM `0x200000b4`. It first compares the stored endpoint byte with the full argument. For a slot whose first byte is zero (control type), it additionally compares the argument's low nibble with the stored endpoint byte. Thus a control endpoint can match both directions and additional high argument bits. Failure returns `-1`. Tests randomize slot contents and exercise explicit alias cases; the model does not add endpoint-number validation absent from the routine.

`0xc34` follows a singly linked list beginning at the pointer stored in a head object and compares node addresses. `0xc4c` asserts that the node is not already present, then appends it and clears its next pointer. Duplicate append reaches the original assertion routine's BKPT; the harness records a trap. Cyclic lists without the requested node do not terminate in either membership or append. These outcomes are preserved rather than replaced by cycle detection. Behavior after an external debugger resumes a breakpoint is outside the model.

`0x3528` copies bytes in increasing address order. Overlapping source/destination therefore follows that exact order, including propagation when destination follows source; it is not modeled as a temporary-buffer `memmove`. `0x353a` stores the low eight bits of its value until the destination reaches destination-plus-length. Tests cover zero lengths, varied values, overlapping copies and lengths up to 128. Arbitrary negative or enormous counts are not claimed validated.

## Small cross-image identity checks

Exact original-byte matches establish these limited correspondences:

| Boot sequence | Application match | Bytes |
|---|---|---:|
| Forward byte copy `0x3528` | `0x9588` | 18 |
| List membership `0xc34` | `0x717c` | 22 |
| Critical-section entry `0x384` | `0x66cc` | 14 |
| Critical-section restore `0x392` | `0x66da` | 12 |

The searched boot fill routine had no complete exact-byte match in the application. These comparisons do not establish a shared SDK release or complete library identity. Critical-section sequences were compared as bytes, not executed as privileged-state differential tests in this suite.

## Reproduction and remaining work

```sh
tools/rea-analysis/venv/bin/python tools/rea-analysis/usb_reconstruction/validate.py
```

The harness uses original image bytes, asserted input hashes, deterministic random cases, synthetic RAM, and an out-of-image return sentinel at `0x1f000`. The model has a loop budget and the emulator an instruction budget; budgets bound execution rather than inventing a successful return. Register/model observations distinguish returns, assertion traps, mapped-memory faults and budget exhaustion.

Still outside this reconstruction: USB interrupt/event priority, endpoint-bank ownership and DMA races, bounce-buffer transfer progression, complete enumeration/state transitions, HID timing, electrical signaling, and real-host interoperability. The full [boot inventory](stock-boot-inventory.csv) continues to expose those routines and unresolved indirect callsites. Passing pure-function cases does not promote the whole USB stack to reconstructed or equivalent status.
