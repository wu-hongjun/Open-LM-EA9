# Stock NVM, reset, and driver reconstruction

Offline reconstruction of the official 1.8.0 application, SHA-256 `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`. Addresses below are original flash/RAM addresses, not replacement source symbols. This supplements [the phase 2 dossier](stock-phase2.md). Original instructions and their recovered call paths are evidence; matching Microchip headers identify register semantics, not proof that a particular SDK release built this binary.

## Settings persistence: important correction

The save wrapper at `0x5d68` attempts unlock, write, lock, but **its unlock and lock calls cannot succeed with their supplied count**. It passes count **1**. The lower routines at `0x79e4` and `0x79a0` require count **256** and 256-byte-aligned address. They return `-13` for count 1 without issuing an NVM command. Original Thumb execution confirms this. The wrapper ignores all three return values.

The middle write succeeds only if the region is already unlocked. At address `0x4100`, lock-check routine `0x7a28` tests NVMCTRL LOCK bit 1 (`address >> 14`); a zero bit means locked. The write HAL at `0x6918` returns `-17` in that case. No retry, verification, or user-visible status propagation occurs in `0x5d68`. This is stronger evidence than interpreting the apparent function names as successful operations. It does **not** establish the physical unit's current lock state.

| Entry | Reconstructed responsibility | Evidence / limitations |
|---|---|---|
| `0x5d68` | Unlock `0x4100,1`; write 44 bytes from `0x20000494`; lock `0x4100,1` | All status results discarded |
| `0x6918` | Validate descriptor/source/nonzero length through assertion; compare range with page-size × page-count; test lock; call lower write | Page-size `0x40` from `0x7870`, page-count `0x1000` from `0x7874`; these are hardcoded software bounds, not detected capacity |
| `0x6894` | Reject address not aligned to 64 bytes | Used by lock/unlock HAL, not byte-write HAL |
| `0x69b0`, `0x6a38` | Lock/unlock HAL: validate alignment and page-count bounds, divide address by page size, call HPL | Successful HPL requires count `0x100`, not 1 |
| `0x79a0`, `0x79e4` | Require count 256 and 256-byte alignment; wait READY; clear status; set halfword-address; issue LR/UR | Commands `0xa540` / `0xa541`; returns 256 immediately after command, without a final READY wait |
| `0x7a28` | Return true if addressed region is locked | Reads LOCK halfword at peripheral `+0x20` |
| `0x78c8` | Read-modify-erase-write complete rows | Details below |
| `0x787a` | Copy flash into RAM, handling odd starting address | Wait READY and clear status before reading |
| `0x7768` | Wait READY, clear status, set ADDR to byte-address / 2, issue keyed command | Called with erase-row command 2 |
| `0x7788` | Clear page buffer, load halfwords, issue page write | Called with 64-byte length and command 4 |

### Exact preservation boundary

The lower writer allocates a stack buffer, rounds the destination down to a 256-byte row, and reads four 64-byte pages. It replaces only requested bytes in the buffer, erases the complete row, and rewrites **all four pages**. It repeats for subsequent rows when necessary. The 44-byte save at `0x4100` therefore rewrites `0x4100..0x41ff`; bytes `0x412c..0x41ff` are intended to retain their pre-save values. Adjacent rows are untouched. The implementation is not a 44-byte-only flash operation.

Private annotated pseudocode and fixtures are in `references/private/rea-analysis/phase3/nvm-drivers`. No per-unit settings bytes are published here. Meaningful synthetic tests execute the original row merge instructions and independently compare every output byte, covering aligned 44-byte writes, unaligned writes, page crossing, row crossing, and full rows.

The software has no two-copy journal, CRC, generation counter, or atomic commit in this path. RAM buffering preserves neighboring bytes only if the entire erase/rewrite sequence completes successfully. Power interruption after erase can lose settings and the retained portion of that row. This follows from the command sequence, not a physical fault-injection result.

### Error behavior

Both command helpers wait for READY before work. Status at NVMCTRL `+0x18` is cleared with `0x11f`. There is no synchronous PROGE/LOCKE/NVME check after each page command. `0x6918` returns zero after the lower writer returns, regardless of such peripheral error bits. The last page command has no final READY polling loop before return; later NVM operations may wait, but the save wrapper's rejected lock call adds no such wait.

The NVM interrupt at `0x7a40` can dispatch ready/error callbacks through a descriptor at `0x2000087c`, registered globally at `0x200005f0`. Initialization installs HAL forwarding functions `0x687c`/`0x6888`; they call user callbacks at descriptor offsets `+0x14` and `+0x18` only when nonzero. This does not by itself establish an application recovery policy or that the peripheral's interrupt enables are set for this save.

