# Astra firmware hardening campaign — October 15, 2026

The owner explicitly requested a minimum of ten Astra lanes auditing and fixing
different concerns, with a new offline candidate, documentation, commits and
push. The runtime allows four concurrent agents including root, so three Astra
lanes run concurrently in waves. Each numbered lane has a separate report and
workbench directory. Root owns shared production/build/app changes and release
publication; lanes provide bounded reproductions, modules or applicators and
independent review. Do not count a queued lane as completed.

All lanes use **gpt-6-astra**. The current foundation is frozen upstream C 3.2,
SHA-256 `e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
No lane may open/enumerate the adapter, send USB reports, flash, run the updater,
drive hardware or mutate canonical Application Support state. 3.2 remains
uploaded but awaiting physical reconnect/strict verification. Published images,
original recovery, unit dumps and keys are immutable/private as appropriate.

| Lane | Scope | State | Write ownership |
| --- | --- | --- | --- |
| 01 | Capture/status/control phase ownership and interrupted replies | Integrated; root composed 59-case recheck passed | `lanes/01-capture`, [`report`](astra-01-capture-2026-10-15.md) |
| 02 | Shutdown priority, snapshots, repeated shutdown and lifecycle | Integrated; root 53-case recheck passed | `lanes/02-shutdown`, [`report`](astra-02-shutdown-2026-10-15.md) |
| 03 | Homing origin/readiness and cancellation | Integrated; root 44 checks and final home regression passed | `lanes/03-homing`, [`report`](astra-03-homing-2026-10-15.md) |
| 04 | REA original-instruction factory oracle | Complete; root oracle recheck passed; rejected blanket sequence rewrite | `lanes/04-factory`, [`report`](astra-04-factory-2026-10-15.md) |
| 05 | UART/EIC receive ownership and bounded transport | Integrated; root 22 cases plus all EIC flag combinations passed | `lanes/05-transport`, [`report`](astra-05-transport-2026-10-15.md) |
| 06 | Servo/encoder completion and fault policy | Integrated; root 392 executions passed; release control regressions passed | `lanes/06-motion`, [`report`](astra-06-motion-2026-10-15.md) |
| 07 | Aperture/capability and fixed lens metadata | Integrated; root 18 scenarios plus opaque operands passed | `lanes/07-aperture`, [`report`](astra-07-aperture-2026-10-15.md) |
| 08 | Diagnostic NVM, retention and decoder | Integrated; root storage/cut/budget/decoder rechecks passed | `lanes/08-diagnostics`, [`report`](astra-08-diagnostics-2026-10-15.md) |
| 09 | Footprint and reproducible release gates | Integrated; root 208 regressions passed; final 408-byte margin | `lanes/09-release`, [`report`](astra-09-release-2026-10-15.md) |
| 10 | Independent adversarial source integration | Five composed failures fixed; exact final 7+65+14 checks passed | `lanes/10-integration`, [`report`](astra-10-integration-2026-10-15.md) |
| 11 | Extra independent Mac host/upload review | Complete; no verified blocker; targeted cases and prepare-only checks pass | `lanes/11-host`, [`report`](astra-11-host-2026-10-15.md) |
| 12 | Follow-up query epoch and bounded worker | Root completed tests/proposal after interrupted Astra turn; not published | `followup/12-query`, [report](astra-12-query-2026-10-15.md) |
| 13 | Follow-up numeric reachability | Root completed partial proposal after interrupted Astra turns; range/size gates open | `followup/13-numeric`, [report](astra-13-numeric-2026-10-15.md) |
| 14 | Exact 3.3 whole-chain stack/IRQ envelope | Astra complete; root analyzer/six negative guards passed; conditional bounds | `followup/14-stack`, [report](astra-14-stack-2026-10-15.md) |

Lane directories are relative to `firmware/upstream-hardening/`; reports are in
this directory. Private scratch is under `artifacts/private/astra-NN-*`. Shared
files require root integration; do not overwrite another lane's work. Agent
messages coordinate interfaces, but do not replace source-bound tests.

## Integration policy

Require a demonstrated defect or justified measured improvement, a failing
control against frozen source, tests through the production path where feasible
and an explicit limitation statement. Track accepted, deferred and rejected
findings individually. Keep the C foundation modular; do not restore the failed
AF 3.0 scheduler/controller wholesale. Retain exact aperture/optical evidence and
avoid guessed gains/origins/exposure compensation. Behavioral changes receive
version 3.3 with a new digest, fixed original 50mm profile and explicit host
installation action; old command meanings and frozen releases remain unchanged.

The initial frame admission module and its 207,131 finite checks are already in
`9001d41`. That is a host overlay, not an installed fix. Integrating it must not
weaken the full-image verification/reconnect guard or lose nonzero-tail support.
No offline review establishes physical camera stability or factory parity.

The [eight-hour ledger](../firmware-hardening-2026-10-15.md) remains the time and
hardware boundary. Update this matrix as lanes finish and document the unified
candidate only after the applicable test and preservation gates pass.


## Root disposition and frozen batch

All requested ten lanes actually ran with Astra; an eleventh independently
audited host integration. Each ran in its own directory with at most three active
Astra workers. Root rechecked and integrated lanes 02/01/03/05/06/07/08/10/09,
then prepared [3.3 offline](../../firmware/candidates/3.3.0/README.md). Research04
and review11 are evidence lanes, not executable overlays. No lane is merely queued.

Accepted findings, deliberate factory-policy differences and deferred physical
questions are in the [unified record](../evidence/upstream-33-hardening-2026-10-15.md).
The universal ordinary-sequence rewrite and masked 256-byte copy were rejected.
The independent review found real interactions missed by individual lanes;
root does not infer system acceptance from the number of auditors.

No device was inspected or flashed. Root's exact final source, ARM writer,
decoder pins, full 53 Swift tests, signed packaging and native prepare-only checks
pass. All 47 preexisting tracked release/recovery/pin artifacts remain identical.
Uploaded 3.2 is still pending physical reconnect and strict verification.
Candidate 3.3 remains camera-unqualified, with physical capture/exposure/AF-S and
shutdown evidence still required. The timed campaign continues with bounded
offline reviews; it must not change a frozen image under the same version.


The later [follow-up workbench](../../firmware/upstream-hardening/followup/README.md)
is not part of frozen 3.3. It identifies additional source defects and a partial
proposal that currently exceeds the diagnostic boundary. No new candidate or
hardware action occurred. Rows 12/13 are root-completed source work, not claims
that interrupted Astra turns completed successfully. Row 14 is a completed Astra
audit of the existing compiled image. Published images and the 3.2 pending
transaction remain untouched. The timed ledger tracks the next bounded work.
