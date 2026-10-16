# AF 3.7 targeted tracing: offline acceptance

**AF 3.7 is prepared and tested offline for the original Contax Zeiss 50mm
f/1.4. Nothing was flashed, enumerated or opened on the adapter. Camera
stability, the wrong-way cause and the shutter-freeze fix remain unestablished.**
The owner will coordinate flashing separately. Installed 3.6 retains its
capture/shutdown failure hold. The expired eight-hour campaign remains closed
and its heartbeat paused.

[Machine-readable record](upstream-37-tracing-2026-10-15.json) ·
[Candidate/pins](../../firmware/candidates/3.7.0/README.md) ·
[Reproduction instructions](../../firmware/upstream-hardening/next37/README.md)

## What the new evidence can distinguish

The actual 3.6 failure log has a sticky wrong-way inhibit and a later UART-disable
marker, but lacks the fault-time encoder/leg coordinates, capture owner and
terminal shutdown progress. The new C modules address those specific gaps:

- Motion: accepted command/operand, initial and current target, leg origin and
  direction, retarget/rebase/hold state, requested duty and four existing encoder
  samples. The first wrong-way/runaway record freezes before a later leg or
  shutdown can overwrite it. Completion suppression, attempt, queue admission/
  overflow and successful status TX return have separate dispositions.
- Capture: raw/ordinary owner, saved session/sequence at TX START and RETURN,
  pending/active slot and local phase, owner completion and shutdown admission.
  A control TX uses its owning request's sequence, which may differ from the
  frame template's sequence. RETURN keeps START's identity across intervening RX.
- Shutdown: after the initial sealed snapshot, append-only footers can retain
  VD two-low versus timeout, the PA23 store, 100 ms delay return and a later
  fatal fault. The initial seal no longer prevents observing those later steps.

The unchanged log range is sixteen 64-byte pages at `[0x9c00,0xa000)`: one
summary, three 48-byte motion chunks, up to eight pages of 32 focused events and
four reserved terminal pages where capacity permits. Routine CS/status records
are filtered while RX/TX counters remain. In the integrated retention fixture,
raw and ordinary capture survive 100 subsequent status cycles; an unfiltered
control loses that evidence and fails. No active-bus/IRQ path writes NVM; there
is no runtime erase, failed-page retry or rewriting of an occupied page.

Fault summary semantics remain precise: the first inhibit is sticky until a
terminal `st_fail` can replace the current reason. The separate motion snapshot
preserves the first wrong-way/runaway context; later footer reasons describe the
terminal point. Neither record establishes encoder polarity, real displacement
or the camera's awaited completion. No guard is removed and no success invented.

## Fit and representation review

The initial complete tracing composition exceeded the real loaded-code/data
boundary. The release gate correctly rejected it; linker text alone was
insufficient because initialized data also consumes flash. The 256-byte floor
and the original log/protected-data boundaries were preserved.

Compact diagnostic calls save 84 loaded bytes; the same composition without
that factoring has only 244 bytes margin and fails the floor. A lossless packet
initializer representation saves another 648 bytes. Its 159-byte bitmap and
374 nonzero values restore **all 1,272 original bytes**, including zero padding;
descriptors/fixups are unchanged. Reset calls the initializer after BSS clearing,
before this handler's VTOR rewrite. The bootloader can already have application
vectors selected; inherited IRQ quiescence stays conditional. The initializer
adds startup work, and tracing adds execution and terminal flash-write time.

The image ends at `0x9ab8`, leaving **328 bytes** before logs. It uses **3,044
bytes static RAM** and **8,192 reserved stack**. Independent compiled analysis
bounds modeled stack use at **1,516 bytes**, conditional on its explicitly
reviewed callbacks, boot/control state, priority model and intact program data.
Physical high-water, IRQ latency and NVM/startup timing have not been measured.
Controller, guards, motor polarity, coordinate origin, optical maps, aperture
policy and wire layout remain upstream; firmware identity changes to BCD `0x37`.

Image SHA-256: `6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5`.
Manifest SHA-256: `15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b`.