Range checks use 32-bit arithmetic, including `address + length`, without a separate overflow check. Stock's fixed address and 44-byte count do not approach that issue. Assertion failures use the stock assert routine; tests stub assertion reporting only for valid arguments.

## Reset and clock chain

`0x6144` copies initialized words from flash `0x99d4` to RAM `0x20000000..0x200004f7`, then zeros `0x20000500..0x20000aaf`. The eight bytes at `0x200004f8..0x200004ff` are not covered by either loop; do not infer their reset contents. It sets VTOR to `0x5000`, performs early peripheral writes, calls C runtime initialization `0x9540`, then application main `0x8b70`. If main returns it spins forever. The application image is linked behind a separate bootloader and is not evidence of reset behavior before application entry.

Main calls board initialization through `0x5114 -> 0x65d8`. Board initialization calls `0x7300`, establishes GPIO configuration, then initializes EIC, NVM, SPI, UART, SysTick delay support, TC4, TCC0 PWM, and TCC1 in that order.

| Function | Clock / controller behavior | Confidence |
|---|---|---|
| `0x8154` | Enables/configures OSC32K and OSC8M; waits oscillator readiness | High, direct registers |
| `0x81b8` | Loads DFLL coarse calibration from factory fuse at `0x00806024`, with fallback; writes DFLLCTRL `0x82` | High; calibration values deliberately not reproduced |
| `0x770c` | GCLK GEN0: DFLL48M, divide 1; GEN1: OSC32K, divide 1; GEN2: OSC8M, divide 1 | High, register writes decoded with local headers |
| `0x7300` | Calls oscillator init, GEN1 setup, DFLL setup, remaining generator setup, then DMA init | High, call order |

DFLLCTRL `0x82` enables the DFLL and on-demand mode but leaves MODE clear: this is **open-loop DFLL operation**. Consequently 48 MHz and derived timer/PWM periods are nominal, not measured or guaranteed closed-loop accuracy. No evidence in this chain justifies claiming a crystal-disciplined 48 MHz clock.

`0x8230` sets SysTick LOAD to `0xffffff` and CTRL to 5: enabled, core clock, interrupt disabled. SysTick thus serves polling delay support; the default SysTick vector is compatible with this. Application delay `0x6120(n)` loops `n` times around `0x60cc(1000)`. Its wall-clock units depend on the delay implementation and actual core frequency; it is not an RTOS sleep.

## Driver objects and producer/consumer relationships

| Object / state | Producer | Consumer / meaning |
|---|---|---|
| NVM descriptor `0x2000087c`, hardware `+0x10` | `0x62ec -> 0x68cc -> 0x7808`, hardware `0x41004000` | Settings save HAL; global pointer `0x200005f0` used by NVM IRQ |
| SPI descriptor `0x20000864`, hardware `+4` | `0x63e8 -> 0x6b8c -> 0x7e0c`, SERCOM0 `0x42000800` | Sensor synchronous transfers; I/O method pointers at descriptor `+0xc/+0x10`, dummy word at `+0x14` |
| UART descriptor `0x20000898` | `0x6474 -> 0x7008 -> 0x7cb8`, SERCOM1 `0x42000c00` | Camera protocol; 16-byte ring backing at `0x20000538`; HPL callbacks installed at descriptor `+8..+0x14`; hardware at `+0x20` |
| UART HPL object `descriptor+8` | `0x7b3c` stores pointer globally at `0x200005f4` | SERCOM1 IRQ; callbacks forward to HAL transmit/receive/error paths |
| DMA base `0x20000910`, writeback `0x200009d0` | `0x7358` sets BASEADDR/WRBADDR and initializes 12 channels from ROM configuration | DMAC IRQ; protocol uses channel 0 transmit, channel 1 receive |
| TC4 timer descriptor `0x20000828` | `0x6208 -> 0x6d88`, hardware `0x42003000`, ops from `0x8988` | Protocol scheduling timer |
| TCC0 PWM descriptor `0x20000848` | `0x6558 -> 0x6ad8`, hardware `0x42002000`, ops from `0x86c8` | Motor drive PWM |
| TCC1 timer descriptor `0x200008e8` | `0x65ac -> 0x6d88`, hardware `0x42002400`, ops from `0x86bc` | Encoder/controller periodic callback |

Timer HAL initialization `0x6d88` stores the operation-table pointer at descriptor offset 0, passes the subobject at `+4` to the HPL initializer, clears `+0x14`, and installs default callback `0x6d24` at `+4`. Application callback registration later replaces that callback. Callback and operation-table pointers have Thumb bit set; published function addresses omit that bit.

