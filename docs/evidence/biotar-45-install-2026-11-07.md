# Biotar 58mm aperture-dial trial: 4.5.0 installation

The owner authorized uploading [4.5.0](../../firmware/candidates/4.5.0/README.md)
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
completed upload. No post-upload CHECK, READ or other USB report was sent.
Raw backups, identities and transaction state remain private.

## Reconnect verification: pending

The owner has been asked to physically unplug and reconnect the cap before
any further USB reports. Complete-image and protected-data verification
has not yet run. The upload acknowledgement alone does not establish the
installed bytes or authorize camera testing.

After the confirmed reconnect, run the guarded native verifier and independently
compare all application bytes, expected metadata, boot code, saved records,
upper flash, user row, calibration and device ID. The six established loader
scratch bytes at `0x403a..0x403f` remain outside the metadata comparison.
NVM register snapshots are non-atomic; qualify their geometry and record any
observed differences separately from immutable factory data.

## A7C II aperture-dial test: pending

No camera observation is recorded for 4.5.0. Once byte verification passes,
guide one startup/shutdown cycle with the Biotar. Confirm still-photo A,
actual MF and Pre-AF Off where available. Check live view and boot f/2, then
whether the camera dial accepts f/2.8 and f/4. Set the physical ring to match
f/4 before one MF photograph if the camera and motor are behaving normally.
Record actual settings, displayed values, saved-file/exposure result and
shutdown; leave unknown details unverified. A numeric display is not proof
of actual iris position or correct exposure. Stop after a freeze or abnormal
drive rather than repeating a failed trial.

The existing [offline checks](../../firmware/candidates/4.5.0/offline-evidence.json)
remain unchanged. This installation does not establish Sony dial acceptance,
saved exposure/EXIF, autofocus quality or camera stability.