## Exact final acceptance

Two fresh compositions produce identical full image, raw load bytes, manifest,
source pins and patch. Normalized instructions, symbols and program headers
also match. The final master passes **23 groups**, checking all **49 source
hashes** before/after and retaining original failing controls:

- Startup, parser/capture/session publication, homing inhibition, query flow,
  coordinate, target/time and release-counter regressions; exact final motion
  parity has seven servo, 22 focus and seven relative cases plus six rejected
  broken observers. Test-only API/reset adapters are explicit and pinned.
- Real v3 core: 1,040 byte-cut/write-failure cases, all 17 occupancy levels,
  chronological retention, counter saturation, terminal reserve, no retry and
  six extracted production shutdown-tail cases; four broken controls fail.
- Actual compiled reset/initializer: every packet byte independently matches
  original C and linked ELF; three poisoned-RAM/incoming-PRIMASK cases execute
  Reset_Handler and its callees through main entry. Five negative controls fail.
  The initializer takes 17,674 supplied instructions, not measured cycles/time.
- Actual ARM writer: nine bounds/erased-page/error cases. Exact compiled
  composition: 41 rejection controls and an accepted exact 1,516-byte budget;
  callbacks, 17 library bodies, vectors, nested PRIMASK restoration, emergency
  cutoff-before-logging and source/control composition are checked.
- Host decoder: 2,111 corruption/partial/cohort checks, 60 independent semantic
  controls and 27 candidate/registry/native-backup controls. The initial decoder
  failed 49 of the 60 semantic checks; integrated code passes all. All 49 legacy
  decoder checks still pass.

Readable CRC-valid pages stay visible when association is incomplete. A missing
or malformed planned snapshot or earlier footer prevents trusting later markers
as a complete terminal chain; trust cannot recover midway. Unsaturated and
saturated motion cursor rules, unused sample bytes and timestamp wrap follow
the actual writer. No validity/completeness label authenticates arbitrary bytes
or proves physical shutdown or camera acceptance.

All **53 Swift tests** pass. App **0.20.0/build 25** and CLI are built and signed,
without launching the app. The separately named 3.7 variant/action preserves
the 3.6 hold and all historical command mappings. Seven native prepare-only
commands reproduce their exact 3.1–3.7 images; the 85mm profile is rejected.
The fixed original 50mm profile has no runtime metadata row, and actual iris
remains Unknown. CLI SHA-256:
`b9c9f77f80ef80e0fd59c97de0d878d62ef68fd5a30b7d1fe4995479a4cf8e67`.

## Reviews, preservation and remaining gate

Seven gpt-6-astra lanes completed distinct scopes, at most three active at once;
root integrated shared files and repeated the exact composed tests:
[33 motion](../audits/astra-33-motion-tracing-2026-10-15.md),
[34 capture](../audits/astra-34-capture-tracing-2026-10-15.md),
[35 storage/tail](../audits/astra-35-targeted-trace-2026-10-15.md),
[36 footprint](../audits/astra-36-trace-footprint-2026-10-15.md),
[37 packet reset](../audits/astra-37-packet-initializer-2026-10-15.md),
[38 exact compiled composition](../audits/astra-38-exact37-review-2026-10-15.md),
[39 decoder/host](../audits/astra-39-decoder-host-review-2026-10-15.md).

All **131 preexisting release/recovery/pin files** compare byte-for-byte with
base commit `d65662a`; historical registry entries remain exact. The original
stock 1.8 recovery application remains SHA-256
`f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`.
[Preservation inventory](upstream-37-preserved-2026-10-15.json).
Earlier images/digests, private dumps and canonical Application Support state
were untouched. Only the new registry entry was appended.

Full factory reverse engineering and factory AF parity remain incomplete. The
next evidence requires a separately authorized upload, physical reconnect,
complete strict byte/protected-data verification and one coordinated cycle
followed by private read-only logs. The
[future test procedure](../upstream-targeted-trace-test.md) preserves those gates.
No further shutter attempt, AF-S trial or hardware action follows from these
offline tests.
