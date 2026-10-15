# Upstream C 3.3 offline hardening — October 15, 2026

Prepared and integrated a separate 3.3 candidate for the original Contax Zeiss
50mm f/1.4, using eleven Astra lanes in waves of three. It is **not installed,
camera-qualified or proven equivalent to stock**. The previously uploaded 3.2
still awaits owner-confirmed physical reconnect and strict verification. No
hardware enumeration, report, updater, flash, motor operation or canonical
Application Support mutation occurred in this batch.

[Candidate and pins](../../firmware/candidates/3.3.0/README.md) ·
[Machine-readable validation](upstream-33-hardening-2026-10-15.json) ·
[Campaign and individual audits](../audits/astra-hardening-campaign-2026-10-15.md).

## Integrated changes

- Full checksum/length/terminator admission precedes dispatch; validated payload
  bounds prevent footer/window padding from becoming operands.
- Capture/control requests have immutable active and pending owners. Raw capture
  waits for VD, suppresses status tails and retains failed-send work. Ordinary
  sessions invalidate stale commands and replies.
- First accepted shutdown owns a dedicated snapshot and immediately revokes
  readiness and inhibits drive. A successful echo and terminal signaling remain
  bounded; repeated commands cannot revive an off adapter. No new park motion
  delays the reply.
- Homing publishes ready only after a successful uncancelled final commit.
  Stop/session/shutdown cancel it; failures inhibit motion. Cancelled work needs
  a fresh motion command and stays within a two-attempt budget.
- Pin remux and request/session publication have short atomic commits. Sensor,
  UART and PWM waits remain outside those commits. Fatal RX drain, work-budget,
  runaway/wrong-way and encoder accumulator overflow inhibit motion.
- Completion uses fresh velocity and retarget dwell. A new ordinary session
  cancels old active motion, queries and deferred work.
- Aperture remains nominal f/1.4 with actual iris Unknown. Capability negotiation
  commits only when an owned ordinary request is consumed; diagnostics label
  observed capability separately. Opaque stock `0x34` handling remains.
- Diagnostics remove both inferred-silence flash writes. First/latest event
  retention, summary-first persistence, one-shot terminal flush and RAM-only
  inhibit reasons improve evidence without active-bus NVM stalls.
- Release-only legacy telemetry and its unused reads are gated out. Selected
  pure/protocol/main units use `-Os`; servo/motor/UART/timers remain `-O2`.
  Pump ADC and control sensor reads remain. Removed raw trace SPI reads, the
  legacy idle voltage burst and compiler choices change incidental cadence;
  host equivalence does not prove electrical timing equivalence.

Lane10 found five failing cross-lane controls after the individual proposals:
request-pointer invalidation, stale readiness after a session/shutdown, and
obsolete request transmission at two admission boundaries. The integrated
fix passes all seven targeted probes including two positive controls. The root
applied no whole earlier AF scheduler/controller transplant.

## Factory findings and explicit limits

REA original-instruction replay confirms phase-driven capture ownership but
also exposes a callback-time shared-RX race in the original firmware. Immutable
snapshots intentionally correct that race. The proposed universal ordinary
sequence increment was rejected: tested ordinary `0x34` replies preserve stored
sequence, while status pairs use their own sequence rule. A masked 256-byte
memcpy proposal was also rejected because its estimated interruption cost was
inappropriate for the receive path; snapshot/checksum work remains interruptible.

Factory shutdown has persisted-option-dependent parking and accepts tested
mode/class combinations. Candidate first-wins shutdown, sticky off/inhibit and
no-new-park policy are documented robustness choices, not exact equivalence.
The factory path enabling homing remains unresolved. Neither stationary sensor
feedback nor a timeout proves physical infinity or motor rest. Stock AF
reconstruction is substantial and partial; the C controller remains upstream.
A7C II capture, exposure, AF-S and shutdown require physical evidence.

## Validation and preservation

Root re-executed every lane's relevant runner and the original-instruction
factory suite. Evidence includes 59 composed ownership cases, 53 shutdown cases,
44 homing checks, 22 transport cases and all 65,536 EIC flag combinations,
392 motion executions, 18 aperture scenarios/all 65,536 opaque operands, six
frozen diagnostic failures, 2,193 storage budgets and 832 injected byte cuts per
implementation. Counts cover overlapping fixtures; do not sum them as unique
behaviors. The prior frame gate has 207,131 finite checks and 3,456 archived
positive frames. Reports bind each scope and negative control.

The final linked source passes seven commit-race probes, 65 capture/session
regressions, 14 storage/capability cases and nine compiled ARM NVM writer cases.
The release cleanup passes 208 executions, including 77 exact wire scenario
pairs, seven servo comparisons, homing/cancellation checks, 65,536 pure numeric
inputs and 40,000 predictor samples. Final source matches that release comparison
apart from the required camera version constant. Full image, manifest and patch
reproduce byte-for-byte in separate fresh build directories.

The fixed image is 20,480 bytes; code plus initialized data ends at `0x9a68`,
leaving 408 bytes before diagnostics. Static RAM is 3,076 bytes with 8 KiB reserved
stack. GCC reports `em_transmit` at 304 bytes, not the complete call-chain/ISR
stack. Stack high-water, physical ISR durations, NVM timing and sensor freshness
remain unmeasured. The cleanup saves 3,796 flash bytes and 888 static RAM bytes
against the composed pre-cleanup control, not against frozen 3.2. That private
size-control image retains 3.2's camera constant and is not a published candidate.

All **53 Swift tests** pass. App 0.16/build 20 and CLI are ad-hoc signed and verified.
Native prepare-only commands produce exact pinned 3.3, 3.2, 3.1 and personalized
3.0 images; 85mm is rejected for 3.3 without output. The independent host lane
passes 45 parameterized DeviceKit cases and one workflow case. First readback
still compares every image byte including blank logs and protected data, and
requires a new physical connection. The offline decoder separately passes actual
published 3.2/3.3 pins and rejects modified prefixes.

[All 47 prior tracked image/manifests/template-pin/recovery artifacts remain
byte-identical](upstream-33-preserved-2026-10-15.json), including original stock
1.8 recovery and frozen 3.2. Raw backups and private camera/unit data remain
excluded. The terminal decoder applicator was made staging-idempotent so its
complete test suite can rerun after root's shared decoder integration; all
fourteen decoder tests pass again. No installation exception was added.

## Reproduction and next acceptance

See the [workbench](../../firmware/upstream-hardening/README.md) for build and
exact-final-source commands, and the [camera procedure](../upstream-hardening-test.md)
for a separately authorized future upload. A passing offline test cannot establish
which physical failure caused previous camera freezes. Keep 3.3 frozen; executable
changes require another version/digest. The remaining eight-hour work window can
add bounded audits/tests without reflashing or relabeling this candidate stable.
