# Factory firmware progress: sensor path and restored position origin

Research date: October 12, 2026, America/New_York. **Factory 1.8.0 is partially
reconstructed, not completely reverse engineered or reproduced as replacement
firmware.** This contribution closes a sensor dependency that the public
38-routine host model previously cut at a supplied raw sample. It does not
change the AF 2.6 candidate, app, recovery image, stock settings or hardware.

The investigation applies the pinned [REA skill](../../references/upstream/morluto/rea/.agents/skills/reverse-engineer-anything/SKILL.md)
and its [finite evidence workflow](../../references/upstream/morluto/rea/.agents/skills/reverse-engineer-anything/references/evidence-workflows.md).
Existing static dossiers were reused; no REA native session or target process
was opened. New behavioral evidence executes the retained original Thumb
instructions in host emulation.

## New executable scope

The isolated [sensor-boundary extension](../../research/stock-1.8/extensions/2026-10-12/README.md)
contains independently authored C11 semantics for these three original entries:

| Entry | Reconstructed boundary | Prior static evidence |
|---|---|---|
| `0x89a4` | Selector-dependent GPIO writes, two-byte SPI response, byte order and fourteen-bit result | `ev_01b06c81fd028cecb6fffcb6df260c2c3d01c21ac610dafe80dd3b4b3d96884c` |
| `0x8c64` | Eight exact word writes to the state block at SRAM `0x20000a90` | `ev_fb144e51b87f6b0c7aed060066f00f6ece8bafe8de1a0ce4cf7a2b1444efc2a1` |
| `0x8c80` | Filter-state initialization, selected sensor read and initial motion/reference fields | `ev_30e1f5c962a02d714962cce9ebd4c7ae4aad6fffcae62dc49a9c612945670331` |

The exact oracle is the public [stock application](../../firmware/recovery/stock-1.8.0/application.bin):
20,172 bytes at `0x5000`, SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
The shared public host model and the original input are unchanged. The extension
also composes the existing restore `0x8ae4`, position `0x8cc0` and boot metadata
`0x8a8c` models; these are not counted as newly reconstructed routines.

The original valid-descriptor SPI wrappers `0x6be4` and `0x6c0c` execute before
the lower enable/transfer stubs. This tests their observable path within the
sensor call, rather than substituting the entire HAL wrappers. It does not
reconstruct all HAL argument cases or the peripheral driver.

## Findings established by original instructions

**The response is a big-endian word with its two lowest bits discarded.** The
reader transfers two zero transmit bytes and computes
`((response[0] << 8) | response[1]) >> 2`. All 65,536 response words match this
expression; changing the low two bits leaves the fourteen-bit result unchanged.
No error/status interpretation is performed for those bits in this reader.
This does not identify the physical sensor or establish what those bits mean.

**Only selector value 1 chooses the first mask.** It writes `0x80` to dummy
address `0x60000014` before transfer and to `0x60000018` afterward. Other tested
selector values, including zero, two and signed boundary bit patterns, use
`0x800`. Their physical signal names and polarities remain outside this evidence.
The normalized action order is GPIO write, valid-descriptor assertion, SPI
enable, one counted-loop request, another valid-descriptor assertion, two-byte
transfer, another counted-loop request, and final GPIO write. No measured SPI
rate or delay duration is inferred.

**Enable and transfer return statuses are ignored by the reader.** The result
is unchanged for supplied success, negative and integer-boundary statuses, when
the transfer stub still supplies two complete bytes. This is not an assertion
that a failed or incomplete physical transfer yields usable data. Unwritten
receive bytes and polling/readiness failures remain unmodeled.

**The initial reference is later replaceable by persistent state.** `0x8c80`
copies its sample into the sample, initial-sample and reference halfwords,
sets position 4096, clears relative motion and initial velocity/history fields,
sets direction 3 and clears the armed byte. The subsequent `0x8ae4` restore
replaces all 44 persisted bytes, including the reference, reported position and
armed byte; it separately copies focal length and sets advertised lower bound
4144. Synthetic origin traces demonstrate this dependency without unit data:

