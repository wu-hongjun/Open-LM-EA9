# Follow-up 37 — lossless packet initializer storage

The exact private 3.7 composition in `artifacts/private/targeted37c` passes this
bounded representation and startup review. All **1,272 bytes**, including zero
bytes and padding outside packet payloads, equal the frozen 3.6 initializer.
Packet descriptors and fixups are unchanged. The complete ARM image saves
**648 loaded bytes**, leaving **328 bytes** before diagnostics; static RAM
remains **3,044 bytes**. Packet compilation retains the release's default
`-O2`; no core control flags or wire-format changes are introduced here.

This is a storage representation change with additional startup work. It does
not establish a camera-freeze root cause or fix, complete wire parity, factory
qualification, physical startup timing, or interrupt safety under arbitrary
inherited state. Hardware acceptance remains separate.

## Implementation and initialization contract

The [applicator](../../firmware/upstream-hardening/followup/37-packet-initializer/apply.py)
requires exact frozen hashes for `emount_packets.c`, `emount_packets.h`, and
`startup_samd21.c`, and refuses the frozen base directory. It encodes the
1,272-byte table as a 159-byte bitmap plus 374 nonzero values. The writable table
moves from initialized data to BSS and retains its full size. Its descriptors,
fixups, offsets and lengths are unchanged. The function declaration is inside
the header guard.

`Reset_Handler` completes data relocation and BSS clearing, calls
`ea9_packets_init()` once, rewrites VTOR, executes the existing startup work and
C constructors, then enters main. The initializer explicitly writes every
byte, including each of the 898 zero bytes; it does not depend on its destination
already being zero. Repeating it restores the original table, which is suitable
for a test reset but would erase live packet edits if called during operation.
There is no new runtime call or production host constructor.

The array bounds follow directly from the pinned generated representation:
`dest` visits 0–1271, `dest >> 3` visits 0–158, and the 374 set bitmap bits consume
values 0–373 exactly once. `dest & 7` bounds the shift to 0–7. All array sizes and
the complete reconstructed output are checked independently in the linked ELF.
This is a fixed immutable-table contract, not validation of corrupted flash.

**The call precedes this reset handler's VTOR rewrite, not the first selection
of application vectors.** The original bootloader already selects application
VTOR before entering the application reset handler. The initial draft's
“before app interrupt delivery” comment was corrected. The
[boot-entry audit](astra-24-boot-entry-2026-10-15.md) establishes conditional
ordinary-reset preconditions and preserves inherited PRIMASK, CONTROL and NVIC
state. This change neither masks interrupts nor normalizes that state. The
existing conditional no-exception initialization interval becomes longer.

## Independent execution and byte evidence

The [runner](../../firmware/upstream-hardening/followup/37-packet-initializer/run.py)
and [retained result](../../firmware/upstream-hardening/followup/37-packet-initializer/result.json)
check all frozen base source pins, every candidate manifest source pin, and the
candidate image digest. The ELF's physical load segments must exactly cover and
match `raw.bin`, which must match the image prefix. All candidate ARM units are
rebuilt with the release flags and per-unit flags; rebuilt load bytes equal the
supplied image. Debug-file paths are not required to produce identical ELF files.

The expected packet bytes come from the frozen 3.6 ELF symbol, then are compared
with a separately compiled original C initializer on the host. An independent
bitmap decoder compares every output byte with that reference. Linked packet
descriptor and fixup bytes also compare exactly with the frozen ELF. Native
AddressSanitizer and UndefinedBehaviorSanitizer tests poison the destination,
explicitly initialize it and compare all bytes on three repetitions. These
explicit calls model packet initialization only; they do not model processor
reset, startup ordering, constructors or interrupt state. Other host suites need
their own explicit reset adapter when replacing the old C static initializer.

Unicorn then executes the **actual linked ARM Reset_Handler and all callees**,
including the initializer and C library startup, stopping before main executes.
There are no function-return stubs. Three cases use RAM fill `0xa5`, `0xff`, or
zero and incoming PRIMASK 0 or 1. At initializer entry, the relocated data must
match its flash source and all BSS must be zero. At the reset handler's VTOR
write, initialization must have returned, all 1,272 destination offsets must
have been written in order, and the entire table must match. It must still
match at main entry. All three cases pass and preserve PRIMASK.

The ARM build performs 1,271 bitmap loads: `-O2` folds the first bitmap value
into an immediate instruction. The runner checks the exact remaining bitmap
read offsets and the exact value offsets 0–373. Writes during initialization
are restricted to the table and its stack window. These observations complement
the fixed source bounds; they are not a memory-corruption resilience claim.

Each reset-to-main fixture executes 33,029 instructions, of which 17,674 belong
to the packet initializer. The observed stack use is 40 bytes during the
reset-plus-initializer call, consistent with the 16-byte reset frame and
24-byte initializer frame. The whole reset-to-main fixture reaches 56 bytes
while also executing library startup. These are finite trace observations,
not a whole-program stack bound or physical high-water measurement.

The emulator starts in privileged thread mode using MSP, with no active or
delivered exception, and VTOR already `0x5000`. Memory-mapped peripheral registers
are inert zero-filled memory; existing startup writes execute normally. No
interrupt scheduler, peripheral progress, elapsed-time model, bootloader
execution or physical device is included. Instruction counts are not cycles or
elapsed startup time. As in the earlier audits, Unicorn execution alone is not
an independent ARMv6-M instruction-legality certification.

## Negative controls and size reproduction

Five deliberate failures are rejected:

1. Removing the actual ARM initializer call fails the VTOR completion check.
2. Clearing a set bit in the linked bitmap fails full-table equality.
3. Changing a linked value byte fails full-table equality.
4. Compiling startup with the call after VTOR fails the ordering check.
5. Changing a byte of the original source initializer fails the applicator's
   frozen-source hash check before transformation.

All mutations are confined to emulator memory or temporary private build trees.
The tested candidate sources and ELF are rechecked at the end and remain intact.

For the size comparison, the runner restores only the three original startup
and packet source/header files in a private copy of the complete candidate and
rebuilds the affected ARM objects with identical flags. The uncompressed
composition ends at `0x9d40`; the candidate ends at `0x9ab8`. Their difference is
648 bytes, and both use 3,044 bytes of static RAM. The uncompressed comparison
is intentionally not a loadable release candidate: it exceeds the diagnostics
boundary. The accepted candidate retains the existing `0x9c00` diagnostics
boundary and exceeds the 256-byte build margin floor by 72 bytes.

| Exact input | SHA-256 |
| --- | --- |
| Candidate image | `6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5` |
| Candidate manifest | `15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b` |
| Candidate ELF | `f7ae647169d14b81495e14c6b061372ed1f135c4fc904e4b1ff2f338d79a873a` |
| Full original/restored packet table | `17429693f3ed56ff71cd1ee641ee03d886f073a184305e1d847c8937b4fa7060` |

```sh
tools/rea-analysis/venv/bin/python \
  firmware/upstream-hardening/followup/37-packet-initializer/run.py \
  --source artifacts/private/targeted37c \
  --output artifacts/private/astra-37-packet-recheck.json
```

No hardware enumeration, USB/HID interaction, updater, application launch,
canonical Application Support write, flash, commit or push occurred in this
lane. No published firmware or frozen base source was modified.
