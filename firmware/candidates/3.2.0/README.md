# 3.2.0 — upstream C startup diagnostic, 50mm f/1.4

**Uploaded; physical reconnect and strict byte verification pending. Not
camera-qualified.** [Current installation record](../../../docs/evidence/upstream-32-upload-2026-10-15.md).
The earlier 3.1 image remains held after missing aperture and a blocked shutter,
with normal shutdown. This candidate repairs a reproduced first-window receive
loss, restores stock lens ID 234 as a compatibility control and adds bounded startup/
handshake diagnostics. Whether it fixes the physical A7C II failure is unproven.

The subsequent [offline hardening pass](../../../docs/firmware-hardening-2026-10-15.md)
reproduces malformed-frame admission and padded short-message operand defects
in this frozen source. Its tested frame gate is a development overlay, not part
of this image. 3.2 remains an unqualified diagnostic candidate; no new camera
success or failure has been reported.

| Property | Value |
| --- | --- |
| Upstream base | `d52ed06cc449918f938e0695fbf29a0c4141f2b2` |
| Loader / camera version | 3.2.0 / BCD 0x32 |
| Image | 20,480 bytes, `[0x5000,0xa000)` |
| SHA-256 | `e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df` |
| Initialized ROM end / margin | `0x9aac` / 340 bytes before diagnostics |
| Diagnostic storage | `[0x9c00,0xa000)`, sixteen 64-byte pages, no runtime erase |
| Static RAM / reserved stack | 3,332 / 8,192 bytes; high-water unmeasured |
| Lens / aperture | Fixed original Contax Zeiss 50mm f/1.4; actual iris unknown |
| Runtime profile row | None; other/edited profiles rejected |

The servo, focus mapping/prediction, homing/parking algorithms and board pin
configuration remain upstream. Diagnostic flash writes are deferred until an
incomplete handshake is quiet, no-body startup stalls, UART is shut down, or a
guard faults. Early breadcrumbs otherwise remain in RAM. A blank log cannot
identify where an early power cut or unguarded CPU failure occurred.

Validation covers 12 current first-window cases, 11 frozen-3.1 failures, eight
retained upstream host outcomes, bounded log storage/failures, nine compiled ARM
writer cases, seven decoder cases and 53 Swift tests. USB byte verification and
camera operation remain pending for this image. Older firmware and original stock
recovery are unchanged.

See [design and reproduction](../../upstream-diagnostic/README.md),
[all upstream source changes](../../upstream-diagnostic/upstream-changes.patch),
[manifest](contax-zeiss-50-f1-4.manifest.json),
[evidence](../../../docs/evidence/upstream-32-startup-diagnostic-2026-10-15.md) and
[camera/log procedure](../../../docs/upstream-startup-diagnostic-test.md).

Use **`prepare-startup` / `apply-startup`** for this candidate. Historical
`apply-upstream` selects held 3.1; `apply-af` selects held 3.0. App 0.15/build 19
offers a separate **Install Startup Diagnostic 3.2.0** action in USB tools. The
October 15 upload followed a separate explicit owner request; byte verification
and the single camera cycle/log retrieval are staged separately.