| Current raw sample | Synthetic saved reference | Position before restore | Position after restore and reread |
|---:|---:|---:|---:|
| 5000 | 4800 | 4096 | 4146 |
| 100 | 16000 | 4096 | 4216 |
| 16000 | 100 | 4096 | 4216 |
| 8191 | 8192 | 4096 | 8191 |

The last row exercises stock's asymmetric seam behavior, not a sensible
physical calibration. These results reproduce the existing arithmetic under a
newly executed sensor boundary. They provide no universal mechanical offset.
The custom candidate's homed tracker therefore remains a deliberate policy;
loading stock reference bytes into that unrelated coordinate system is not
justified by this research.

**Restore-after-stop ordering is now traced through the original main prefix.**
Eight fixtures execute `0x8b70` until its first invocation of foreground poll
`0x5dd4`. Under explicitly cut board/timer/motor/delay services, each trace
reaches encoder initialization, stop, settings restore and metadata publication
in that order. A generated saved armed value of 1 replaces the stop boundary's
armed value 0 before the first foreground poll. This is software-order evidence,
not a claim that stock physically restarts the motor. The homing gate starts and
ends zero in these fixtures; its later enabling writer/reachability is still
unproved.

## Validation and negative control

The [sanitized result](../../research/stock-1.8/extensions/2026-10-12/sensor-boundary-validation.json)
records **68,648 passing cases/steps**:

| Scope | Count |
|---|---:|
| Every possible two-byte response under selector 1 | 65,536 |
| Selector boundaries, supplied status pairs and seeded unrelated SRAM | 1,024 |
| Filter initializer with full-width arguments and seeded SRAM | 1,024 |
| Encoder/motion initialization with synthetic samples and statuses | 1,024 |
| Eight initialize/sample/restore/sample sequences | 32 steps |
| Original main initialization prefix through first foreground poll | 8 cases |

Each entry/composed step compares all 3,072 modeled persistent SRAM bytes and
the relevant return value and ordered boundary events. Prefix fixtures compare
the complete resulting modeled SRAM and the declared action/checkpoint order.
Void return registers are not claimed equivalent. Stack addresses are normalized
to transfer contents/count; other unmodeled SRAM writes must remain inside the
declared caller/callee stack range.

A negative control changes only the generated host model's byte order. With
response `0x48d3`, the original returns 4660 while the incorrect model returns
13522. The comparison must detect that mismatch. The retained vendor file and
authored sources are never mutated. Compilation passes C11 `-O2`, `-Wall`,
`-Wextra`, `-Werror` and `-pedantic`; the result pins all relevant source and
original-range hashes. No device enumeration, USB report, updater, flash write,
motor operation or physical calibration was performed.

Four separate [input/output guard checks](../../research/stock-1.8/extensions/2026-10-12/input-guard-validation.json)
reject existing output, optimized Python, a wrong-size synthetic input and a
wrong-digest synthetic copy before producing files. The original input remains
unchanged. The guard runner is retained beside the differential validator.

## Honest overall coverage

The [whole-firmware ledger](whole-firmware-reconstruction.md) remains the source
for the larger inventory. All 20,172 application bytes are assigned layout
categories; 235 application and 145 boot instruction-bearing entries are
inventoried. That is byte/code discovery, not semantic completeness.

The established public application model has 38 routine entries and 24,991
finite cases/steps. This separate extension adds three new bounded entries,
bringing the union of those application semantic models to 41 entries. The
case counts overlap existing composed routines and have different definitions;
adding them yields no coverage percentage. Separate boot/USB/NVM models remain
separate and are not integrated into a reset-to-camera replacement.

Still open: real SPI readiness/error handling, timer/IRQ scheduling and races,
ordinary homing-gate reachability, optical-table interpretation/calibration,
camera meaning and request grammar for `0x34`, some boot and upper-image data
semantics, and whole-program reconstruction. There is no buildable reconstructed
factory replacement or claim of factory AF parity. AF 2.6's physical exposure,
loaded-lens focusing, timing and hunting remain subject to camera testing after
a separately scoped upload and byte verification.
