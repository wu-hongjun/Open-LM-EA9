# Upstream C hardening workbench

This workbench now builds the separately frozen [3.3 offline candidate](../candidates/3.3.0/README.md).
Eleven Astra lanes audited and root integrated the composition. It is **not
installed or camera-qualified** and does not change the pending uploaded 3.2.
[Unified evidence](../../docs/evidence/upstream-33-hardening-2026-10-15.md),
[campaign](../../docs/audits/astra-hardening-campaign-2026-10-15.md) and
[eight-hour ledger](../../docs/firmware-hardening-2026-10-15.md) track scope and
acceptance. Published images and their pins remain immutable.

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


## Complete 3.3 composition

`accepted-lanes.json` pins the source/test/applicator inputs. The builder applies
frame admission and explicit transmit success, then lanes 02/01/03/05/06/07/08/10/09.
Research-only04 supplies original-instruction contracts;11 independently reviews
the Mac host. Lane06 owns the motor overlay. New pure ownership/shutdown/frame
modules remain separate C units; homing/transport/driver changes apply to staged
upstream sources. The complete patch includes added modules.

Use the pinned dependencies and materialized 3.2 build described by the
[diagnostic workbench](../upstream-diagnostic/README.md). Choose fresh paths under
existing writable parents:

```sh
python3 scripts/build-upstream-hardened.py --output firmware/upstream-hardening/build/reproduce-33
python3 scripts/test-upstream-hardened.py --build firmware/upstream-hardening/build/reproduce-33 --output artifacts/private/reproduce-33-tests
python3 firmware/upstream-hardening/lanes/09-release/run.py --lane10 --output artifacts/private/reproduce-33-size
python3 firmware/upstream-hardening/lanes/09-release/test.py --build artifacts/private/reproduce-33-size
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

The builder requires at least 256 bytes before diagnostics, validates code plus
initialized data and RAM boundaries, records per-unit optimization/stack estimates,
pads only within the 20 KiB application and refuses an image differing from frozen 3.3.
It never publishes, packages, opens a device or installs firmware. Two fresh root
builds produce identical image/manifest/patch. Test scripts operate only on local
source, simulated peripherals, published bytes and synthetic dumps. Individual
lane reports provide their negative controls and complete finite test commands.

`test-upstream-hardened.py` binds exact staged source/image to the published
candidate and bundled resource, then executes final commit/capture/diagnostic
probes, the compiled ARM page writer and actual published 3.2/3.3 decoder pins.
The REA virtual environment supplies Unicorn. This is separate from strict
native installation verification; mutable diagnostic tails never gain an upload
verification exception. Mac preparation uses a new explicit 3.3 command; old CLI
meanings are preserved. A future executable change needs another version/digest.

The release removes unused legacy telemetry and some trace-only sensor reads.
That changes incidental cadence, so exact host outputs are not physical timing
proof. The original C controller remains; factory reconstruction and A7C II
capture/exposure/focus behavior remain unqualified. Follow the
[separately coordinated test procedure](../../docs/upstream-hardening-test.md).
