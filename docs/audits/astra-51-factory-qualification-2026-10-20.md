# Astra51 — bounded factory/upstream reference qualification

The concrete software policy defect is the hardening conversion of an upstream
**drive cap** into a prerequisite for forty ticks of driven stillness. Upstream
`references/upstream/weiziqian/E-mount-impl-on-Techart-EA9/src/main.c:256` explicitly
calls drive and settle durations caps; its threshold comment says threshold
crossings fall back to the fixed pulse. Its `motor_home` proceeds to zero duty,
brake and settle when the drive loop expires. Lane03 `apply.py` inserts
`if (!drive_ok) goto failed;` before that transition. AF3.9 retains it.
This is an intentional stronger safety policy with a concrete liveness cost,
not evidence that duty, drive duration or sensor wiring is incorrect.

The new snapshot has anchor280, cutoff300 and no driven40 qualification. The
source-extracted helper probe supplies a synthetic trajectory ending at−2902
at280 and remaining unchanged thereafter: it cannot qualify before300, yet can
remain fixed throughout a subsequent forty-tick released interval. This is a
counterexample to requiring driven40 for every bounded software reference; it
is not reconstructed raw telemetry or proof this mechanism reached infinity.
The probe pins all49 baseline sources and the exact AF3.9 manifest/image, verifies
the upstream reference checksum, and passes Clang ASan/UBSan including tick wrap
and both signed coordinate extremes. Private result:
`artifacts/private/astra51-policy-1/result.json`.

## What the factory instructions establish

The already pinned Astra47 original-instruction receipt supplies the relevant
contract without rerunning its24 cases. Conditional home0x5e00, when its supplied
gate is set, writes CC0/2=0 and CC1/3=800, requests delay300, executes the real
stop0x8e28, requests delay500, samples/reference/samples, persists and clears the
gate. Disagreeing supplied samples still pass. Stop removes PMUX ownership and
sets PA19 high; electrical coast/braking cannot be inferred from inert MMIO.
This is distinct from upstream's zero-compare, mux-attached brake. The stock
startup restores persistent origin after initial sensor/reference setup. Neither
stock path validates the physical infinity stop or licenses restoring readiness
from a saved reference. Its unrelated servo timeout completion is also not a
homing qualification result.

## Qualified bounded adjustment

Lane49's proposed fallback is defensible as an explicitly experimental software
reference policy: preserve early driven40 behavior; preserve duty800 and cap300;
at the cap require observed negative travel greater than6 within the existing
travel envelope, repeated pre-cutoff observation of the retained anchor, and a
fresh forty-tick postdrive interval whose **every observed position** stays
within6 of that same pre-cutoff anchor. Use the existing500 settle bound and
shared poll budget. Reject positive/zero/excessive net travel, insufficient
corroboration, any later anchor escape, cancellation, encoder fault and deadline
crossing. The fallback should release first and remain released while settling.
It avoids changing electrical drive duration or introducing an uncalibrated
minimum twenty-tick driven threshold merely because this one snapshot shows20.

This is weaker driven evidence than forty ticks: two observations could be only
one tick apart. Net negative travel does not prove monotonic travel. Release can
stop a slowly moving carriage within6, and static encoder failure/stiction can
satisfy either old or new stillness checks. Consequently the result is qualified
software readiness, not endstop detection or proof of physical/optical origin.
The new trace alone cannot prove the fallback would pass: it lacks the final
raw sample and the required postdrive observations.

A fresh ordinary settling anchor is insufficient. The probe supplies7 counts
of postdrive drift and then rest; the original resetting stillness helper accepts
it, whereas a fixed pre-cutoff anchor rejects it. Accumulated creep must compare
to that fixed anchor, never just the preceding sample. No reset/retry on escape.

## Cutoff, arithmetic and commit requirements

- GPIO emergency release must precede potentially waiting CC synchronization,
  extra encoder reads and diagnostics at the cap. `motor_drive(0)` and
  `motor_brake()` both attach pins before clearing compares; calling them after
  cutoff can remux stale nonzero duty. Released fallback avoids this hazard.
  Any alternative brake helper must clear all compares while detached and only
  then attach under existing inhibit/cancellation ownership.
- A300 tick cap is a software scheduling bound, not an exact electrical-time
  measurement. A returning pump/read can cross it. Reject over-cap late evidence;
  do not count postdeadline samples as pre-cutoff driven corroboration.
- Keep int64 subtraction or the proven unsigned magnitude after signed ordering.
  Plain signed int32 subtraction and uint16 narrowing break full-domain guards.
  Tracker overflow inhibits but retains the corrupt coordinate, so later checks
  must honor sticky inhibition rather than assume all values are in±65536.
- Unsigned elapsed subtraction handles ordinary uint32 tick rollover. A frozen
  clock needs the unchanged shared poll cap; neither mechanism establishes an
  independent elapsed-time bound when interrupts stop or ticks are lost.
- Bind the chosen zero to the qualified sample. Existing `after` read and
  `abs_encoder_track_reset()` perform additional encoder reads after settling;
  merely checking an earlier settled sample leaves a gap. Reject a final sample
  outside the fixed anchor and avoid an unchecked new sample in reset, or check
  that reset sample explicitly. A reset-from-already-validated-last-raw helper
  avoids an additional unvalidated I/O boundary.
- Keep Stop, shutdown, handshake/session change and sticky sensor/motor faults
  checked before/after pump, after samples and immediately before serialized
  readiness commit. Changing the software reference alone grants no readiness.
  Do not perform peripheral I/O inside the final lock.

