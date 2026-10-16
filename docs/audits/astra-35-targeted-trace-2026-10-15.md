# Astra 35 — compact v3 tracing and terminal shutdown evidence

October 15, 2026. This is a new offline AF3.7 observation proposal. It does not
restart the expired campaign or its paused heartbeat. AF3.6 remains held after
the reported camera capture/shutdown failure. No physical timing, camera
acceptance, motor remedy or factory parity is established by this work.

## Scope and source boundary

The source base is the exact `artifacts/private/handoff36-repeat` tree matching
the pinned 3.6 candidate manifest and image SHA-256
`d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`.
The applicator writes only a new private staged tree. Lane35 delivers the
diagnostic core, byte schema, shutdown markers and tests under
`firmware/upstream-hardening/followup/35-targeted-trace/`; lane33 owns motion
observation and lane34 owns capture/ownership instrumentation. Root owns the
decoder, versioned builder, registry and host application integration.

The original first-window preservation helper is byte-identical. The hardware
NVM writer remains byte-identical; its containing source gains only a terminal
footer call in `st_fail`, after the existing emergency GPIO cutoff, fault note
and flush. Motor control, guard thresholds, gain/map/origin/polarity choices,
protocol bytes and existing timeout budgets are unchanged by this applicator.
The main shutdown function adds observations after its existing UART-disable
boundary. Flash writes add elapsed time there; no physical timing claim follows.

## Byte schema and retention

`schema.json` is the machine-readable contract and `trace_format.h` contains
typed layout assertions. Serialization uses `memcpy` only with compile-time
little-endian, structure-size and field-offset checks.

Each page is 64 bytes: magic `E9S3` at 0–3, version 3 at 4, type at 5,
cohort at 6, item count at 7, little-endian physical slot at 8–9, chunk at 10,
reserved zero at 11, 48-byte payload at 12–59, IEEE CRC32 over bytes 0–59 at
60–63. Cohort equals the first append slot plus one; it is not a physical boot
counter. Types are summary 1, focused events 2, motion chunks 3 and terminal
footer 4. Reserved bytes are zero.

Summary payload offsets are milliseconds 0, RX bytes 4, last RX milliseconds 8;
16-bit RX count 12, TX return count 14, RX errors 16, UART status 18, focused
evictions 20 and intentionally filtered observations 22; then byte fields stage
24, historical handshake 25, fault 26, pins 27, first/last RX 28/29,
first/last TX 30/31, capability 32, capability-seen 33, shutdown marker 34,
retained focused count 35, planned focused count 36 and planned motion chunks
37. Bytes 38–47 are zero. Saturating counters never wrap. Fault is the first
nonterminal inhibit unless a terminal `ST_FAULT` arrives before the summary;
a terminal fault after the initial snapshot is recorded separately in its footer.

There are 32 recent focused 12-byte event records. Each contains milliseconds
at 0, kind at 4, opcode/ID at 5, ownership flags at 6, sequence at 7 and two
16-bit fields at 8/10. Capture kinds 11–18 interpret those last two fields as
the low/high halves of the full session token. All retained events are written
in chronological ring order. Motion is a dedicated 144-byte bounded snapshot
serialized as three 48-byte chunks, with four existing sensor samples and a
frozen guard context; lane33 defines its fields and completion semantics.

Legacy stage, CS, RX, successful-TX and capability events update their summary
fields/counters but are filtered from the focused ring. Ownership CS and phase
events require RAW flag 1. TX start/return events require CONTROL flag 2 or
SHUTDOWN flag 4. The filtered counter includes every such intentional omission.
These choices prevent repeated ordinary status traffic from displacing the
capture opener and its ownership boundaries. The focused eviction counter plus
`retained - planned` counts omitted focused records, subject to saturation.
Neither a full retained snapshot nor zero focused evictions means full runtime
history.

Initial payload budget is `max(0, 11 - initialSlot)`. Three motion chunks are
planned only if that budget admits all three. Remaining budget permits up to
four events per page, bounded by the retained count. Fresh storage therefore
admits one summary, three motion pages, eight event pages and four terminal
pages. Existing occupied storage can reduce this capacity; planned counts are
intentions, not assertions that the writes completed. A summary is attempted
even with less than four footer slots left. Missing records always remain
missing/unknown, never success.

## Storage and post-flush boundaries

