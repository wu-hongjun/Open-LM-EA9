# Bounded C composition after 3.3

[3.4 candidate](../../candidates/3.4.0/README.md) freezes four reviewed overlays:
coordinate admission, query session ownership/budget, query backpressure/pump
service, and terminal homing failure after inhibition. `accepted-lanes.json`
pins applicators and supporting proof/test inputs. Root owns integration.

Reproduce pinned 3.2 and 3.3 build prerequisites as described in the
[parent workbench](../README.md). The immutable materialized 3.3 input is
`firmware/upstream-hardening/build/final-33a`; recreate it with
`scripts/build-upstream-hardened.py --output` at that path if absent. Use fresh
private output directories with existing parents:

```sh
python3 scripts/build-upstream-bounded.py --output artifacts/private/recheck34
python3 scripts/test-upstream-bounded.py --build artifacts/private/recheck34 --output artifacts/private/recheck34-tests
```

The builder checks the published 3.3 manifest, image and source hashes; applies
only the frozen plan; compiles every production ARM unit with the established
flags; enforces initialized-data load extent, at least 256 bytes before logs,
RAM/vector bounds and a blank 1 KiB diagnostic tail. An existing published 3.4
must reproduce exactly. No hardware or state-store operations occur.

The test entrypoint validates exact source/image/resource hashes, prior capture/
shutdown regressions, query ownership and flow with failing controls, arithmetic
boundaries, inhibited homing and composed fault cuts, compiled stack evidence,
compiled ARM flash writer, and independently pinned diagnostic decoding. Host
Swift tests and signed packaging remain separate:

```sh
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

Do not launch the app during offline work: its normal device refresh enumerates
hardware. Native `prepare-bounded-upstream` may be exercised with an isolated
`--state-directory`; it returns before device inventory. No install/backup/verify
command is part of offline validation.

`measure.py` is an analysis-only link of the coordinate/query proposal before
the final homing guard. Its 300-byte margin is historical exploratory evidence;
the final image has 276 bytes. The rejected 64-bit widening remains documented
in `../followup` rather than being silently substituted into this candidate.
See [unified evidence](../../../docs/evidence/upstream-34-bounded-2026-10-15.md).


The exact stack review pins its original ELF/map containers. A fresh build keeps
image/raw/manifest identical but may embed a different private directory in
DWARF/map strings. `stack-reproduction.json` binds the reviewed ELF/policy and
normalized objdump disassembly, symbol table and program headers. The acceptance
runner requires all these hashes before rebinding only ELF/map container pins
in scratch; executable bytes, source inputs and reviewed call evidence stay exact.
