# Astra lane 10 — adversarial composition review

Offline source-level review, October 15, 2026. Root owns integration and release.
Uploaded 3.2 remains pending owner reconnect and strict verification. No device
was enumerated/opened, no HID/USB report or updater was invoked, and no physical
motor, Application Support state, recovery material or released image was changed.
This lane performed no networking, binary extraction or binary analysis.

## Reproduced cross-lane failures

Review inputs were the campaign, reports 01–08, the in-progress accepted plan and
builder, root frame/TX applicators, and a fresh private source composition of
02 → 01 → 03 → 05 → 06 → 07 → 08 (06 replaces the root motor overlay).
Lane09 and root's exact final draft received a later checkpoint below. The in-progress
accepted plan was not mistaken for a published candidate.

1. **A session interrupt can null the active request pointer.** Lane01 clears
   `g_retry` when it admits ordinary INIT/0x01. Lane07 dereferences that global
   for its operand-length guard. An interrupt immediately before the guard on
   ordinary 0x34 produces a UBSan null-member-access abort in composed production
   `emount.c`. The request's local immutable snapshot remains valid; its retry
   bookkeeping pointer does not.
2. **Old handshake completion can publish readiness into a new session.** An
   ordinary 0x01 received after the completion predicate and immediately before
   `em_handshake_done = 1` resets readiness and increments the epoch, but the
   interrupted foreground store then restores readiness without the new session
   completing its handshake.
3. **Shutdown can likewise be followed by stale readiness publication.** The
   same cut with shutdown0x16 leaves readiness true despite the sticky latch.
   Merely locking the completion commit is insufficient: a shutdown accepted
   immediately after unlock must itself revoke readiness at admission, rather
   than waiting for a future acknowledgement poll.
4. **Earlier request admission also needs its epoch.** A new ordinary session
   after the old control's length/fixup work but before transmit is not caught
   by the TX-local CS generation: that generation is sampled after the new
   session. A second probe interrupts at the dequeue/active-owner handoff.
   Both controls transmit an obsolete 0x0a reply. These are the same ownership
   defect at earlier boundaries, not additional hardware failure claims.

The negative control is the **composed source before10**, not frozen 3.2: the
null access arises from interactions between the new lane01 and lane07 code.
Two positive controls preserve ordinary successful0x0a and immutable0x34 despite
an unrelated pending0x19. All control expectations are explicit in the runner.

## Minimal source applicator

[`apply.py`](../../firmware/upstream-hardening/lanes/10-integration/apply.py)
operates only on a disposable source tree after07;08 may precede it, and root
intends to apply09 last. It changes only `emount.c`:

- Pass the stable local request length into the ordinary sender.
- Publish active request pointer, byte pointer and captured epoch together under
  the already existing dequeue lock; do not resurrect a retry after an ISR has
  invalidated it.
- Check that active epoch inside the existing final TX admission lock, alongside
  CS and shutdown checks. The lock never spans UART or checksum work.
- Serialize successful completion's epoch/shutdown predicate and readiness
  publication; discard retries belonging to an invalidated epoch.
- Clear handshake readiness immediately when shutdown is accepted.

Only the existing accepted ordinary0x01 path advances the epoch. A raw capture
0x01 does not become a session opener. Ordinary template sequence bytes remain
unchanged; status sequence and raw echo rules are preserved. This is an explicit
ownership policy, not a claim of exact factory behavior.

## Evidence and reproduction

The source snapshot used for initial controls is
`artifacts/private/astra-10-initial`. Exact input hashes are in the result files.

```sh
python3 firmware/upstream-hardening/lanes/10-integration/run.py \
  --source artifacts/private/astra-10-initial \
  --output artifacts/private/astra-10-control-02
python3 firmware/upstream-hardening/lanes/10-integration/run.py \
  --source artifacts/private/astra-10-initial \
  --output artifacts/private/astra-10-proposed-03 --proposed
python3 firmware/upstream-hardening/lanes/10-integration/regression.py \
  --source artifacts/private/astra-10-regression-source \
  --output artifacts/private/astra-10-regression-01
```

Use fresh output directories for re-execution. The first two runs execute whole
production dispatcher/packet/ownership/shutdown/trace modules against the
existing host hardware shim, with Clang ASan/UBSan and warnings as errors.
Explicit hook calls mark four C instruction boundaries. The host IRQ model
preserves nested masking and delivers pending callbacks at unlock. It invokes
actual CS receive callbacks with complete checksum-valid requests.

