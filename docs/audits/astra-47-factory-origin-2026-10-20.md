# Astra47 — factory origin, homing prerequisites and optional size reduction

The factory/upstream comparison establishes no production homing remedy. In
particular, restoring a factory reference does not establish a physical origin,
and the conditional factory homing block is not the upstream stillness
algorithm. Sensor setup/hold instructions differ, but no supplied timing or
validity evidence establishes that the difference caused the AF3.8 failure.
No motor polarity, duty, gains, bounds, coordinates, reference gate or sensor
initialization was changed by this lane.

## Baseline and actual observation

The tests bind the published AF3.8 manifest SHA-256
`be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0`, all
49 reconstructed source hashes, and its recorded image SHA-256
`8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`.
The private baseline is `artifacts/private/readiness38-repeat`.

The [camera evidence](../evidence/upstream-38-camera-failure-2026-10-20.md)
records hunting, one perceived photo, reset and no further photos, with normal
shutdown and AUTO exposure. Focus mode and whether a file was saved remain
unknown. The retained fault17 selects the drive-phase deadline failure; the
empty servo collector does not exclude homing motion. It provides no encoder
trajectory, fault occurrence time, physical end-stop position or measured pump
duration. A pump returning after the deadline can select fault17. This lane
makes no claim that a missing shutdown footer establishes a delay hang or that
local raw readiness return establishes camera acceptance.

## Original-instruction evidence

[Runner and results](../../firmware/upstream-hardening/followup/47-factory-origin/README.md)
pin the stock application (`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`),
REA oracle/config and individual executed instruction ranges. Unicorn2.1.4 runs
24 bounded cases: eight sensor, four delay-loop, eight conditional home and
four initialization/restore prefixes. Six explicit incorrect interpretations
are rejected. GPIO/TCC registers are inert synthetic memory; supplied SPI bytes
and status, delay service and persistence boundaries are stubbed. These are
original-instruction facts within those boundaries:

- Reader0x89a4 asserts CS (selector1 PA7, otherwise PA11), calls SPI enable,
  executes busy-loop0x60cc with argument1, transfers two zero bytes, executes
  that loop again, then releases CS. The result is the big-endian receive word
  shifted right two. The actual loop executes `5 + 38*n` instructions, so its
  two argument1 invocations execute86 instructions. These are instruction
  counts, not measured microseconds. Supplied negative HAL status does not
  alter this path's returned sample.
- Conditional home0x5e00 is inert with the supplied gate byte0x20000530 clear.
  With the gate set it executes actual pair/compare setters: CC0=0, CC1=800,
  CC2=0, CC3=800; records delay arguments300 and500 around the real stop path;
  reads two samples; captures the first reference and clears the gate. It does
  so even when the two supplied samples disagree. There is no equivalent
  upstream six-count/forty-tick stillness decision in this block.
- The real stop0x8e28 writes the GPIO release convention for all four pins.
  No electrical brake/coast behavior is inferred from synthetic registers.
- Main0x8b70's tested prefix reaches sensor initialization0x8c80,
  stop0x8e28, restore0x8ae4, metadata0x8a8c and first foreground0x5dd4 in that
  order. Synthetic saved reference and armed fields overwrite the initialized
  values. The gate remains clear in this supplied prefix. This does not prove
  that no enabling writer exists anywhere in the whole program or every
  shipped image.

## Current caller and timing comparison

The pinned upstream sensor uses SERCOM0 mode/baud configuration, CS1 and the same
14-bit byte assembly. It enables SPI once in initialization and has no explicit
factory setup/hold busy loops in `abs_encoder_raw`. Clock, encoder and motor
initialization precede `em_init`; the initial reference/track reset precedes the
handshake-gated home attempt. This review found no proved initialization order
or configuration contradiction sufficient to explain fault17. Blindly copying
the factory busy loops lacks a minimum timing contract and a failing-control
reproduction. It is not proposed.

