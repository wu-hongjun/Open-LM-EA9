# System design audits

Requested October 10, 2026. Three subagents independently examined the practical
choices for each product layer, using the pinned references and current primary
documentation. They did not install toolchains, run the updater, or flash the
adapter.

- [Firmware stacks and scheduling](firmware-options.md)
- [Host protocol, persistence and recovery](host-protocol-options.md)
- [macOS app and host tooling](macos-options.md)

The parent synthesis is [the system design recommendation](../system-design-recommendation.md).
The [product direction](../product-direction.md) remains the requirements source.
Recommendations are proposals; hardware compatibility and transport reachability
had not been established when those initial design audits were written.

## Implementation audit and independent firmware study

The owner requested two Astra jobs on October 10, 2026:

- A separate local project thread, **REA study of official LM-EA9 firmware**
  (`01a128ac-9e4d-7382-8efb-d3e6d3ed1893`, model `gpt-6-astra`), uses the
  archived [morluto/rea](https://github.com/morluto/rea) and the recovered
  official application to study startup, E-mount framing, metadata and autofocus.
  Its public notes belong in `docs/reverse-engineering`, private analysis in
  `references/private/rea-analysis`, and tool scratch in `tools/rea-analysis`.
- An independent Astra subagent completed the
  [implementation and optimization audit](astra-implementation-audit-2026-10-10.md).
  It identified two P1 coordination gaps and three P2 recovery, cancellation
  and durability issues, then reviewed the coordinating agent's corrections.
  No unresolved P1 objection remains in that bounded source review.

Both jobs were explicitly instructed to avoid all live USB access, updater launch,
flashing and user Application Support changes. The previously acknowledged stock
upload was awaiting the owner's physical reconnect when those jobs began. The
owner subsequently reconnected; stock readback passed and the 50mm custom image
was uploaded with a fresh backup. After another owner-confirmed reconnect,
custom two-pass readback also passed. A subsequent A7C II photograph confirmed
50mm, f/1.4 and the Contax Zeiss lens name in EXIF. Focus mode, camera display and
clean shutdown remain unconfirmed; the custom build disables motor motion.
See [camera metadata evidence](../evidence/camera-50-metadata-2026-10-10.md).
Audit tests remain offline and do not qualify camera behavior or
arbitrary power-loss recovery.
See [remediation evidence](../evidence/astra-audit-remediation-2026-10-10.md).

## Factory reverse engineering, second Astra pass

The owner subsequently requested deeper factory-firmware reverse engineering
using the same Astra lane. The existing thread was resumed; no duplicate thread
was created. The [completed first pass](../reverse-engineering/stock-first-pass.md)
provides 213 discovered procedures, 268 resolved call edges, 27 targeted dossiers,
verified packet extraction, startup/storage boundaries and a motor-control map.
These counts describe analysis coverage, not complete semantic reconstruction.

The second pass prioritizes the 44-byte factory settings structure, E-mount
input/dispatch and metadata dependencies, autofocus state/timing/limits, and
readable behavioral reconstructions with offline differential checks where
practical. It will assess a metadata patch that preserves factory autofocus.
Its requested public deliverable is `docs/reverse-engineering/stock-phase2.md`;
binary-derived reconstructions and unit values stay in the private analysis tree.
The thread confirmed that it is actively continuing this work.

The second pass remains entirely offline and does not alter production sources,
the adapter, updater, user state or distribution builds. A patch feasibility plan
does not establish camera compatibility or authorize an unreviewed flash image.

## October 11 correctness and reproducibility pass

An independent firmware lane audited the current source against the pinned upstream
implementation and REA dossiers, then reproduced and corrected frame admission,
interrupt handoff, Stop/retarget ownership, telemetry cadence and bounded startup
faults. See [the concrete findings and finite evidence](firmware-correctness-2026-10-11.md)
and [retained compile/run results](../evidence/firmware-correctness-tests-2026-10-11.json).
These fixes form offline AF 2.3; the installed and USB-verified adapter remains 2.2.

A separate offline lane promoted the application reconstruction's authored model
and validators into [tracked research sources](../../research/stock-1.8/README.md)
and reran 24,991 instruction comparisons and ten input/output guards. The
[whole-firmware ledger](../reverse-engineering/whole-firmware-reconstruction.md)
separates this reproducible application subset from the other local models and
remaining peripheral, scheduling, data and replacement-image work.
