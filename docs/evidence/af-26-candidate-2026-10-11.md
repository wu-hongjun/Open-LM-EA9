# AF 2.6: audited aperture policy and stock opaque query

October 11, 2026, America/New_York. **Prepared offline for the Contax Zeiss
50mm f/1.4; no adapter connection, USB reports, upload or camera qualification.**
This is a separately versioned successor to the held 2.5 candidate, not an
overwrite of its binary or original test evidence.

## Protocol and aperture changes

`0x34` is removed from `lens_aperture_publish` and from the aperture-specific
RX-fixup exception. The original table's fixups now clear reply byte 6 and copy
the consumed request's bytes 6/7 into reply bytes 7/8, preserving every other
response byte. Those are opaque operands; neither matching an AV number nor
sharing a factory memory source with `0x1b` establishes aperture semantics.

Before applying the `0x34` fixups, transport requires both bytes inside the
validated payload: six header bytes, at least two operand bytes and three
trailer bytes. Short payloads produce no reply and cannot copy a checksum into
the operand. Longer frames remain admitted, including the 16-bit length form;
this is a minimum memory bound, not proof of the exact original grammar.
Framing/checksum validation and atomic request-snapshot ownership are retained.

Known aperture fields remain under the fixed policy:

- `0x05` duplicates the declared AV, with zero iris countdown and the iris-rest
  bit set while preserving unrelated bits.
- `0x1b` returns the only declared accepted aperture instead of implying an
  unavailable physical stop-down.
- `0x28` includes the declared value only after consumed `0x08` negotiation;
  a new session clears that optional publication until renegotiated.
- Profile application sets equal electronic range endpoints. Real maximum
  specification remains separate from the camera declaration and unknown iris.
- Per-frame `0x03` requests are recorded without changing the declaration.
  `0x35` is still unsupported/not emitted by this dispatcher; unknown capability
  bits are not relabeled as proven advertisement semantics.

The 50mm profile declares nominal f/1.4 (`0x1100`, descriptor `0x10`). No F--
sentinel or exposure offset is introduced. The app retains **Actual aperture:
Unknown**. Manual stop-down should need no app/profile changes for ordinary use;
saved EXIF remains declared metadata. Camera metering and dial clamp still need
qualification. Equality of `0x05 pl[46]` with the declared maximum is a retained
compatibility hypothesis, not a recovered field meaning or metering correction.

Stock optical packet rows remain byte-preserved. Production initialization does
not install the unused SEL5518Z donor constants, and none of these rows becomes
a measured Contax calibration. Stale source comments about IRQ publication,
request echo and sensed wide-open aperture were corrected.

## AF behavior retained

The factory-derived controller, bounded wrapper, reference, prediction, mapping,
completion and production main sources are byte-identical to 2.5. In particular:
whole corrections within the four-count wire resolution can end without a
drive pulse; a direction-consistent progressing move can terminate on its
bounded deadline and admit a following command; unsafe timeouts, stall,
runaway/wrong-way and I/O faults remain latched. Stop acknowledgement does not
erase those faults. Measured actual position is retained. An actuator completion
event is not optical focus lock.

The eight-target mechanical regression still reproduces the intended fixes:
four counts terminates at zero with no drive, followed by a successful 40-count
move; full travel terminates at a healthy deadline at 5,762, followed by a
successful reversal toward 4,000 ending at 3,997. These are inherited simulation
coefficients, not observations of this owner's mechanism. Loaded braking,
homing/origin and camera timing remain unmeasured.

## Validation

| Check | Result |
| --- | --- |
| Native macOS suites | 50 tests pass; 2.6 admitted, image mismatch rejected, future 2.7 rejected, variant preservation and recovery checks retained |
| Firmware host suite | Pass; 27 wrapper scenarios, 21 hardening scenarios per backend, lifecycle/wait checks and transmitted frames for all eight requested profiles |
| Opaque `0x34` probe | 56 operand/length/sequence cases and two absent/partial-operand cases pass; a later normal frame cannot replace the consumed operand |
| Original-instruction query comparison | 32 full 32-byte replies match, including original sender checksum/framing and stored init sequence; final I/O helpers stubbed |
| Frozen 2.5 negative control | Unsupported override detected; historical 2.5 regression remains reproducible from its immutable original Git inputs |
| Factory AF oracle | 7,323 comparisons pass; altered-gain negative control detected |
| Mechanical regression | Eight targets pass; both former completion failures admit successful following motions |
| Cross-build/package | 20,480 bytes; profile CRC/vectors valid; native/Python images identical; app and CLI built and locally signed |
| Preservation | Frozen 2.0–2.5 templates, historical candidates and original public stock 1.8 recovery bundle unchanged |

The historical `test-refined-candidate.py` no longer silently executes current
source as 2.5. It materializes digest-checked files from commit `7efac6b` using
[the input manifest](../../firmware/candidates/2.5.0/regression-inputs.json).
Its old aperture assertion is explicitly a superseded hypothesis. The current
suite uses `test_stock_query.c` and `test-audited-candidate.py` instead.

The image fits exactly below the profile: initialized flash ends at `0x9f00`,
with zero free bytes before that row. Linker assertions keep writes inside
`0x5000..<0xa000`. Static RAM ends at `0x20000afc`; the reserved 8 KiB stack ends
at `0x20002b00`, inside 16 KiB SRAM. Actual stack high-water is unmeasured.
No logging flash writers or legacy servo are linked. Future features need
code-size reduction within this fixed boundary.

Evidence: [build inputs](af-audited-build-manifest-2026-10-11.json),
[query/motion regressions](af-26-regressions-2026-10-11.json),
[factory oracle](af-26-factory-oracle-2026-10-11.json),
[release validation](af-26-validation-2026-10-11.json), and
[candidate/pins](../../firmware/candidates/2.6.0/README.md).
Private unit backups, calibration, serials and recovery keys remain excluded.

## Separate hardware milestone

The adapter is disconnected. Flashing is explicitly deferred. App 0.9.0/build 12
and CLI explicit AF installation now select 2.6, while normal dropdown changes
preserve the verified installed version. A future upload must save a fresh
verified same-unit backup/journal, finish the transfer, then pass strict
readback after physical reconnect before camera use.

Follow [the staged A7C II procedure](../af-s-test.md): loaded-lens MF
startup/idle/shutdown and exact aperture display first; saved exposure at physical
f/1.4 and f/4 in A, then P/Auto without changing declared metadata; only after
normal lifecycle/metering, one bounded AF-S attempt and then stopped-down AF.
Stop unsuccessful hunting after roughly two seconds; do not repeat a failed
attempt to force a result. An owner-reported failure is sufficient, while a
retained photo enables quantitative/EXIF analysis. No new stock-photo exercise
is required now. Optical accuracy, AF-C/video and factory parity remain open.
