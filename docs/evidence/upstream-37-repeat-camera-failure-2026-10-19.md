# AF 3.7 — repeat camera freeze, October 19

**Camera acceptance remains failed; further 3.7 camera trials remain held.**
The owner reports another attempt with two photos taken before a freeze, followed
by returning the adapter to the computer. A fresh read-only backup contains a
new software `home-failed` summary. The detailed event history for this later
record was omitted by the writer's remaining-capacity policy. Freeze cause and
the failing homing phase remain unresolved.

[Sanitized receipt](upstream-37-repeat-camera-failure-2026-10-19.json) ·
[Earlier full trace](upstream-37-camera-failure-2026-10-17.md) ·
[Source-bound Astra40–41 review](../audits/astra-40-41-af37-camera-trace-2026-10-17.md)

## Owner report and observation limits

The owner said: “I tried again and it took two photos before freeze, it is
connected again.” This is an owner-initiated repeat after the prior hold; no
additional camera test was requested. The photo count is an owner observation,
not independent saved-file or EXIF verification. Actual MF/AF, Pre-AF, exposure,
whether both files saved, exact freeze stage, shutdown and battery removal remain
unverified. Root asked only for details already known, without another test.

The existing USB-cap return context and preflight establish a fresh qualified,
unblocked connection with no competing updater/app/CLI processes. Same-unit
identity and a new connection are confirmed by the native backup. Camera
shutdown/battery actions are not inferred from the USB return.

## Native read and independent audit

The signed CLI remains pinned to SHA-256
`b9c9f77f80ef80e0fd59c97de0d878d62ef68fd5a30b7d1fe4995479a4cf8e67`.
One `backup PRIVATE/after-camera.ea9backup --idle` operation completed two matching
131,072-byte flash reads and two auxiliary passes, with 4,359 CHECK/READ exchanges.
It exited 0 at **2026-10-19T15:08:02.331732+00:00 UTC**
(**11:08:02 America/New_York**). No write, erase, upload, restore or retry was sent.
Full flash SHA-256:
`7f192fc9a3eea86fca3644940e799ff7860d09e29e0e4d50fcb74f2f45989dee`.

The filesystem-only audit verifies both native backup manifests, all file sizes/
digests, boot identity, MCU geometry and same-unit binding. Compared with the
October 17 post-camera backup, exactly **128 flash bytes changed**, all within
the two previously erased diagnostic pages, zero-based slots 14 and 15. All
earlier occupied pages are preserved byte-for-byte. Every flash byte outside
`[0x9c00,0xa000)`, the immutable application prefix, user row, calibration and
device-ID data is unchanged. Canonical pending/applied/firmware-observation files
and the blocked-connection set are unchanged; only native marker JSON ordering
changed. No journal or safety marker was manually altered.

The frozen image/manifest, all 49 reconstructed source digests, all 131 previously
inventoried release/recovery/pin artifacts and original stock recovery remain
exact. No firmware or app source was modified for this follow-up. Raw dumps,
unit identifiers, camera operands and complete decoded records remain private.

## New evidence and capacity boundary

The decoder finds **16 valid pages, zero invalid, inconsistent or unassociated
pages, and no erased pages**. The old fourteen-page cohort is unchanged. The
new summary at slot 14 is writer-consistent and records connected state, the
handshake flag, zero reported UART errors, `home-failed` and the UART-disable
boundary. The final page records **VD-timeout** for that new cohort.

Only two pages were free before the attempt. The pinned writer therefore planned
**zero event pages and zero motion chunks**. It records 32 buffered focused
events omitted for capacity, 35 earlier evictions and 14,048 filtered/summarized
observations. Its `snapshotStatus: complete` means that this reduced plan was
fully persisted; it does not mean a detailed motion/capture history survived.

The new record independently repeats the software homing-failure marker; the
drive, settle or work-budget branch is still unknown. There is no retained new
motion trajectory, owner sequence or TX pairing with which to explain this
attempt's two-photo report. The earlier cohort's raw-echo/PA23 observations must
not be attributed to the later attempt. The new PA23 and delay-return footers
could not fit once the final page was consumed; their absence does not locate
a shutdown hang or prove an electrical power state.

Diagnostic storage is now exhausted. This writer has no runtime erase path, so
further starts cannot append another cohort. A future candidate installation
must provide fresh diagnostic storage through the existing upload/verification
gates. Root did not erase or reflash to obtain more logs. Full storage is
an observation limit, not an established cause of the camera freeze.

Keep 3.7 held and leave the adapter on its USB cap. The next source investigation
remains the exact homing/readiness workload and post-capture status ordering
described by Astra40–41. This follow-up does not claim those proposed experiments
were run or a remedy was implemented. Two reported photos before a freeze do
not establish capture stability, optical AF or factory parity.