The range stays exactly `0x9c00:0xa000`, 16 × 64-byte pages. Init scans all
pages and appends after the highest occupied/torn slot; it never fills earlier
holes. Every append checks that its selected slot is erased, consumes the slot
before the write, and permanently stops this run's writer on read/write failure.
There are no erase operations, retry loops or occupied-page rewrites. Reboot can
use a wholly erased failed slot, while any partially programmed slot is skipped.
Host strict initial full-image verification remains a separate unchanged gate;
diagnostic mutability does not relax it.

`st_note` and motion observations are bounded RAM-only operations. The first
snapshot writes only at the existing allowed terminal/fail-stop callsites.
`st_terminal` requires the sealed snapshot and is called only after UART disable
or emergency motor cutoff. All append operations use the existing IRQ lock.
There is no NVM call from receive IRQ or normal active protocol handling.
A fail-stop may record after motor cutoff while the UART peripheral is still
configured; this is not a claim that an active bus is preserved on failure.

Footer payload is kind at 0, bounded observed value at 1, current fault at 2,
one-based footer ordinal at 3, milliseconds at 4–7 and zero bytes 8–47.
Kinds are: 1 two consecutive VD-low readings observed; 2 bounded VD wait
expired; 3 PA23 software write reached; 4 the existing 100-tick delay returned;
5 subsequent `st_fail`. Footer 1/2 is after the VD loop and before PA23,
footer 3 is after the write and its existing timestamp assignment, and footer 4
is after the existing delay. A later terminal fault can append after all three.
These statements concern software execution. They do not independently measure
the electrical pin, transmitted reply delivery or camera power state. Power
loss between a software boundary and its footer can leave that boundary unknown.

## Verification and remaining gate

The compiled production core passes ASan and UBSan tests over all 17 initial
occupancy counts, chronological 32-record retention, saturating
summary counts, full-session field preservation, CRC's standard check vector,
occupied/gap/torn-page scanning, failed reads, and no write when disallowed.
All 1,040 page/cut combinations (16 attempted pages × 65 byte-cut positions)
exercise write failure, no subsequent retry and reboot append placement.
Four deliberately broken variants fail as required: sealing out later footers,
incorrect ring order, retry after a write failure, and corrupted CRC.

The extracted production shutdown function passes six synthetic cases covering
two-low success, timeout with zero or only one final low sample, each with
completed or interrupted final delay. Assertions establish UART disable before
storage, VD-result marker before PA23, PA23 marker after the write, and completion
marker only after the 100-tick delay returns. This is source execution with inert
registers and deterministic time, not MCU/IRQ/peripheral timing simulation.

Lane34 additionally executes the production emount path with this real core and
motion recorder: raw capture opener, ordinary recovery opener, 100 intervening
status cycles, then shutdown. It retains 22 focused records without eviction,
counts 1,226 filtered observations and 205 successful TX returns, and performs
no active-bus NVM operation. Its filter-removal control loses the intended
capture context and fails. See that lane's `retention-results.json`.

The header specializes compile-time constant legacy diagnostic calls through
`st_summary(kind,id,ms)` and focused calls through `st_record(ms,identity,payload)`.
The generic seven-argument `st_note` ABI remains callable, including dynamic
kinds. Tests compare their entire serialized buffers byte for byte. Existing
millisecond expressions remain evaluated; omitted legacy metadata arguments
are side-effect-free reads/literals at the inspected production callsites.
The original-width casts are retained in packed fields. No schema field is
removed by this footprint optimization.

`run.py --source <private-build-directory>` verifies every source hash from
that directory's manifest, copies those exact sources, and tests its core and
extracted shutdown function. The default mode independently verifies all
pinned 3.6 source hashes and applies the lane to a new private source copy.
`measure.py` composes lanes33/34/35 with the original3.6 per-unit flags and
`-Os` only for the new motion recorder; it emits ELF/map, no loadable image.

The composed measurement after these trace-only reductions ends at `0x9d94`,
404 bytes beyond diagnostics, with 3,044 static RAM bytes and 8,192 reserved
stack bytes. This includes initialized-data load bytes; linker success alone
is insufficient. It needs another660 bytes of reduction to meet the unchanged
256-byte minimum margin and is not an acceptable candidate. Additional
root-owned representation proposals and final integration remain separate
review gates.
No binary has been published or flashed by this lane. Real camera frames, unit
dumps, keys and identifiers were not opened or copied. No adapter enumeration,
HID, motor operation, updater/app launch or canonical application state access
occurred.