`0x90fc` connects DMA channel 0 destination to UART DATA (`hardware+0x28`) and completion callback `0x90d4`; channel 1 source is the same UART DATA register, completion callback `0x90c0`. It also installs a UART callback `0x90e8`. This establishes direction independently of register naming assumptions. Actual byte count and buffer producer/consumer behavior is described in the protocol dossier.

SERCOM configuration comes from ROM tables consumed at `0x7bc8` (UART) and `0x7e0c` (SPI). These routines reset/disable the peripheral, wait synchronization, and apply table fields. Matching ASF-style assertion strings in the original identify `hal_usart_async.c`, `hal_spi_m_sync.c`, and `hpl_sercom.c`; this is evidence of family/structure, not a guarantee of source-version equivalence. Full electrical UART/SPI rate validation remains open.

### Pin setup recovered directly

`0x630c` selects function D for PA4/PA5/PA6, with PA5 output/high and PA6 input setup. `0x6430` selects function D for PA0/PA1 (UART). `0x64c0` selects function E for PA8/PA9 and F for PA18/PA19 (PWM outputs). `0x6248` sets EIC-related PA2/PA3 mux/configuration. These are register-level pin configurations; sensor wiring, H-bridge polarity, pull circuitry and physical motion direction remain external assumptions. Decompiler addresses in the `0x60000000` region are SAMD21 PORT I/O-bus aliases, not ordinary SRAM writes.

## Validation and remaining closure

Run locally with the prepared private environment:

```sh
tools/rea-analysis/venv/bin/python tools/rea-analysis/phase3_nvm_tests.py
```

**26 original-instruction cases passed**: eight lock/unlock combinations, two lock-gated write cases, eight complete row preservation cases, five odd-address/cross-boundary reads, two actual page-loading/command cases, and one failed-status save sequence. Input hash is asserted before execution. Fake NVM registers and flash I/O exist only inside emulator memory. The source firmware file is never modified. These tests validate CPU-side decisions and transformations, not real flash programming, silicon timing, interrupt races or power-loss behavior. The installed emulator also does not strictly reject every unsupported ARMv6-M instruction; it is not an ISA legality oracle.

Private evidence includes exact inclusive function ranges, selected original dossiers, annotated pseudocode, and validation JSON. Still open: exhaustive callback reachability and interrupt-enable audit; whole-program alias closure; hardware rate/polarity validation; power-loss recovery behavior outside this app; ROM table-to-driver struct names and build-version matching. This document reconstructs the NVM algorithm and board initialization structure, not a complete substitute SDK or flashable replacement.

## Host C reconstruction extension

`tools/rea-analysis/nvm_reconstruction/nvm_model.c` and its header now provide host-only source for the recovered lock/count checks, HAL write-status decisions, complete-row merge, page-buffer halfword loading, and bootloader page erasure. The validator compiles that C independently and compares it with original application and bootloader instructions. Host memory guards are explicitly marked additions; no hardware registers or firmware entry points exist in the model.

The bootloader differs materially: its page-count constant is 2048 (128 KiB software bound), while the application uses 4096. Boot save wrapper `0x2534` attempts unlock(count 1), erase(one 64-byte page), write(64 bytes), lock(count 1). Both lock calls are rejected and all statuses ignored. Partial-row erase at `0x0f50` calls the row-preserving writer with an all-ones page, then the ordinary write repeats the row operation. A successful 64-byte boot write therefore performs two row erases and eight page writes, retaining the other 192 bytes of its row. This is distinct from the application's single row erase/four page writes per settings save.

Boot GEN0 uses OSC8M while GEN2 uses DFLL48M; USB selects GEN2. Boot DFLLCTRL sets USB clock recovery mode (`0xa2`), unlike the application's `0x82`. These clock differences must be preserved when comparing timing-dependent boot and application code.

The [boot inventory](stock-boot-inventory.csv) includes inline REA evidence IDs and 145 inspected function roles. The [whole boot byte partition](stock-boot-byte-partition.csv) accounts for every byte to `0x3fff`, including explicit unresolved-code and padding-candidate categories. It does not claim every byte's purpose is proven. In particular, unreferenced code at `0x2530..0x2531` and `0x34d4..0x34db`, and the pointer at `0x366c..0x366f`, remain provisional. Per-function unresolved indirect callsites remain visible in the inventory.

The compiled C validation completed **1,580 checks**: **1,514 original-instruction comparisons**, 65 independent page-loading oracle cases, and one negative control that deliberately discards neighboring row bytes and is detected. These are additional to the 26 focused NVM cases above. The private result records exact input and model-source hashes. No physical flash correctness is inferred from these synthetic tests.