**Before10: five intended failures and two passing controls. After10: seven of
seven pass, without sanitizer diagnostics.** The null case's required failing
control emits UBSan's null-member-access diagnostic. The host link emits the
existing Darwin common-section alignment warning; it is not a runtime failure.

**65 capture/session regressions pass** against the composed dispatcher plus10:
existing lane01's59 cases plus raw0x01 at all six status interruption points.
These include 9/17/64/255/256-byte echoes, normal-traffic controls, raw exact
bytes, ordinary template sequence preservation, first-wins pending ownership,
failed sends, session queue invalidation, focus-copy IRQ masking and shutdown.
The regression runner reuses the existing lane01 fixture and records its hash;
it does not pretend that reuse is an independent protocol oracle.

## Exact all-lane draft checkpoint

Reviewed root `firmware/upstream-hardening/build/full-draft-6`, manifest image
SHA-256 `adc4b5de9a717b1a573425006ef565962bf5c56ab2233a4eca9192feb7ad11cd`.
Every manifest-bound C/header input matched before diagnostic tests. This draft
contains finalized lanes 08, 10 and 09. **All seven targeted probes, 65 capture/session
regressions and 14 diagnostic cases pass on these exact source files.**

```sh
python3 firmware/upstream-hardening/lanes/10-integration/run.py \
  --source firmware/upstream-hardening/build/full-draft-6 \
  --output artifacts/private/astra-10-final-commits --already-applied
python3 firmware/upstream-hardening/lanes/10-integration/regression.py \
  --source firmware/upstream-hardening/build/full-draft-6 \
  --output artifacts/private/astra-10-final-regression
python3 firmware/upstream-hardening/lanes/10-integration/diagnostics.py \
  --source firmware/upstream-hardening/build/full-draft-6 \
  --output artifacts/private/astra-10-final-diagnostics
```

The diagnostic cases execute actual final `startup_trace.c`: 11 storage cases,
including 832 page tear cuts, 2,193 budget combinations and all seven first-inhibit
reason codes, plus 9/10/11-byte capability cases through the actual dispatcher.
Source gate assertions verify no `emount.c` flush, exactly one main flush after
UART disable, and the fail-stop flush after IRQ disable and GPIO detach. The
writer source remains byte-identical to frozen 3.2. `st_inhibit_fault` is checked
as a RAM-only first-reason assignment under a preserved mask, with no NVM call.

Lane09's report and 208 before/after executions were reviewed. A separate source
comparison confirms that **every staged source matches lane 09's verified after
composition except the version constant in `emount.h` (0x32→0x33)**. Thus its
seven actual servo tests and 19 homing cases per build cover the same motion and
home source reviewed here; this lane does not relabel those as its own runs.
Comparison evidence: `artifacts/private/astra-10-final-source-comparison.json`.

Root's manifest records code plus initialized data end 0x9a68, 408 bytes before
0x9c00, 3,076 bytes static RAM and 8 KiB reserved stack. The builder checks the full
code/data end and 256-byte minimum margin, plus the blank diagnostic tail, and
rejects differing bytes if 3.3 has already been published. These are root build
results reviewed here, not a separate binary analysis or measured stack high
water. Root must refresh test-input hashes and repeat the final build after
these scripts/reports are frozen; the lane 10 applicator is unchanged since the
reviewed draft.

**No remaining release-blocking defect was found within this bounded reviewed
source scope.** This is not installation or physical qualification. Root and
lane 11 own final host/resource pins, fixed-profile selection, explicit command
semantics, immutable prior artifacts and full-image reconnect verification.
Diagnostic prefix matching remains separate from installation verification.

## Limits

Explicit C hooks model selected IRQ boundaries; no instruction-level test here
establishes all interrupt schedules, external pin timing, sensor freshness,
physical stopping, camera acceptance or electrical stability. The existing
lane 06 driver tests and lane 09 regressions establish separate bounded cutoff
properties; the dispatcher fixture does not drive motor registers. Query answer
publication was inspected only partially and is not granted general concurrency
acceptance by this checkpoint. Physical stack high water and camera behavior
remain unmeasured. Uploaded 3.2 still awaits owner reconnect/strict verification;
no 3.3 installation was performed or implied.
