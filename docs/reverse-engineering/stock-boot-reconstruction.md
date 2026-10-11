# Stock bootloader: offline reconstruction

This extends the application investigation into the original first16KiB of flash. Its SHA-256 is `8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895`. Original unit metadata and identifiers are not reproduced here. The final analysis ELF is `6ce9bb156694b18724515d34438927e1fe3868dfea6b6b48203993892d2d2510`; it preserves all16,384 source bytes and derives RAM initialization from reset. It is an analysis container, not a replacement firmware.

## Startup and architecture

Reset `0x012c` copies flash `0x3670..0x3703` to RAM `0x20000000..0x20000093`, clears BSS `0x20000094..0x2000068f`, sets VTOR tozero, performs early bus/register setup, calls constructors and main `0x269c`. Its initial SP is `0x20001690`. Init/fini code at `0x3650`/`0x3660` is executable code separated from neighboring pointer arrays; corrected analysis sections prevent an empty decompiler placeholder being mistaken for a recovered function.

Main initializes board state through `0x0114` and samples PA23. Low invokes `0x2510`, loading MSP from the application vector at `0x5000`, setting VTOR=`0x5000`, then calling its reset vector. No image validity/signature or vector-range check appears on this path. High initializes USB through `0x3380`, registers report callback `0x257c`, arms a64-byte receive, and spins at `0x26f0`. The callback, not the idle main loop, services transfers. There is no ordinary later strap recheck or discovered launch command.

| Layer | Recovered entries / behavior |
|---|---|
| Board and clock | `0x0308` board chain, `0x0c8c` clock startup. Boot generator0 uses OSC8M; USB generator2 uses DFLL48M. Boot DFLLCTRL=`0xa2` enables USB clock recovery; the app's`0x82` does not. |
| NVM | HAL `0x0404`, `0x0450`, `0x04e8`, `0x0574`, `0x05fc`; HPL around`0x0db8..0x1098`. Host-equivalent behavior requires flash status/locking/power-loss semantics beyond CPU call traces. |
| USB HAL | Endpoint lookup/state at`0x0684` and endpoint operations`0x06f4..0x0bdc`; callbacks are registered through slots rather than all being directcalls. |
| USB peripheral | HPL initialization`0x1ae0`, endpoint configuration`0x1bf8`, transfer machinery`0x14fc`,`0x1688`,`0x1e08`,`0x22d8`. IRQ`0x2504 → 0x188c` dispatches peripheral events. |
| USB device core | `0x31e8` initializes state;`0x2c9c` resets control endpoint;`0x3164` handles SETUP callback and routes standard requests or registered function handlers. |
| HID class | `0x2984` registers interface handler;`0x2950` dispatches configure/unconfigure;`0x283c` enables two endpoints;`0x2900` disables them;`0x2764` handles class/control requests. |
| Application update protocol | `0x257c` report callback, write wrapper`0x2534`, send/receive wrappers`0x2a20`/`0x29f0`. |

The [function inventory](stock-boot-inventory.csv) assigns local semantic roles and evidence IDs to145 instruction-bearing functions. Role assignment is not whole-function behavioral equivalence. Targetless callback sites and exact source extents remain separately recorded in the private inventory.

## Report protocol reconstructed as executable host code

The authored, host-only `tools/rea-analysis/boot_model.py` models the report handler and HID class handler against caller-owned byte arrays. It contains no USB/device API. NVM and USB actions produce inert ordered events; it does not issue real transfers or program a file/image.

At report callback`0x257c`, only callback status1 dispatches. Other statuses re-arm receive. RAM byte`0x20000568` selects protocol state and its64-byte buffer starts at`0x2000056c`.

| State/input | CPU-side behavior |
|---|---|
| Idle0, four-byte magic mismatch | Re-arm receive, no send/write. |
| Idle0, command pair1/1 | Set transientstate5; call write wrapper using metadata pointer initially`0x4000` and incoming payload starting atbyte6; initialize upload pointer`0x5000`; echo report; enterstate2. |
| Idle0, command pair2/2 | Set transientstate1; copy16 metadata bytes into replyoffset6; send64-byte reply; returnstate0. |
| Idle0, command pair3/3 | Set transientstate6; assemble little-endian source address frombytes6..9; copy64 bytes into reportbuffer; send; returnstate0. |
| Idle0, any other command pair | Re-arm receive without operation. All65,536 pairs tested. |
| Uploadstate2 | Treat the entire next64-byte buffer as data, call write at current pointer, echo, advance pointer by64 with32-bit wrap; remainstate2. Header matching is not performed in this state. |
| Other nonzero states | Re-arm receive without an operation. |

