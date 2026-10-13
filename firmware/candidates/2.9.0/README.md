# AF 2.9.0 — Contax Zeiss 50mm f/1.4

**USB upload/readback passed; camera acceptance failed; further trials held.** This candidate
keeps healthy camera communication/timing serviceable through sticky motion
faults, records transmission success truthfully and resets status admission on
a new initialization request. A fresh stock backup is saved; AF 2.8 stays held.
See [the installation record](../../../docs/evidence/af-29-upload-2026-10-12.md).
The owner reports focus achievement followed by an immediate capture-time
freeze, requiring battery removal. See [the failure and protocol investigation](../../../docs/evidence/af-29-camera-failure-2026-10-12.md).
The owner later reports reset movement on reboot followed by no focus movement;
the actual focus mode and reference state remain unverified. Do not retry this
image to obtain additional observations.

| Property | Value |
| --- | --- |
| Loader / camera | 2.9.0 / BCD 0x29 |
| Application / profile | `[0x5000,0xa000)`, 20,480 bytes; profile at `0x9f00` |
| Declared / actual aperture | Fixed f/1.4 / Unknown, physical ring only |
| Image SHA-256 | `c5fac2eeb7b8c26833b37555f25598352c850f224dba1d091379c09cd9a6ffc3` |
| Template SHA-256 | `657406719f6f911b49b6430015a7c1f1ffa1ff1a4f8b454ec578fe5bf005fa3c` |
| Profile SHA-256 | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340` |
| Flash margin / static RAM / stack | 276 / 2,200 / reserved 8,192 bytes |

See [implementation and limits](../../../docs/evidence/af-29-link-service-2026-10-12.md),
[validation](../../../docs/evidence/af-29-validation-2026-10-12.json),
[build inputs](../../../docs/evidence/af-serviced-build-manifest-2026-10-12.json),
[image manifest](contax-zeiss-50-f1-4.manifest.json) and
[camera runbook](../../../docs/af-s-test.md).

38 targeted cases pass and 15 failures are detected in frozen 2.8 controls.
The pure controller/reference/aperture/observer are retained. The owner's freeze
and shutdown hang were not proven resolved; AF 2.9 also failed capture and
shutdown acceptance. Faulted motion remains inhibited; no automatic rearming is introduced.

App 0.12.0/build 15 and explicit `prepare-af`/`apply-af` select 2.9. Normal lens
changes preserve the verified installed variant. All older templates/images and
original recovery are preserved. The implementation/validation pass was offline;
the separately authorized October 12 installation is recorded above.

```sh
python3 scripts/build-firmware.py --variant serviced-af
scripts/swift-local.sh test
python3 scripts/test-camera-link.py --output /new/link-checks
python3 scripts/test-firmware.py --af
tools/rea-analysis/venv/bin/python scripts/test-stock-shutdown-order.py --output /new/stock-shutdown
scripts/build-macos-app.sh
# Isolated local state and new output paths; no USB reports:
dist/ea9ctl --state-directory /new/state prepare contax-zeiss-50-f1-4 /new/profile.bin
dist/ea9ctl --state-directory /new/state prepare-af contax-zeiss-50-f1-4 /new/native.bin
python3 scripts/prepare-af.py /new/profile.bin /new/python.bin
cmp /new/native.bin /new/python.bin
```

Output parents must exist; evidence directories/files must be new. Full Git
history containing `1043bad` is required for frozen controls. Use the repository's
pinned Unicorn dependency. Upload and camera testing are separately coordinated.
