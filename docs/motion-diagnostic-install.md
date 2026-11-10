# LM-EA9 4.8.1 diagnostic installation

The CLI uses the bank transaction path for an explicitly coordinated 4.8.1
install. It requires the same unit's existing stock-upload qualification, the
pinned 4.8.0 application/extension/bank, a valid committed profile with no
newer pending request, and an erased, unlocked `0x14000–0x16000`. The plan
binds the full two-pass preflight, device connection, preserved bytes, payload
and protected auxiliary data to the approval. A fresh backup and plan must
still match that approval immediately before the upload.

One START carries `4.8.1` in metadata bytes 0–2 and the existing bytes 3–57.
The 832 sequential pages cover `0x5000–0x12000`, including exact copies of the
opaque bytes in `0xa000–0x10000`. No page reaches the bank, journal, trace
slots, or later upper flash. The known six loader scratch bytes are excluded
from post-upload equality. Boot, saved records, bank, live journal, trace slots,
upper flash, user row, calibration, device ID, geometry and lock bits must
match before camera use. This uses the pinned loader's physical and software
lock checks for the outgoing payload and adds the diagnostic trace lock check.

With TECHART Update and OpenLensAdapter closed and one adapter on its USB cap:

```sh
dist/ea9ctl inspect --idle
dist/ea9ctl bank-plan motion-diagnostic -
dist/ea9ctl bank-motion-diagnostic APPROVAL --idle --experimental
# Physically unplug and reconnect the same adapter through its USB cap.
dist/ea9ctl bank-verify --idle
```

The plan is disk-only. The existing transaction code saves recovery evidence
and a durable intent before START. A lost report or interrupted upload keeps
that intent pending. No follow-up report is sent on the upload connection.
Use the same adapter on a new connection for the complete two-pass verify.
The original pre-bank and stock recovery backups remain available. Profile
switching is disabled while the diagnostic is installed, so the two camera
cycles use the same committed profile.

After strict verification, follow the loaded then bare procedure in the
[4.8.1 release notes](../firmware/releases/4.8.1/). Retrieve each trace with a
read-only two-pass backup after normal shutdown and a physical reconnect. The
decoded raw trace and backup stay private. Use the pre-test verified backup as
the baseline for checking all bytes outside the diagnostic trace range.

The first owner-coordinated upload and its verification state are in the
[November 9 hardware record](evidence/motion-481-install-2026-11-09.md).
