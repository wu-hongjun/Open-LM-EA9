# Upstream C AF 3.8 — homing-query readiness, fixed 50mm f/1.4

Prepared offline October 19, 2026. The separately authorized
[upload and strict byte verification](../../../docs/evidence/upstream-38-upload-2026-10-19.md)
passed after physical reconnect, including an independent full-image/protected-
data audit. **Camera acceptance subsequently failed; further trials are held.**
The owner reports hunting and apparent focus for one photo, then a motor reset
and no further photos; shutdown was normal. Read-only logs identify
`home-drive-unsettled` and no initialized AF-servo snapshot. Code/protected data
are unchanged; physical homing and the shutter-block cause remain unresolved.
[Camera evidence](../../../docs/evidence/upstream-38-camera-failure-2026-10-20.md).
The prior 3.6/3.7 camera-failure holds remain in place.

The operand-only optical query worker now runs before foreground polling even
when homing has not completed. It can answer after motion inhibition, while
retaining handshake, abort, shutdown, session and finite queue gates. Motor
inhibition and false readiness remain intact. No automatic homing retry or
reference reset is added. The drive, settle and shared poll-budget failure
branches gain distinct diagnostic codes 17, 18 and 19, respectively.

The upstream C controller, motor limits, coordinate origin, optical maps,
capture/status ownership, shutdown sequence and aperture policy remain those
of 3.7. REA original-instruction replay supports retaining post-capture silence
until ordinary readiness re-arms status; no separate capture/shutdown defect
was reproduced. Version BCD changes to `0x38`. The exact production delta is
[three files](from-37.patch): `main.c`, `startup_trace.h`, and `emount.h`.

| Artifact | SHA-256 |
| --- | --- |
| 20,480-byte application | `8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9` |
| Manifest | `be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0` |
| Delta from frozen 3.7 | `215f5cdb1070e3ff412db0551e0cbf7693e8f8f2611ceeb003e477190fce945a` |

Loaded code/data ends at `0x9ab0`, leaving 336 bytes before the complete
`[0x9c00,0xa000)` diagnostic tail. Static RAM is 3,044 bytes; reserved stack is
8,192 bytes. Compiled analysis gives a conditional 1,516-byte stack envelope,
with no measured high-water or physical timing. Logs remain append-only,
sixteen 64-byte pages, with no runtime erase; missing records cannot locate a
hang. All 1,024 diagnostic bytes in this prepared image are erased.

Lens ID is 234; nominal reported AV is 4352 (f/1.4). **Actual iris: Unknown**;
only the physical lens ring sets it. This is the original fixed 50mm build with
no runtime profile row; library edits remain local. No new exposure policy is
introduced in this milestone.

App 0.21.1/build 28 marks 3.8 held and disables ordinary readiness installation.
`prepare-readiness-upstream` prepares this exact image offline;
`apply-readiness-upstream` remains a separately coordinated USB action. Earlier
commands, images, pins and original stock recovery remain preserved. No
hardware action is authorized by running a build or test script.

[Evidence and limits](../../../docs/evidence/upstream-38-readiness-2026-10-19.md) ·
[Build/test prerequisites](../../upstream-hardening/next38/README.md) ·
[Held test/log procedure](../../../docs/upstream-readiness-test.md)