Upstream's home drives−800 with a300-tick cap, minimum40 and40-tick stillness
qualification at threshold6; the subsequent settle cap is500 with minimum20.
It checks cancellation before/after pump and preserves inhibition on failure.
Comments equating stillness with end-stop arrival or claiming all factory
homing is unreachable are stronger than this lane's evidence. Neither saved
factory reference nor the conditional block grants permission to set `g_homed`.
The next useful discriminator is the root lane45 bounded homing snapshot:
phase duration, qualifying stillness progress and work/pump consumption at
failure, while keeping every existing guard. It still cannot by itself prove
motor current, sensor electrical validity or camera shutter acceptance.

## Independent ADC consumer closure for lane48

A complete source-reference search finds ADC register use only in `vdd.c`;
`main.c` is the only API consumer. Supply idle/load results feed only legacy
MOTR words5/6 under `#ifndef EA9_NO_LOG`. In the release build, reset, sample,
result and initialization remain called even though those consumers are absent.
There is no servo, protocol, encoder, motor inhibition or current-limit consumer.
The weak ADC IRQ handler is unused; this driver enables no ADC IRQ.

`vdd_init` ORs the ADC APBC clock mask, routes GCLK0 to the ADC channel without
changing the shared generator, reads calibration fuses, configures internal1V /
scaledIOVCC ADC input, enables it, and discards eight conversions. It changes no
GPIO or BOD33 setting. Sample performs one blocking conversion and updates two
private min/max values; result/reset only read/reset those values. `vdd.c`
explicitly distinguishes logic IOVCC from the separate motor supply. Omitting
these four calls when legacy logging is disabled preserves the used data
consumers and removes the ADC wait dependency. Guard the adjacent ST_ADC stage
note too, so it does not imply initialization occurred. Full legacy logging
should retain the original driver and calls unchanged.

This supports the root lane48 optimization and software-liveness investigation;
it does not prove ADC stalled or caused physical fault17. Real pump cadence
will change. Host fixtures whose fake clock increments in the VDD stub must
move that synthetic boundary explicitly and rerun the same scenarios, rather
than claiming cadence parity from unchanged fixture outcomes.

## Separate arithmetic optimization, optional

`apply_size.py` replaces int64 signed subtraction plus two-sided threshold
comparison with unsigned magnitude selected by signed coordinate order. For
`now >= at`, the mathematical difference is in[0,UINT32_MAX], so unsigned
subtraction represents it exactly; the reverse branch represents its negation's
magnitude. Thus `magnitude > 6` equals the original int64 predicate for **every
int32 pair**, including retained corrupted coordinates. Timestamp updates and
unsigned clock subtraction remain unchanged.

An earlier int32 signed-subtraction experiment saved68 bytes but depended on
normal reachable tracker values within±65536 (difference±131072). The real
tracker inhibits on corrupted retained coordinates without sanitizing them;
that experiment therefore reduced the old arbitrary-coordinate arithmetic
guarantee. It was rejected. The retained applicator uses the full-domain version.

The source-extracted differential fixture runs6,898,454 comparisons: every
reachable anchor against extremes/threshold-adjacent samples and five elapsed
clock cases, plus signed extremes and deterministic full-int32 inputs. It also
executes actual production tracker reset/update with both-sign overflow,
capacity boundaries and corrupted retained values, comparing inhibition/fault
behavior. Clang ASan/UBSan pass; uint16 truncation and inclusive-threshold
mutants both fail. The algebra, rather than finite random samples, supplies the
full-domain guarantee.

Recompiling only main with the AF3.8 manifest flags and relinking the baseline
objects produces code/data end39552 versus39600: **48 bytes saved**, margin384
versus336, static RAM unchanged3044. This is a size experiment, not a published
candidate or a homing fix. Root may omit it if lane48 provides sufficient space.
No hardware operations, camera acceptance, physical timing, or new stack bound
are established by these runs. Original instructions remain subject to the
explicit fixture boundaries above.

## Final disposition

Root accepts the independently reviewed release-only ADC dependency removal
with lanes45/46 observation changes for AF3.9. The optional arithmetic overlay
is excluded. [Final compiled acceptance](astra-af39-compiled-acceptance-2026-10-20.md)
checks both fresh identical images, cutoff-before-snapshot stores, discarded ADC
code, unchanged flash-write caller gates and the conditional1532-byte stack
bound. The [integrated evidence](../evidence/upstream-39-homing-2026-10-20.md)
records the prepared, unflashed candidate and unresolved physical/camera limits.
