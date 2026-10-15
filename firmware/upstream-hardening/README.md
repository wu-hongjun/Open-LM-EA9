# Upstream C hardening workbench

This workbench contains modular changes under offline review. **It is not a
released firmware candidate and does not change the uploaded 3.2 image.**
Current work and the eight-hour continuation ledger are in
[the hardening record](../../docs/firmware-hardening-2026-10-15.md).

`src/em_frame.c/.h` validates the complete E-mount frame before dispatch:
start, little-endian 16-bit length, minimum nine bytes, available bytes,
terminator and additive checksum. A successful view excludes the CS-window
tail; a failed view is cleared. Nonzero tails are allowed. The module has no
device API, heap, global state, class interpretation or motor instruction.
The caller must supply a stable receive window. This is **not** an interrupt
ownership or message-semantic validator.

The runner first pins every materialized 3.2 C/header input to its build
manifest and checks the committed image. It then builds a temporary `emount.c`
overlay that calls this gate before any dispatch and uses the validated length
for known field guards and request snapshots. It retains the original window
length for diagnostics. Frozen 3.2 and the overlay run the same probes with
ASan/UBSan. Deliberately bad/truncated traffic must not arm handshake readiness
or publish a Move; short padded messages must not read footer/tail operands.
Valid init/Move and nonzero-padding controls must still work. The original
source tree, candidates and app resources are never rewritten by this runner.

Reproduce from the repo root, using a new output path under an existing parent:

```sh
# Only if the ignored, pinned 3.2 build inputs are absent:
python3 scripts/build-upstream-diagnostic.py
python3 scripts/test-upstream-frame-admission.py --output /new/frame-admission-check
```

The corpus fixture is regenerated from
`references/analysis/entropy512-frames.jsonl`, never from private camera logs.
The 3,456 valid windows include both directions. Corpus replay validates the
frame module; fifteen separate fixtures execute the actual C dispatcher under
scripted CS and immediate TX. Neither proves A7C II compatibility, asynchronous
peripheral timing or optical performance. A future release needs a separate
version, complete build/host regression gates and owner-coordinated hardware
acceptance. Preserve 3.2 for the already requested diagnostic cycle.
