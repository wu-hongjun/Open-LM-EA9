# Biotar 58mm aperture-dial trial: 4.5.0 installation

The owner authorized uploading [4.5.0](../../firmware/releases/4.5.0/README.md)
with the LM-EA9 on its USB cap and both TECHART Update and Open LM-EA9 closed.
The target is a Zeiss Jena Biotar 58mm f/2 on the Sony A7C II. This build
declares 58mm, boots at f/2, and accepts camera-requested reported values
through f/16. The physical iris remains controlled by the lens ring.

## Preflight and upload

The source-built, signature-verified native CLI detected one matching adapter.
Its prepare-only command emitted the exact pinned application:

`8fba0303581fd684ae279a73aab7be136508f5d90b6fc975c5e4406a210c9f35`

The original stock recovery application and encrypted archive passed the
offline recovery verifier, and the separate local key remained present.
The previous 4.4.0 update was already recorded as verified. Private update
state was snapshotted before this transaction.

`ea9ctl apply-camera-aperture --idle` completed a fresh two-pass flash and
auxiliary backup using 4,359 read exchanges. Admission required the qualified
bootloader and exact pinned 4.4.0 application. An independent file audit
validated the published backup, its same-connection identity binding, the
complete 4.4.0 code and the planned 58 metadata bytes with only the version
changed to 4.5.0.

One START and all 320 application pages were acknowledged. The 20,480-byte
upload finished at **06:01:28 UTC on November 7, 2026** (1:01:28 AM EST).
The durable journal records the expected image, Biotar startup profile and
completed upload. No post-upload CHECK, READ or other USB report was sent
before the owner-confirmed physical reconnect. Raw backups, identities and
transaction state remain private.

## Reconnect verification: passed

The owner confirmed a physical unplug/reconnect with both apps closed.
`ea9ctl verify --idle` then completed two matching flash/auxiliary passes
using 4,359 read exchanges on the new connection. Strict verification passed
at **06:04:40 UTC on November 7, 2026** (1:04:40 AM EST). The native verifier
published firmware 4.5.0 and the Biotar's compiled 58mm/f/2 startup setting.

An independent offline audit of both published backups confirmed the same
unit on a different USB connection, all 20,480 pinned application bytes, all
58 expected metadata bytes, unchanged boot code, saved records, upper flash,
user row, calibration and device ID. The six established loader scratch
bytes at `0x403a..0x403f` remain outside the metadata comparison. NVM geometry
qualified and its snapshot also matched; these register reads remain
non-atomic observations, not a lock-state restoration guarantee.
[Sanitized verification result](biotar-45-install-2026-11-07.json).

## A7C II camera result: owner-confirmed working

On November 7 the owner reported that this firmware works well and explicitly
confirmed **AF, photos, aperture-dial control and shutdown work**. This is the
working baseline for the owner's A7C II and Biotar 58mm f/2 setup.

The actual focus/exposure mode, Pre-AF setting, selected aperture values,
saved-photo path/EXIF, quantitative exposure and endurance counts were not
supplied. Those details remain unverified; the general positive report is
accepted without requiring another test. This does not establish all-camera,
all-lens compatibility or factory parity.

The owner subsequently requested a wider virtual f/1.2–f/22 range. It is
prepared as separate [4.6.0](../../firmware/releases/4.6.0/README.md), while the
working 4.5 application and original USB/offline evidence remain unchanged.