The callback contains no image length, digest, end-of-upload command, or error-result check. Its write/send/receive return values do not control pointer advancement or acknowledgement. Acknowledgement therefore does not prove successful flash programming. This is tested with callees returning failure, not inferred solely from missing error strings.

START's write wrapper consumes64 bytes beginning six bytes into the report buffer: the final six source bytes lie beyond that64-byte incoming report in adjacent RAM. The instruction model preserves this behavior; it does not silently clamp it. READ uses the actual forward byte-copy routine, including overlapping RAM cases. No physical memory probing was performed during this reconstruction.

## HID control boundary

`0x2764` recognizes the matching interface's standard descriptor request and passes HID or report-descriptor pointers to the lower transfer layer through`0x272c`. For class requests, it rejects mismatched interfaces and all device-to-host class requests. It handles request9 (SET_REPORT), request11 (SET_PROTOCOL), and request3 in the accepted direction; the last returns one protocol-state byte. These are observed numeric cases, not proof of full HID conformance.

SET_REPORT stage0 asks the transfer layer to receive the declared length into its control buffer. A later stage calls an optional function pointer atRAM`0x200005c4`, if registered. Startup registers the OUT endpoint callback, not this optional control callback. The generic callback setter`0x2a50` can set it when invoked with selector2; no discovered startup call does so. This is bounded static evidence, not an assertion that arbitrary RAM corruption could never change the pointer.

Descriptor-transfer counts in the host model are the counts requested by this layer; lower-layer USB packet size, wLength clipping, stalls, retries, DMA ownership and timing require their own models. The full device stack is decompiled and locally labeled but is not claimed to have enumerated in an emulator.

## NVM implications

Boot write wrapper`0x2534` differs from the app save wrapper: it calls unlock, **erase one page**, write64, lock. Lock/unlock again receive count1, which the lower implementation rejects; results are ignored. The explicit erase itself uses the same row rewrite primitive with anFF-filled page. A successful complete write therefore performs two256-byte row erase/reprogram cycles, preserving the other192 bytes each time. See [NVM reconstruction](stock-nvm-drivers.md) for exact statuses, row boundaries and physical limitations.

The boot HPL advertises2,048 pages of64 bytes (128KiB), whereas the app HPL's constant is4,096 pages. Shared-looking library routines must be compared, not assumed identical.

## Checks and remaining work

- Original callback assertions: **66,565 cases**, including every command pair, every single-byte magic mismatch, callback statuses and protocolstates.
- Independent host-model differential suite: **65,542 report cases** and **12,288 HID cases**, comparing return value, lower1,680RAM bytes, ordered events and sent bytes. The report suite includes overlapping READ copies.
- Negative control: a model incorrectly accepting CHECK with a mismatched second command byte is detected.
- Hardware-facing actions are inert stubs/events. All flash metadata used in these tests is synthetic. Original images remain unchanged.

Counts describe overlapping test domains; they should not be added together and presented as unique firmware coverage. Unicorn's known Cortex-M0 admission limitation still applies: accepting an instruction does not prove ARMv6-M legality.

Remaining work includes peripheral transfer/register semantics, interrupts during callbacks, endpoint lifecycle/error paths, flash busy/error transitions and power-loss behavior, full pointer-alias closure, and physical boot/app-handoff validation. No live enumeration, updater, reset, flash write or motor action occurred.

## Standard control-request expansion

The Python model additionally reconstructs nine original entries:
`0x2d34`, `0x2d74` (endpoint feature operations), `0x2efc`, `0x2f48`,
`0x2fb0` (device/configuration/string descriptor response selection),
`0x300c` (descriptor dispatch), `0x3040` (status), `0x30a4` (interface state),
and `0x310c` (standard IN request dispatch).

**6,912 additional differential cases pass**, comparing return values,12KiB of
synthetic RAM and ordered service calls. This preserves descriptor response
length clipping, the recovered zero-length-packet condition, configuration
index wrap, status/stall decisions and finite optional interface callbacks.
Descriptor lookup, endpoint stall state and transfer submission are explicitly
injected service boundaries in this suite; the descriptor walkers are tested
separately. Interface tests use an absent or finite one-node callback list;
cyclic lists and interrupt races are not covered.

The original boot harness now uses return sentinel`0x1f000`. The app harness's
sentinel`0x1000` lies within boot code and is unsuitable for general boot-helper
tests. Report/HID comparisons were rerun with the corrected sentinel and still
pass. This is an oracle repair, not a firmware change.
