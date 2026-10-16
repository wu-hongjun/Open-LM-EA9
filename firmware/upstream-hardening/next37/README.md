# AF 3.7 offline tracing composition

This builds [3.7](../../candidates/3.7.0/README.md) from the exact frozen 3.6
materialization at `artifacts/private/handoff36-repeat`. If absent, follow the
[3.6 prerequisites](../next36/README.md) and reproduce it there first. The pinned
toolchain, compiler flags and linker memory regions remain the same; the new
diagnostic-only `motion_trace` unit uses `-Os`.

Choose fresh private output directories under existing parents:

```sh
python3 scripts/build-upstream-targeted.py --output artifacts/private/recheck37
python3 scripts/test-upstream-targeted.py --build artifacts/private/recheck37 --output artifacts/private/recheck37-tests
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

The builder checks every frozen base source and manifest, the accepted
applicator/source pins, total loaded code **plus initialized data**, the 256-byte
margin, vectors, RAM/stack and the erased 1 KiB log tail. Published 3.7 bytes must
reproduce exactly. `accepted-lanes.json` binds production inputs; `test-inputs.json`
separately binds regression templates and explicit host-only ABI adapters.

`replay.py` generates private runners while preserving the original fixture
locations, base controls and control/wire assertions. Retained control harnesses
use weak observation-only mocks and generic API dispatch; dedicated motion,
capture and storage checks execute the real new modules. Host C test mains skip
Reset_Handler, so the adapter explicitly invokes the production packet initializer
only when its module is linked. Actual compiled Reset_Handler initialization and
ordering are independently executed by lane37; a host constructor is not IRQ proof.

Documented rebindings include the new version/pins, the v3 test-only fault
accessor and log plan, the moved filter mutant, and the real queue hook advancing
ATTEMPT to QUEUED. They do not redefine control success, remove failing controls,
or change frozen releases. Every final source hash is checked before/after tests.

The compiled audit binds actual callbacks, library bodies, vectors, PRIMASK,
ordering and finite stack paths. `stack-reproduction.json` permits only ELF/map
container pins to change after exact raw/image/manifest and normalized compiled
instruction/symbol/program-header equality. Conditional boot/IRQ assumptions,
physical stack/timing limits and camera qualification remain explicit.

The macOS app must remain closed during offline work: normal refresh enumerates
hardware. `prepare-trace-upstream` with an isolated private state directory only
prepares the pinned image; all USB actions remain separately owner-coordinated.
The CLI state-directory flag does not isolate the canonical USB safety guard.
No script here launches the updater, flashes or clears that guard.
