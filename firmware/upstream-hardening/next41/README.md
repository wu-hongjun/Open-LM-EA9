# AF 4.1 offline crash-observability acceptance

The master is `scripts/test-upstream-crash.py`. It accepts an exact frozen build
under `artifacts/private`, verifies the published image/manifest/resource and all
source pins, runs retained contract suites plus crash/health/decoder acceptance,
then checks source/test/preservation pins again. `--skip-compiled` is explicitly
partial and cannot produce a final-acceptance status. Candidate pins bind the frozen4.1 image and manifest in `test-inputs.json`;
an unset or substituted pin rejects acceptance.

The fourteen historical regression templates remain pinned and untouched. The
new41 binder reuses the reviewed37 binder, changes only the candidate/base identity,
and retains the40 contract adapters for validated homing reset and scheduling.
Shared `compiler_compat.py` adds weak observation mocks and `st_health` only to
host clang/cc links. Historical fixtures have synthetic peripherals and do not test
watchdog hardware; this stub makes that boundary explicit. The dedicated52 health
suite executes actual watchdog code against inert registers, and compiled checks
independently inspect target behavior. ST_HOST omits only the retained ELF section
placement; the target linker/boot-retention audit establishes that placement.

Private wrapper scripts apply the same compatibility boundary to the49/50/48/43/
44/35/36 runners. They do not edit candidate sources or relax their manifest pins.
Existing temporary adapters admit4.1 in version checks, preserve original decoder
version sentinels, and bind packet-reset recompilation to exact candidate flags.
The unchanged40 failed-home decoder suite still checks its original ABI; the new
crash decoder suite independently checks41 type5 records and ordinary cohorts.
All historical receipt writes remain suppressed only in fresh private copies.

Lane54 executes actual trace C with checkpoint-interruption hooks, synthetic flash
power cuts, reset-cause matrices, retained/flash corruption and negative controls.
Its actual emitted recovered and baseline-plus-summary pages feed the new decoder
suite. CRC-valid impossible payloads and cross-cohort children remain untrusted;
new records cannot become ordinary snapshots or shutdown proof. No later page is
trusted after a crash or invalid-CRC storage barrier, because41 boot fail-stops there.
CRC-valid foreign headers do not automatically trigger that storage latch; actual
C fixtures verify the decoder preserves this distinction.

A passing offline run does not establish physical watchdog timing, measured NVM
or interrupt latency, camera capture/shutdown acceptance, focus quality, or the
root cause of the4.0 crash. Battery removal before reset/append can still lose the
checkpoint. A zero-byte failed append leaves no durable evidence. No task here
opens or enumerates hardware, launches the app/updater, or edits host safety state.

## Reproduce the frozen candidate

Materialize the pinned toolchain/dependencies and the exact frozen 4.0 tree at
`artifacts/private/reference40-repeat` first, following the
[previous workbench](../next40/README.md) and its earlier prerequisites. Generated
private trees are not imported into Git. Use fresh private output paths:

```sh
python3 scripts/build-upstream-crash.py --output artifacts/private/crash41-rebuild
python3 scripts/test-upstream-crash.py --build artifacts/private/crash41-rebuild --output artifacts/private/crash41-retest
./scripts/swift-local.sh test
./scripts/build-macos-app.sh
```

Do not launch the app: its refresh enumerates devices. Isolated native
`prepare-crash-upstream` with a fresh private state directory and output returns
before inventory. Every hardware verb remains outside offline acceptance. The
state-directory option does not isolate canonical USB safety/lock state.

The builder pins six changed baseline files and all three accepted applicator
inputs; it preserves 49 source-file identities, the 1 KiB diagnostic region,
256-byte code margin floor and 8 KiB stack reserve. Two fresh builds must match
complete image/manifest/source/patch/shim bytes. Exact compiled checks retain the
reviewed call/stack analyzer, require the fixed NOLOAD region and strong naked
HardFault vector, and bind every health/NVM call site. ELF/map path differences
are accepted only under the strict normalized-disassembly/symbol/section contract.
The only new optimization flag is `servo -Os`; supplied I/O and actual compiled
ordering remain independently checked.

The app adds a pinned full image and explicit research action. Fixed-lens,
fresh-backup, journal, physical-reconnect and strict complete-image/protected-data
verification guards remain. App packaging/signatures and native preparation do
not demonstrate installed bytes or camera acceptance. See the separate
[installation/test/log procedure](../../../docs/upstream-crash-diagnostic-test.md).

Final root acceptance on the fresh repeat build passes all 40 suite groups,
including the compiled audit and 681 new crash-decoder checks. The sanitized
[release receipt](../../../docs/evidence/upstream-41-crash-diagnostics-2026-10-21.json)
binds the complete test/input and private-output digests. The conditional compiled
stack bound is 1,588 bytes, not a measured runtime high-water mark.
