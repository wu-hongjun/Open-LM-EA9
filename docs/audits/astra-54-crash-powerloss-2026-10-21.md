# Astra54 — independent offline crash-persistence acceptance

The lane52 retained-checkpoint core passes synthetic interruption and corruption
checks against actual C, with six deliberately faulty variants rejected. This
is an observability test, not a diagnosis or repair of the battery-required 4.0
camera crash. No device enumeration, opening, reports, flashing, motors,
app/updater launch or canonical host-state access occurred.

The runner verifies frozen4.0 image SHA256
`06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae`, manifest SHA256
`8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`, and all manifest
source pins before and after execution. It applies lane52 only to a fresh private
copy, or verifies a supplied candidate. Published artifacts are never edited.

Actual `startup_trace.c` is included in the harness so its private state can be
observed without adding production test hooks. The production ST_HOST boundary omits the ELF retained-section attribute for
host compilation; target builds retain the linker placement. Five interruption
hooks follow the real checkpoint's invalidate/copy/time/checksum/publish boundaries.
The hooks are outside production source; checksum and append behavior remain the
actual C implementation. Host flash is synthetic, with a single controllable
byte-prefix write. ASan/UBSan and finite process deadlines cover every run.

Checks cover all256 reset-register values;448 single-bit corruptions spanning the
56-byte retained marker, checksum and summary;65 power-cut prefixes from zero to
64 bytes;16 occupied-tail frontiers including full storage; five cold/reserved/
external reset causes followed by watchdog reset; and failed flash reads. All
checkpoint interruption boundaries before final publication reject recovery.
The completed checkpoint survives the synthetic warm-reset operation. Baseline
payload is zero and consumes stale RAM; repeat reset cannot replay that checkpoint.
Torn/failed appends do not retry in the same boot. A new boot advances past the
highest valid occupied slot, never fills earlier holes, and never erases. Invalid
CRC in any occupied page instead latches a storage-damage fail-stop.

An independent Python/zlib oracle checks all65 emitted prefixes and512 individual
page-bit corruptions. This establishes envelope checksum detection for the supplied
fault schedules, not arbitrary hardware write atomicity. The six negative controls
remove retained checksum validation, loosen exact reset eligibility to a bitmask,
omit consumed-marker clearing, omit initial checkpoint invalidation, allow
append retry, and disable the persistent latch. Every control fails an acceptance assertion. These are actual
modified C executions, not predicates that merely mirror implementation text.

Private frozen-core receipt: `artifacts/private/astra54-powerloss-freeze/results.json`.
The original intermediate receipts remain private and unchanged.

Additional checks verify256 later reset causes cannot bypass a valid persisted
crash latch, and512 single-bit corruptions of a flash record all stop later boots
as storage damage. A zero-byte failed write leaves no occupied evidence and can
permit a later cold boot; interrupted nonempty writes latch storage damage.
An actual baseline followed by an ordinary summary uses separate append cohorts
(one and two), preserving the legacy summary origin rule. The old4.0 decoder
rejects the new type5 record.
Reproduce using a fresh private output:

```sh
python3 firmware/upstream-hardening/followup/54-crash-powerloss/run.py \
  --output artifacts/private/astra54-powerloss-new
```

These tests do not yet establish emitted ARM/bootloader retention, physical WDT
clock/reset timing, integration feed policy, motor fail-stop, or decoder semantic
acceptance. Those remain separate integration obligations. No stack or pointer
captured from the faulting context is dereferenced by this core. A checkpoint is
an earlier foreground summary, not an exact crash-time snapshot or session ID.
The boot cohort identifies the append frontier, not the checkpoint's old session.
Battery removal before reset and boot append can still lose the volatile record;
a partial boot write may leave a torn page. Durable baseline presence proves only
that boot reached the append. Neither baseline nor recovered checkpoint proves
capture success, optical focus, shutdown completion or a hardware root cause.

## Final candidate and acceptance integration

The final4.1 image is
`fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641`, manifest
`557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b`.
The final source passes this lane at `artifacts/private/astra54-foreign-final`.
Nine actual-C fixtures additionally distinguish CRC-valid foreign/malformed
headers from CRC-invalid occupied storage: the former consume space and may be
followed by a normal baseline; the latter latch fail-stop. The decoder checks
this exact distinction rather than treating every structurally invalid page as
a hardware storage latch.

The681-check new decoder suite uses the C-emitted recovered and baseline-plus-
ordinary records. It tests decoded fields,512 individual page-bit corruptions,
64 incomplete prefixes, CRC-repaired impossible headers and payload fields,
old-version rejection, reserved fields, cross-cohort assembly, a full append
frontier, later records after a crash/CRC-storage barrier, and all nine foreign
header fixtures. Both the wrapper and underlying decoder source hashes are
recorded. Zero values in flush-only summary members are not measurements of no
traffic or no errors; only the live-summary fields are updated by the foreground
checkpoint path.

The new41 acceptance master retains the historical contract and decoder suites.
Private adapters admit the new version, supply weak `st_health` only at the
historical host hardware boundary, and define ST_HOST for both clang and cc.
The35 writer guard compares the entire original flash prefix unchanged, followed
by the exact new motor include and52 watchdog module. The isolated41 registry
fixture adds the new decoder module to its copied dependencies. No production
source checks or historical test assertions were removed.

All39 non-compiled groups passed across
`astra54-acceptance41-partial3` (first21 groups) and
`astra54-acceptance41-tail3` (remaining18). The latter is an explicitly partial
private debug runner whose receipt names the earlier groups as not rerun; it is
not final acceptance. Final canonical execution is owned by root. The partial
receipts verify all49 source files,151 preserved artifacts and unchanged older
registry entries. Target instruction/stack/linker acceptance remains lane53's
independent responsibility.
