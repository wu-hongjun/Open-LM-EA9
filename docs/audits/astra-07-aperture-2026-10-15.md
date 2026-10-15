# Astra lane 07 — aperture negotiation and operand boundaries

October 15, 2026. Offline proposal for the upstream C 3.3 composition; no device
access, enumeration, USB reports, flashing, motor operation, or Application
Support changes. Frozen 3.2 remains unchanged, SHA-256
`e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.

## Findings and disposition

**Proposed: commit optional aperture metadata from the consumed ordinary request.**
Frozen `emount.c` changes `em_m08_aperture_on` and rewrites live packet buffers
inside the receive callback, before lane 01 accepts or rejects that request.
Consequently an overflow-rejected `0x08`, or one owned by the raw capture echo
path, can enable `0x28`'s optional AV. A subsequent ordinary session opener also
leaves the old capability enabled. These are observed production-path defects,
not inferred camera exposure outcomes.

The overlay removes those two receive-side assignments. The ordinary dispatcher
commits bit 7 of consumed `0x08` payload byte 1, inverted as the archived upstream
research specifies; consumed `0x01` resets the optional field to zero. Raw capture
echoes remain unchanged and do not negotiate metadata. Commit occurs before the
ordinary reply attempt; failed transmission remains owned by lane 01 for retry,
so no subsequent ordinary `0x28` bypasses it. Receive diagnostics still count and
record observed requests independently of whether they are accepted for service.

**Proposed: reject missing two-byte operands for `0x08`, `0x1b`, and `0x34`.**
Transport admission validates the enclosing frame but does not establish each
handler's payload. Complete 9/10-byte frames have zero/one payload bytes; the
old `0x34` fixups copy footer bytes into the response word, and all three
handlers emit ordinary replies to these incomplete inputs. The staged guard
requires at least 11 declared bytes before the relevant ordinary handler runs.
Window padding cannot satisfy it. This is the minimum necessary for the two
bytes these handlers consume, **not a complete legal request grammar**, and
larger requests remain accepted. `0x34` remains an opaque word echo; the fixed
aperture override applies only to `0x1b`.

**Validated unchanged: nominal Contax 50 mm f/1.4 declaration.** Actual transmitted
`0x05` current words are `0x1100`; descriptors at payload 44, 46, 51, 52 are
`0x10`; the status does not claim iris transit. Both `0x1b` words retain `0x1100`
under a conflicting f/8 request, and normal `0x03` only records requested AV.
Both focal pairs in `0x05` and `0x28` remain 500 (50 mm), lens ID remains 234,
and `0x28` AV is `0x1100` only after the negotiated enabling choice, otherwise
zero. No `0x35` ordinary reply is emitted and advertised bit 52 is clear.

**Deferred: physical metering, dial clamp, stopped-down AF, optical calibration.**
No fixture measures physical aperture, and no firmware field is changed to a
hypothetical F-- sentinel. No exposure compensation or new optical rescaling is
introduced. Fixed nominal f/1.4 is a compatibility declaration; the actual iris
is unknown and set on the lens ring. Seamless A/P/Auto exposure on the A7C II
remains a hardware acceptance question from the prior aperture audit.

## Provenance correction

The October 11 aperture audit described AF 2.5, whose donor rows were inactive.
That statement does not describe upstream C 3.2: its initialization actively
installs optical rows. However, its pupil-size row is **not the unchanged f/1.8
donor** suggested by stale header prose. `scripts/build-upstream-baseline.py`
rescales `d1 d0 d5 e8 e9 ef` by the encoded f-number ratio to
`d2 5a c8 e1 e2 ea`; the frozen header contains the latter. The baseline evidence
already discloses inherited, unmeasured curves. This lane preserves those bytes
and corrects the aperture and pupil-row comments in staged headers. Numerical
consistency is not Contax optical calibration or a physical aperture measurement.

Original REA reconstruction and its recorded original-instruction validation
support stock boot `0x18` descriptor -> f/2 current words and `0x34` request word
at SRAM `0x69a` -> reply word at `0x30f`, with reply byte `0x30e` zero. Neither
proves the semantic type of `0x34`, or that its separate 850 pair is aperture.
The archived `msg_0x34.md` still has stale focus-position and payload-length
wording; instruction dependencies and the actual 32-byte packet table take
precedence. This lane reviewed the existing original-instruction evidence; it
did not independently re-execute the stock binary. Its exhaustive `0x34` test
covers all 65,536 input words through the C production dispatcher.

## Reproduction and measured cost

Run from the repository root, using a fresh output directory:

```sh
python3 firmware/upstream-hardening/lanes/07-aperture/run.py --output artifacts/private/astra-07-aperture-recheck
```

The harness verifies every manifest-bound frozen source hash, copies the inputs,
and compiles the actual `emount.c`, packet table, startup trace, and applicable
modules against the existing hardware shim with Clang ASan/UBSan and warnings as
errors. It compares frozen 3.2, frame → TX → 02 → 01 → 05, and that composition
plus 07. Lane 03 modifies homing/main rather than these dispatcher paths; the
root remains responsible for the full all-lane linked build and regression.

All 18 scenario invocations pass with 07. Each control source fails the expected
16 defect scenarios and passes the two invariant scenarios. These include every
9/10-byte operand guard with zero/32-byte padded receive windows, deferred
capability commit, overflow rejection, session reset, raw capture negotiation
isolation, fixed metadata, and all 65,536 opaque words. Transmitted lengths,
terminators, and checksums are checked. No sanitizer diagnostics occurred.

Final private result is `artifacts/private/astra-07-aperture-final/result.json`;
reviewable result and source hashes are in the lane directory. An ARM Cortex-M0+
`-O2` object comparison (same frame/TX/02/01/05 staging) measured `.text` plus
read-only data reported by GNU size as 6445 -> 6529 bytes, **+84 bytes**, with
unchanged data (3) and BSS (1600). This is an object measurement, not linked image
size or proof of fit. The root reported an existing composition ROM overflow;
07 must not bypass that release gate.

The overlay is `firmware/upstream-hardening/lanes/07-aperture/apply.py` and must
run after lane 01 ownership. It adds no new C compilation unit. No Git commit,
push, release mutation, or publication was performed by this lane.
