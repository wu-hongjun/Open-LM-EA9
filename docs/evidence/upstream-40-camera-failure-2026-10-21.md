# AF 4.0 — battery-required camera crash, no persisted diagnostics

**Camera acceptance failed; further 4.0 trials are held.** The owner confirms two
photo files saved in reported AUTO mode, followed by a hard crash that required
battery removal to turn the camera off. The AUTO wording does not establish the exact dial/menu or focus setting:
actual MF/AF/Pre-AF, preview/exposure, aperture display and motor behavior remain
unverified. No further camera attempt is requested.

[Sanitized receipt](upstream-40-camera-failure-2026-10-21.json) ·
[Strict installation record](upstream-40-upload-2026-10-20.md) ·
[Offline evidence](upstream-40-reference-2026-10-20.md) ·
[Preservation ledger](upstream-40-camera-preserved-2026-10-21.json).

## Owner observations and installation boundary

The initial October 21 client-date report was: “this time, hard crash and i had to
power cycle after two photos.” The clarification confirms both saved files,
AUTO mode as reported, battery-required recovery, camera powered off and adapter returned to
the computer in response to the USB-cap question. Native descriptor/process checks
then confirm one qualified new cap connection and both apps absent. The requested
single MF photo is not relabeled a confirmed controlled MF cycle. The saved files
are owner-reported, not independently inspected; optical focus and exposure remain
unqualified. The earlier 3.9 normal-shutdown observation is not carried into 4.0.

AF 4.0 for the original Contax Zeiss 50mm f/1.4 previously passed strict installation
verification after physical reconnect: complete 20,480-byte image, blank 1K log tail,
known metadata and protected flash/auxiliary windows. That historical verification
remains separate from this failed camera milestone. No source/image change or stock
restoration followed the report.

## Read-only retrieval and independent audit

The pinned signed native reader remained byte-identical, SHA256
`44d9b94f9338037978575fa6a61d2c495383eb8749e3b11bc95c93de63f89b1c`.
Process and descriptor preflight found no updater, prototype app or competing CLI,
one qualified adapter on a new unblocked connection, and an unchanged verified 4.0
journal. Inventory sent no reports. One guarded native backup exited 0 at
**2026-10-21T04:38:24.427217+00:00 UTC**, with two matching 131,072-byte flash passes and
two auxiliary passes, 4,359 CHECK/READ exchanges. No writes, erase, restore or retry
were sent; no further hardware report followed completion.

Filesystem-only checks verify every backup size/digest, recognized boot code,
MCU/geometry, same-unit binding and the new connection. **The entire 128KiB flash
is byte-identical to the pristine installed readback.** User row, calibration and
device-ID windows are unchanged. Pending/applied-lens/firmware-observation/stock-
qualification/library records and blocked-connection membership remain unchanged.
No canonical state or safety marker was manually edited.

Both pre-camera and post-camera full-flash SHA256:
`46c4d45590e03f9deb6bc325aaec531cef6511ee4a443a2b91e157cfcc815248`.
Changed flash bytes: **0**, including zero changed diagnostic pages. There is no
observed flash corruption; this does not establish hardware health or a runtime
fault mechanism. All 49 reconstructed source pins, 151 release/recovery/pin artifacts,
all registry entries and original stock 1.8 recovery remain exact.

## What was retained — and what was lost

The registry/image/manifest-bound decoder reports **0 valid pages, 0 torn pages,
16 erased pages**, zero semantic/cohort issues and zero assembled snapshots.
A direct comparison independently confirms all 1,024 diagnostic bytes are `0xff`;
this is not a decoder rejection or full storage. No homing, motor, capture, local
TX or shutdown record survived. The later backup is diagnostic evidence, not a
new claim of pristine-image installation verification after camera use.

The exact 4.0 source and reviewed compiled call graph locate `st_flush` only in
`powerdown_signal` and `st_fail`. Routine events, motion snapshots and sticky
inhibition reasons are collected in RAM. `st_inhibit_fault` does not flush; terminal
footers require an already sealed snapshot. Battery removal can discard unflushed
RAM, so this design can lose the evidence needed for this failure class.

The blank area does **not** prove a shutdown/fault handler was never entered, a
flash write was never attempted, that homing succeeded/failed, or that the servo,
parser or capture owner caused the crash. An absent terminal admission, interruption,
pre-write failure or lost RAM remains possible. The two saved files demonstrate
partial capture progress, not reference qualification, optical AF or sustained
capture. Actual focus mode is still unknown. No real camera exchange can be
reconstructed from an empty tail; no raw-capture re-arm, home-policy or controller
change is justified by this dump alone.

## Disposition and host hold

Keep 4.0 held and leave the adapter off the camera. No additional camera cycle,
flash or automatic stock restoration is requested. Before another physical trial,
the next offline milestone should address diagnostic persistence through a crash
requiring battery removal, with protocol timing/NVM ownership reviewed and bounded.
This is an observability requirement, not an implemented remedy or permission for
unreviewed mid-protocol flash writes. The root cause remains unresolved.

App 0.23.1/build 32 continues to disable ordinary 4.0 installation from every installed
version and keeps read-only/recovery tools. Historical native commands retain exact
image pins. The previous app fails five intended hold/workflow assertions; the hold
change passes all 53 named Swift tests and signed packaging without launch. The
reader is unchanged; no further app/source change or redundant test campaign was
needed for this clarification/retrieval. The prior signed package is preserved
privately. Raw backups, keys, unit identifiers and real traffic remain private.

This work completes read-only retrieval and evidence analysis. It does not fix
physical homing, capture/shutdown, optical AF or establish factory parity.
