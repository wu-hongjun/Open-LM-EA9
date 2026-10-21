# AF 4.0 offline acceptance

Run `python3 scripts/test-upstream-reference.py --build PRIVATE_BUILD --output
PRIVATE_OUTPUT` against the frozen candidate. `--skip-compiled` is explicitly a
partial run and cannot produce final acceptance. Final receipts bind image,
manifest, all 49 sources, shim, tests, fixture adapters and compiler/stack evidence.
No test sends device reports or qualifies camera behavior.

The 14 historical template runners remain hash-bound, with copies generated in
private output. The 3.9 query-live and phase-label adapters are retained. Three
additional 4.0 harness changes expose the actual new reference contract:

- Time and target/time fixtures extract `abs_encoder_home_reset` from the
  candidate, counting its actual coordinate commit. Their synthetic motor
  boundaries support the new detached-release entry. The production encoder
  helper is not replaced by a stub.
- The target/time reset-session injection occurs after the validated coordinate
  commit. Its former trigger depended on the second raw read that4.0 deliberately
  removes. Session cancellation and reset-count assertions remain unchanged.
- The home-inhibit negative control removes both the existing home cancellation
  inhibition guard and the new encoder-reset inhibition guard. Removing only the
  first now remains safely closed. Actual candidate checks retain both guards.
  The master also executes the original single-guard control against frozen 3.9.

Lane49 provides the new late-reference policy tests and concrete mutants, and
lane50 composes readiness with the actual servo, protocol owners, completion,
queries, raw readiness/re-arm and shutdown. These replace the old45/46 candidate
harness assumptions about the strict drive deadline; old sources and receipts
are preserved. The remaining capture/status, shutdown, ADC independence, trace,
original stock capture/re-arm, compiled writer and decoder checks run against
actual4.0 or explicitly identified historical controls. The new version-scoped
reference decoder test runs alongside the unchanged3.9 home decoder.

The motor/encoder trajectories and scheduling are supplied offline. Passing
establishes the asserted software contracts, not physical endpoint identity,
optical acquisition, camera shutter acceptance or measured interrupt timing.

## Reproduce the release

Use the pinned toolchain/dependencies and reconstruct the frozen3.9 tree first,
following the [previous workbench](../next39/README.md) and its earlier prerequisites.
The builder requires that exact49-file tree at `artifacts/private/homing39-repeat`,
including its source manifest, patch and host shim; it rejects a substituted base.
Generated/private files are not imported into Git. From the repository root, with
fresh output names and an existing private parent:

```sh
python3 scripts/build-upstream-reference.py --output artifacts/private/reference40-rebuild
python3 scripts/test-upstream-reference.py --build artifacts/private/reference40-rebuild --output artifacts/private/reference40-retest
./scripts/swift-local.sh test
./scripts/build-macos-app.sh
```

Do not run the app as part of offline acceptance: its refresh enumerates devices.
Only `prepare-reference-upstream` with a fresh private `--state-directory` and new
output returns before inventory; other CLI verbs can operate hardware and are
outside this task. The state-directory flag does not isolate the canonical USB
safety lock or reconnect guard. The [separate procedure](../../../docs/upstream-reference-test.md)
requires owner authorization and physical reconnect before post-upload reports.

The builder verifies3.9 full image/manifest/source/shim/patch pins, the accepted
applicator and compiler flags, vector bounds,256-byte code margin and the blank1K
log tail. Reproductions must match the published4.0 image; behavioral changes
require a new candidate. Final acceptance checks all input pins before and after,
including the exact compiled policy, and preserves146 historical artifacts and
all older registry entries. The two fresh release builds match manifest, image,
source, patch and shim. ELF/map container paths may differ only under the strict
normalized-disassembly/symbol/section rebind contract.
