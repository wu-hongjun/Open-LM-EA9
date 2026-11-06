# November upstream trial — November 6, 2026

**Upload and strict readback passed after physical reconnect.** The
owner requested the latest upstream build for a camera trial. The remote `main`
resolved to [e054db9](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/commit/e054db90cfae5d67fac67a7e0db4bb100f5893ae)
immediately before the transfer. [Pinned build](../../firmware/candidates/4.2.0/README.md) ·
[Sanitized receipt](upstream-november-trial-2026-11-06.json).

**The owner later reported that the camera trial did not work.** The exact
failed step remains unknown. The [handshake investigation](../audits/a7c-ii-november-handshake-2026-11-06.md)
records the maintainer's compatibility report and the reproduced software gaps.
No follow-up camera attempt or flash was made.

The local build retains the upstream application behavior and 50 mm f/1.8
defaults. The DFP startup spelling and ROM limit are adapted for this build;
size optimization keeps the image within the established upload range. The
camera-facing version is upstream 2.0. USB metadata 4.2.0 is the local identifier
used to keep the new image distinct from historical firmware 2.0.0. Release
diagnostics are compiled out. The app's installed setting describes the
reported optics; it cannot detect the actual lens or iris.

Two clean builds match the full 20,480-byte image and manifest. The upstream
host suite and all 54 native tests passed. App 0.24.2/build 35 and the signed
native CLI retain the old upload, verification and stock recovery paths. The
new explicit command accepts only the exact pinned image. Prepare-only output
matched all bytes without sending any report.

Native upload made a fresh two-pass full flash and auxiliary backup of stock
1.8.0, checked it could serve as a restoration source and saved the durable
journal before START. One START and 320 application pages were acknowledged;
no extra report followed the last page. The process completed at **2:21 PM
Eastern**. A separate file-only audit passed the backup and journal checks.
The earlier 156 artifact pins, all nine diagnostic registry entries and the
original stock recovery remain intact. Raw backup and USB identifiers stay
private.

After the owner confirmed physical reconnect, the signed native CLI verified
the same adapter on a new USB connection at **2:25 PM Eastern**. Two matching
full-flash and auxiliary passes completed with 4,359 read exchanges and no
writes. The native check and separate file audit matched all 20,480 application
bytes, the expected 58 metadata bytes, boot code, saved records, upper flash,
user row, calibration and device ID. Only the established six loader scratch
bytes were excluded from the flash comparison. The verified stock backup and
original recovery remain available. This USB result does not qualify camera behavior.

The original camera procedure was to power off before mounting, then use confirmed MF
and Pre-AF Off. Check that live view and aperture display respond. If normal,
save one photo, release the shutter fully, then save a second photo and shut
down. Record whether both files saved and whether shutdown responded. This
isolates capture and re-arm before testing AF-S. Stop the trial if the camera
freezes or the motor keeps driving. Stock can be restored through the preserved
USB recovery path. USB verification alone does not qualify camera behavior.
