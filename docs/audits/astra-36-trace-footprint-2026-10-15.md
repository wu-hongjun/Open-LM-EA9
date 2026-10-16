# Astra 36 — capture trace footprint

October 15, 2026. This lane provides a diagnostics-only source rewrite under
`firmware/upstream-hardening/followup/36-trace-footprint/`. It changes only the
new capture observation helper and four observation callsites in `emount.c`.
The applicator requires the exact reviewed lane34 emount hash and a private
staging directory. It never writes the frozen 3.6 base or publishes an image.

## Change and equivalence boundary

`em_trace` sends three 32-bit scalars to lane35's `st_record`: milliseconds,
packed identity, and the original full session token. On the format's asserted
little-endian target, the packed identity has kind in byte 0, opcode in byte 1,
flags in byte 2 and sequence in byte 3. These are exactly the four former
`st_note` byte arguments. A 16-bit identity contributes its high byte to bits
8–15 and its low byte to bits 24–31; all four fields occupy disjoint ranges.
The session formerly split into two 16-bit arguments remains a full 32-bit
value. No arithmetic changes the milliseconds or session value.

A shared `em_trace_owner` constructs the existing identity and ORs the existing
ownership flags for OFFER, TAKE and the two COMPLETE callsites. The same input
values and source reads remain. The TX START/RETURN path keeps its original
saved identity, flags and session; it does not reread current ownership at
RETURN. This refactoring adds no locking or peripheral access. Diagnostic
sampling instruction order and execution time are not claimed identical under
arbitrary asynchronous IRQ timing.

The 144-byte motion record, 32 focused records, filtering, CRC, terminal footer
schema, flash range and 256-byte minimum margin are unchanged. Control branches,
frame construction, timeouts, guards, motor parameters and control-unit compiler
flags are unchanged by this lane. The first-window helper is untouched.

## Verification

`run.py --source artifacts/private/targeted37b --output <new-private-dir>`
accepts either the original lane34 source or an already compacted final source.
For a compacted source, it reconstructs the exact lane34 observation source in
private scratch and requires that this applicator reproduce the final candidate
emount hash exactly. It compiles the production emount, owner, frame and shutdown
units with Clang ASan and UBSan and the lane34 synthetic harness.

Ten cases pass: ordinary request, raw capture, session IRQ during TX, shutdown
IRQ during TX, occupied pending slot, high session token, failed TX, shutdown,
completion queue saturation and status phase. Before/after runs compare the
complete synthetic transmitted bytes and CS assertion records, every collected
trace field including milliseconds, and completion records. The harness also
checks its existing protocol/control assertions and side-effect digest. A
sequence-packing mutation and a live-session-at-RETURN mutation both fail the
expected observation assertion. `results.json` pins inputs and records all
case results.

The final source includes lane37's packet initializer. Since this host harness
does not execute ARM reset, both variants call the actual production initializer
before `em_init`; the runner verifies its single call exists in production reset.
The first attempted final-source harness omitted that reset obligation and failed
its ordinary-frame assertion; adding the explicit host reset setup made the full
suite pass. This does not validate ARM reset execution, which belongs to lane37.

The observation collector checks the calling convention and retained argument
values; it substitutes the diagnostic backend. Actual ring/NVM behavior and
retention tests belong to lane35/root. These tests establish neither electrical
behavior nor physical camera, motor or interrupt timing equivalence.

## Full-image measurement

`measure.py` recompiles every production unit with the 3.6 manifest's unchanged
flags, adding only the already agreed `-Os` for the new motion diagnostic unit.
It links the complete image and measures loaded code plus initialized data as
`_etext + _erelocate - _srelocate`, not object text or linker text alone.

Against `artifacts/private/targeted37b`, the comparison is:

| Capture observation form | Loaded end | Margin before 0x9c00 | 256-byte floor |
| --- | ---: | ---: | --- |
| Original lane34 construction | 0x9b0c | 244 bytes | fails |
| Compact lane36 construction | 0x9ab8 | 328 bytes | passes |

This is an 84-byte full-image reduction. Part of the saving comes from removing
the final production reference to the seven-argument `st_note` bridge, allowing
section garbage collection to discard it. `measurement.json` records all source
hashes, flags, unit sizes, static compiler stack reports and symbol presence.
The fit above includes root/lane37's separate packet initializer work; lane36
alone did not make the earlier composition fit. Stack high-water use is not
measured. Root owns final source-bound independent review, complete regressions,
release acceptance and publication.

No hardware enumeration, device open, HID, motor command, updater/application
launch, canonical Application Support access, image overwrite, flash or commit
was performed by this lane. The result is diagnostic and camera-unqualified.
