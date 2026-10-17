# Upstream C AF 3.7 — targeted tracing, fixed 50mm f/1.4

Prepared offline for the original Contax Zeiss 50mm f/1.4 profile. The separately
authorized October 17 upload and strict byte verification passed after physical
reconnect, with an independent full-image/protected-data audit, in the
[live installation record](../../../docs/evidence/upstream-37-upload-2026-10-17.md).
**Camera acceptance failed; further trials are held.** The owner reports some
movement, no achieved focus and a freeze after one photo. Read-only log retrieval
and independent Astra review are complete in the
[camera evidence](../../../docs/evidence/upstream-37-camera-failure-2026-10-17.md).
The trace records `home-failed`; its cause and the freeze cause remain unresolved. It
retains 3.6's controller, guards, origin, optical maps, aperture policy and
protocol replies, with BCD version `0x37` and additional diagnostics.

The first wrong-way/runaway snapshot retains the accepted command, target,
leg origin/direction, retarget/rebase state, requested duty and four existing
encoder samples. Completion suppression, queue admission and successful TX
return are recorded separately. Capture tracing identifies raw versus ordinary
requests, saved session/sequence at TX START and RETURN, and shutdown admission.
The v3 log retains 32 recent focused events and excludes routine status noise.

After the initial terminal-only snapshot, separate footer pages can record VD
two-low/timeout, the PA23 write, tail-delay return and a later fatal fault. All
are software breadcrumbs. Missing records, a GPIO store or a delay return do
not prove physical motion, pin voltage, camera acceptance or power-off.

The reserved range remains `[0x9c00,0xa000)`, sixteen 64-byte pages, append-only
without erase or retry. Four terminal pages are reserved where capacity permits;
used storage can prevent a complete snapshot or any recording. Live camera-bus
and IRQ paths only update RAM. Flash writes remain in terminal/fail-stop context.

Lossless storage of the existing 1,272-byte reply initializer and compact trace
calls make room for these records. Reset restores every original table byte
after BSS clearing, before this handler's VTOR rewrite. The bootloader may
already have selected application vectors; inherited IRQ quiescence and physical
startup timing remain unqualified. Instrumentation adds execution/NVM time.

| Artifact | SHA-256 |
| --- | --- |
| 20,480-byte application | `6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5` |
| Manifest | `15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b` |

Loaded code/data ends at `0x9ab8`, leaving 328 bytes before logs (floor 256).
Static RAM is 3,044 bytes; reserved stack 8,192 bytes. Compiled analysis gives a
conditional 1,516-byte stack envelope; no physical high-water/timing measurement
exists. Lens ID is 234; nominal reported AV is 4352 (f/1.4). Actual iris is Unknown.
This fixed build has no runtime lens-profile row; library edits remain local.

Historical `prepare-trace-upstream`/`apply-trace-upstream` actions remain pinned
for research. App0.20.1 blocks ordinary 3.7 installation after this camera failure.
Older commands/pins and the 3.6 camera-failure hold remain separate. Any later flash
requires the existing backup, physical reconnect and complete strict byte/
protected-data verification. The completed owner-coordinated cycle and read-only
log retrieval do not authorize another trial of this failed image.

[Build/test prerequisites](../../upstream-hardening/next37/README.md) ·
[Evidence and limits](../../../docs/evidence/upstream-37-tracing-2026-10-15.md) ·
[Milestone and Astra scopes](../../../docs/firmware-targeted-tracing-2026-10-15.md) ·
[Coordinated test/log procedure](../../../docs/upstream-targeted-trace-test.md)
