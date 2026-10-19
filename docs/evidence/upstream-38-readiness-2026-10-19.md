# AF 3.8 homing-query readiness — October 19, 2026

**AF 3.8 is prepared offline. One homing-related protocol dead end is reproduced
and repaired. Physical homing and the A7C II capture/shutdown freeze remain
unresolved. No adapter was enumerated, opened, flashed or driven in this work.**
The owner requested a separate flashing session. Factory parity remains
unachieved; the firmware is C on the pinned upstream implementation.

[Candidate](../../firmware/candidates/3.8.0/README.md) ·
[Machine-readable acceptance record](upstream-38-readiness-2026-10-19.json) ·
[Build/test reproduction](../../firmware/upstream-hardening/next38/README.md) ·
[Future coordinated procedure](../upstream-readiness-test.md).

## Evidence and integration decision

The latest owner-confirmed 3.7 attempt saved two photos in AF, then froze and
required battery removal. AF-S versus AF-C and other settings remain unknown.
Both diagnostic cohorts report generic `home-failed`; the newer cohort lacks
full event/motion detail because storage was full. Earlier local capture and
shutdown TX returns do not prove camera acceptance and must not be attributed
to the later attempt. [Failure record](upstream-37-repeat-camera-failure-2026-10-19.md).

Three requested **gpt-6-astra** lanes audited the pinned production composition
and REA/upstream evidence in parallel:

| Lane | Finding and disposition |
| --- | --- |
| [42: homing readiness](../audits/astra-42-home-readiness-2026-10-19.md) | Frozen 3.7 strands operand-only optical queries after homing failure. Accept the minimal liveness fix and independent phase diagnostics. |
| [43: capture/status](../audits/astra-43-capture-status-2026-10-19.md) | Eleven production cases and original stock instruction replay support existing post-capture silence and readiness re-arm. No new production patch justified. |
| [44: shutdown](../audits/astra-44-shutdown-liveness-2026-10-19.md) | Seventeen capture/wait/tail cases expose no separate production defect. Keep the bounded fail-stop/terminal policy and its timing limits. |

In 3.7, the foreground query worker runs only after readiness and additionally
rejects motor inhibition. Failed homing leaves readiness false and motion
inhibited indefinitely, so either gate independently strands operand-only
queries. Those conversions need supplied operands and static maps, not a home
reference or current encoder coordinate. 3.8 services them before foreground
polling and removes only the two worker motor-inhibit predicates. Handshake,
abort, session, shutdown, critical-section and finite queue protections remain.
It does not assert readiness, release inhibition, reset a reference or retry
homing after failure.

Six fault schedules reproduce zero answers on frozen 3.7 and one correct answer
on 3.8, with motion still inhibited/unready. Both half-fixes fail. Eight unique
home workloads cover normal completion, clock wrap, drive and settle movement,
UART work crossing each deadline and frozen/shared poll budgets. The lane
requires all 18 expected passes and 13 intended assertion failures across 31
executions, including independent cutoff/inhibit/shared-budget/phase mutants.
The same final candidate appears twice in candidate-mode groups; these are not
31 distinct workloads. ASan/UBSan and exact reply-byte checks are retained.

Phase-only codes 17 (drive), 18 (settle) and 19 (shared work budget) replace the
generic home failure in those branches. All existing deadlines, shared counter,
drive polarity/duty, stillness thresholds and failure actions remain unchanged.
Phase labels identify software branches, not physical end-stop evidence.
The decoder admits them only for registry-bound 3.8; 3.7 interpretation remains
unchanged. An earlier summary and a later fatal footer may legitimately retain
different faults; the writer's equal terminal reason/fault requirement remains.
The real source-produced late-fatal fixture already covers that distinction.

REA-assisted replay of the pinned stock 1.8 application executes seven
capture/re-arm cycles. Raw echo returns to initialization mode; eight VD pulses
alone remain silent, and ordinary readiness restores the connected status mode.
The supplied connected state, explicit callbacks and cut peripheral operations
do not prove physical timing or full startup reachability. Changing status
policy or shutdown timing without a reproduced counterexample is not a verified
fix. Capture/shutdown ownership and controller code therefore remain unchanged.

## Final candidate and host integration

Only `main.c`, `startup_trace.h` and the version in `emount.h` differ from 3.7.
No new production module is linked. The behavioral fix saves 16 bytes; phase
attribution adds eight. Code plus initialized data ends at `0x9ab0`, with 336
bytes before logs, 3,044 bytes static RAM and 8 KiB reserved stack. The complete
1 KiB log tail remains erased in the prepared image and append-only at runtime.

Image SHA-256 is `8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`;
manifest SHA-256 is `be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0`.
The candidate retains lens ID234 and nominal f/1.4 for the original Contax Zeiss
50mm profile. Actual aperture stays Unknown; physical stopping down remains a
lens-ring operation. No new aperture or exposure policy is introduced.

Signed app 0.21.0/build27 includes an explicit experimental 3.8 action and
`prepare-readiness-upstream` / `apply-readiness-upstream`. It retains the 3.6/3.7
camera-failure holds, fixed-profile restrictions and existing backup, durable
journal, physical reconnect and strict readback guards. Installed 3.8 is shown
as unqualified, with no runtime profile editing. The app was packaged and its
signature verified, but never launched; canonical Application Support state was
not accessed. All native preparation used isolated private state and exited
before inventory. Preparing an image does not authorize USB activity.

## Verification and limits

- All **29 offline acceptance groups** pass against the repeat build: 14 retained
  production-path suites, three new Astra compositions, original stock capture
  replay, trace/compaction/reset/writer checks, version-scoped/adversarial/legacy
  decoding and final compiled composition. All 49 source pins and 27 test-input
  pins are checked before/after. Intentional historical test-contract adapters
  are explicit and pinned; baseline controls remain separately enforced.
- All **53 Swift tests** pass (7 LensCore, 35 DeviceKit, 11 app workflow), including
  the retained 3.7 assertion and new 3.8 full-image/reconnect/blank-log checks.
  Eight native prepare-only actions reproduce versions3.1–3.8 exactly; 88 wrong
  profile, edited profile and existing-output cases are rejected.
- Two builds at different paths produce identical image, raw binary, manifest
  and patch. The compiled audit checks exact normalized instructions, symbols
  and program headers before rebinding only ELF/map container hashes. It rejects
  policy edits and altered instructions; optimized Python is explicitly rejected
  because assertions are required. Four retained graph/pin mutants also fail.
- The compiled conditional stack envelope remains **1,516 bytes** with no
  unresolved edges or recursion. Callback registrations, library frames,
  terminal/wait operations, vectors and NVM caller gates are checked. This is
  not a physical stack high-water or interrupt-duration measurement.
- All **136 historical artifacts** and every previous registry entry match the
  [preservation ledger](upstream-38-preserved-2026-10-19.json). Published images,
  digest pins and original stock recovery are untouched. Historical runners'
  duplicate public receipt writes are suppressed in private test copies.

The physical homing trajectory, failed branch and camera-side capture sequence
remain unknown. Synthetic clocks and finite schedules do not measure bus/IRQ/
NVM timing or prove a mechanical cutoff inside a blocked call. Stationary or
frozen encoder feedback can still satisfy the existing software-reference
policy. Homing readiness, focus accuracy, exposure, capture, shutdown and factory
parity need observed hardware acceptance. No new camera outcome is claimed.
The next separate session must preserve fresh logs and complete upload,
physical reconnect and strict full-image/protected-data verification before a
single coordinated camera cycle.
