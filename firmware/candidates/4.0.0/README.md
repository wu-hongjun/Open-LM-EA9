# AF 4.0 — bounded reference qualification

**Prepared offline; not flashed or camera-qualified.** This candidate is fixed to
original Contax Zeiss 50mm f/1.4 metadata: lens ID 234, nominal AV 4352. Actual iris
position remains unknown; lens-library edits stay local. The version rolls to4.0
because the camera uses a single BCD byte; this does not indicate factory parity.

The [3.9 logs](../../../docs/evidence/upstream-39-camera-failure-2026-10-20.md)
show the drive budget expiring with only 20 of 40 required stillness ticks, followed
by17 consumed requests while reference readiness remained false. Original upstream
C permits settling after the drive cap; the recovered factory conditional routine
also separates drive and released settling. Neither proves a physical endpoint.

This candidate retains the early 40-tick driven qualification path. At the unchanged
300-tick drive cap, a guarded fallback detaches the pins before synchronized PWM
operations, clears stale compares while detached, requires bounded negative travel
and a repeated pre-cutoff anchor, and observes40 released ticks against that fixed
anchor. Any drift beyond 6 counts, stale deadline, cancellation or inhibition fails
closed. The final sampled coordinate must qualify before it becomes the software
reference, with no unchecked second raw read. Capture/shutdown ownership and the
upstream AF controller remain unchanged; no readiness or completion is fabricated.
Stationary stiction can still resemble an endpoint. This is an experimental software
reference policy with weaker driven corroboration, not measured physical infinity.

| Artifact | SHA-256 |
| --- | --- |
| [20,480-byte image](contax-zeiss-50-f1-4.bin) | `06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae` |
| [Manifest](contax-zeiss-50-f1-4.manifest.json) | `8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc` |

[Exact delta](from-39.patch) changes main, encoder and motor helpers, their headers,
and camera version. Code/data end 38956 (`0x982c`), margin 980 before diagnostics;
static RAM 3040, stack reserve 8192. The diagnostic tail is still1024 erased bytes,
16 append-only pages with no runtime erase. Failed-home tag 0x40 is decoded only
under the 4.0 image/manifest registry pins; all older layouts remain strict.
Two additional units use the existing `-Os` policy to retain the 256-byte flash floor.

[Build/test workbench](../../upstream-hardening/next40/README.md) ·
[Integrated evidence](../../../docs/evidence/upstream-40-reference-2026-10-20.md) ·
[Separate upload and one-cycle procedure](../../../docs/upstream-reference-test.md).

All historical images, digests and original stock recovery are preserved.3.9 remains
held. Upload, physical reconnect, strict complete-image/protected-data verification
and one owner-coordinated A7C II cycle are separate future steps. Sustained capture,
optical focus, exposure, shutdown and factory parity remain unqualified.
