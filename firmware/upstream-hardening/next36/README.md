# Post-3.5 startup handoff composition

[Candidate 3.6](../../candidates/3.6.0/README.md) accepts the scoped EIC setup/start
proposal, two release-invisible RAM snapshot omissions and BCD version 0x36.
The rejected full-PRIMASK proposal remains only in the audit workbench. Root
owns integration; scripts here never access hardware.

The builder requires exact pinned 3.5 materialization at
`artifacts/private/absolute35a`. If absent, reproduce the
[3.5 prerequisites](../next35/README.md) first:

```sh
python3 scripts/build-upstream-absolute.py --output artifacts/private/absolute35a
```

Then choose fresh private output paths under existing parents:

```sh
python3 scripts/build-upstream-handoff.py --output artifacts/private/recheck36
python3 scripts/test-upstream-handoff.py --build artifacts/private/recheck36 --output artifacts/private/recheck36-tests
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

`accepted-lanes.json` pins the exact applicators and supporting source tests.
The production delta changes only EIC C/header and protocol C/version header.
The host shim gains a separate no-op hardware API for tests; its hash is bound
in the manifest and it is never linked into the ARM image. Flags, compiler,
controller and drivers remain unchanged. The builder checks initialized-data
load extent, the 256-byte minimum margin, vectors, RAM/stack limits and blank
diagnostic pages. A published 3.6 image must reproduce exactly.

`replay.py` reuses pinned prior regression templates in private copies rather
than duplicating their fixtures per release. Explicit transformations retain
the original fixture locations, bind the new version/image/manifest and use
the new hardware mock ABI only for proposal sources. Test cases and expected
outcomes are unchanged; frozen controls retain their old sources and mocks.
Each replay records both template and transformed-runner hashes. Exact final
startup tests execute actual UART/EIC source through the independent lane 28
harness. Source/compiled identities are checked before and after execution.

The master also runs retained capture/shutdown/home/query/numeric/target/time
checks, decoder boundaries and the compiled ARM writer. Its compiled stack/
handoff audit keeps every reviewed callback, library, vector and ordering guard.
Fresh ELF/map path strings may differ: `stack-reproduction.json` permits only
those container pins to be rebound after exact image/raw/manifest/source and
normalized disassembly/symbol/program-header equality. No compiled ordering
or physical-entry caveat is relaxed.

Native Swift tests, signed packaging and isolated prepare-only commands are
separate checks. Do not launch the app during offline work: normal refresh
enumerates hardware. USB backup/apply/verification and camera tests remain
owner-coordinated. The prior 3.2 journal was resolved by strict verification in
a separate interactive session; the authorized 3.6 upload now awaits its own
physical reconnect and verification. No script here modifies either journal.
See [offline evidence](../../../docs/evidence/upstream-36-handoff-2026-10-15.md)
and the separate [installation record](../../../docs/evidence/upstream-36-upload-2026-10-15.md).