No shared production source, old receipt, release, manifest, patch, pin, app
resource or recovery artifact was edited by this lane. No hardware or app was
opened. This audit supports a testable causal fix for the overstrict cap gate;
final integration, compiled acceptance and camera validation remain separate.

## AF4.0 integration review follow-up

A downstream stale-duty hazard must be closed before accepting released fallback:
`servo_move_from` attaches motor pins before its first position sample or newly
computed duty. GPIO release preserves old compare values, including home duty800.
Thus success followed by ordinary servo entry can remux stale home drive unless
all compares are cleared while detached. Release-only settling alone does not
close this path. The required helper must detach first, clear all four compares
using existing bounded synchronization, and leave the pins detached; final
readiness/cancellation guards still apply. This finding was sent to lane49 and
the integrator before freezing AF4.0.

`inspect_compiled.py` prepares a pinned AF4.0.0 evidence inventory for review.
Its output is explicitly **not acceptance**. Exact callback-site, stack, NVM and
new register-sequence review must follow against the final frozen build.


## Final AF4.0 compiled acceptance

Frozen `artifacts/private/reference40d` passes the exact-image compiled audit.
Image SHA-256 is
`06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae`;
manifest SHA-256 is
`8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`.
Code/data end38956 leaves980 bytes before diagnostics, static RAM3040 and
reserved stack8192 remain unchanged. Only encoder and motor receive additional
`-Os`; all other per-unit/global flags equal AF3.9. All49 final source pins
match and exact lane49 reapplication plus version0x40 reproduces the sources.
AF4.0 uses loader `[4,0,0]`, not an ambiguous3.10/BCD combination.

The unchanged pinned graph analyzer, adapted only for RAM3040, covers153 emitted
functions,536 calls and12 indirect sites with no unresolved edges or recursive
components. Compiler static frame records are bound to the manifest. The maximum
conditional all-vector stack bound is **1588 bytes**:
foreground1172 + EIC168 + UART32 + six36-byte exception charges.
This is56 bytes above AF3.9, principally main's additional homing state, not a
measured high-water mark. The same ARMv6-M/control-flow/boot-entry assumptions
and unmeasured inherited interrupt-state limitations from AF3.9 remain.

`motor_home_release` calls real GPIO release at0x6ca6, then writes zero to the
TCC0 compares at0x6caa/0x6cb0/0x6cb6/0x6cbc with bounded sync calls after each.
Its0x6cc4 literal is the actual TCC0 base0x42002000. There is no attach call.
The real release body clears all four PMUXEN bits, clears their direction bits
and writes PA19 high before returning, with no peripheral wait. This closes
stale-duty exposure on eventual servo attachment without assigning electrical
coast/brake behavior to those register writes.

Main calls the helper at0x829c after capturing elapsed time; it rejects anything
other than the exact300 cutoff and checks retained-anchor corroboration and
full-width signed travel. Released settle checks fixed-anchor displacement.
The formerly unchecked after-sample now has a full-width±6 check at0x84b6–0x84c8
before cancellation0x84ca and final reset0x84d6. The reset routine calls track
exactly once, checks sticky inhibition and full-width tolerance, then zeros
`g_track` at0x6ed0 using the already-updated last-raw value. It does not call raw
again. Final lock0x84de, cancellation0x84e4 and readiness stores0x8540/0x8546
preserve serialization without locked sensor I/O. Exact reviewed function-body
hashes bind every branch, arithmetic operation and MMIO literal in these paths.

The failed-home record follows motor inhibition0x8562; its aligned writes stay
inside bytes112–143 and the0x40 tag store0x859c is last. Failure metadata does
not introduce flash calls. The early-success brake path remains distinct.

Compiled STOCK callback pointers and actual cfg offsets48/52/56, main callback
literal registrations, EIC callback storage, all45 vector words, IRQ setup,
handoff suffix, libc init arrays and zero weak clone callbacks pass. New libc
indirect PCs are0x9470/0x947a; its preinit is empty and init holds only
`frame_dummy`. All library stack operations match the prior reviewed sequence.
Shutdown, fail-stop, UART disable and delay operations retain their prior
semantics after named RAM-literal relocation. Diagnostic NVM callers remain
exactly the prior flush/terminal/append/write/read gates; ISR, trace and motion
completion roots cannot reach NVM or fail-stop. Release ADC remains discarded.

The new [runner](../../firmware/upstream-hardening/next40/compiled_audit.py),
[policy](../../firmware/upstream-hardening/next40/compiled-policy.json) and
[reproduction contract](../../firmware/upstream-hardening/next40/stack-reproduction.json)
are separately pinned. Runner SHA-256:
`4724400d2f19eceecb7e4378671630f69e895d0122e3a8227a68cc73d35f24f1`;
policy SHA-256:
`024e2ae89c2aeb33e1918b6e91a3e86600b9e1bb4db3ec7fefbbec0562b3b8e0`.
Private acceptance is `artifacts/private/astra51-compiled40-final.json`.
Internal unknown-indirect, unknown-library, recursive-callback and image-pin
mutants fail. External graph-policy modification, optimized Python and a mutated
main instruction also fail without acceptance output; private controls are
`artifacts/private/astra51-compiled40-controls1/results.json`.

Repeat builds may rebind only ELF/map container hashes, after raw/image/manifest
pins and all normalized objdump disassembly, symbols and program headers match.
Only the printed ELF pathname is normalized. No instruction/address/section
normalization permits altered code. This acceptance establishes the stated
offline conditional software properties, not physical motor timing, true
infinity origin, camera shutter acceptance or permission to flash.
