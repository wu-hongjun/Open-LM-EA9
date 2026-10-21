# AF 3.9 — homing observations and release ADC dependency removal

Prepared offline. The separately authorized [upload](../../../docs/evidence/upstream-39-upload-2026-10-20.md) and strict byte verification passed after physical reconnect, including an independent full-image/protected-data audit. **One camera cycle and logs are pending; compatibility remains unqualified.** Fixed to the original
Contax Zeiss 50mm f/1.4 profile (lens ID 234, nominal AV 4352). Actual physical iris
position is unknown; no runtime lens-profile row is supported.

This builds on pinned upstream C commit
`d52ed06cc449918f938e0695fbf29a0c4141f2b2` and frozen 3.8. It removes an unused
blocking ADC dependency from the release communication pump/startup and adds a
32-byte failed-home snapshot plus a saturating count of later consumed non-Stop
requests. It retains reference readiness, deadline rechecks, sticky inhibition,
capture re-arm policy, motor guards and the upstream controller. The physical
phase 17 failure and camera shutter-block cause remain unresolved.

| Artifact | SHA-256 |
| --- | --- |
| [20,480-byte image](contax-zeiss-50-f1-4.bin) | `87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44` |
| [Manifest](contax-zeiss-50-f1-4.manifest.json) | `9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a` |

[Exact delta](from-38.patch) changes only `main.c` and the version constant in
`emount.h`. Code plus initialized data ends at 39304 (`0x9988`), leaving 632 bytes
before diagnostics, above the unchanged 256-byte floor. Static RAM 3040 bytes;
reserved stack 8192. The full `[0x9c00,0xa000)` diagnostic tail remains erased in
the pristine image. Compiled stack analysis and offline controls are described
in the integrated evidence; they do not measure physical execution.

Preserve these published bytes and all historical releases/recovery. Any later
production change requires another candidate version. Do not resume held 3.8
camera trials. Separate owner-coordinated upload requires a fresh backup,
durable journal, physical reconnect and strict complete-image/protected-data
verification before the [one-cycle camera procedure](../../../docs/upstream-homing-test.md).

[Integrated evidence](../../../docs/evidence/upstream-39-homing-2026-10-20.md) ·
[Build/test workbench](../../upstream-hardening/next39/README.md) ·
[Prior camera/log evidence](../../../docs/evidence/upstream-38-camera-failure-2026-10-20.md).
