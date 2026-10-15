# 3.5.0 — upstream C absolute targets, Contax Zeiss 50mm f/1.4

**Prepared offline; not uploaded or camera-qualified.** This extends frozen
[3.4](../3.4.0/README.md) with source-bound target/time fixes and a measured
release-only counter omission. It retains controller gains, optical maps,
protocol ownership, aperture policy, sensor drivers and diagnostic storage.
[Unified evidence](../../../docs/evidence/upstream-35-absolute-2026-10-15.md).

| Property | Value |
| --- | --- |
| Loader / camera version | 3.5.0 / BCD `0x35` |
| Image | 20,480 bytes, `[0x5000,0xa000)` |
| SHA-256 | `04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632` |
| Code plus initialized-data end / margin | `0x9af8` / 264 bytes before logs |
| Diagnostic storage | `[0x9c00,0xa000)`, sixteen append-only 64-byte pages; no runtime erase |
| Static RAM / reserved stack | 3,072 / 8,192 bytes |
| Conditional compiled whole-chain stack envelope | 1,560 bytes; physical high-water unmeasured |
| Lens / aperture | Original fixed 50mm f/1.4 profile, lens ID 234, nominal AV 4352 |
| Physical iris / runtime profiles | Actual aperture Unknown; no runtime profile row |

The new shared `servo_move_from(start,target,...)` entry keeps the resolved
absolute destination and starting sample used by main/predictor. A later sensor
read no longer shifts the internal destination. The controller still reads fresh
feedback before driving. Relative instructions are resolved as before; the
legacy `servo_move_rel` API samples once and delegates to the same control body.
The wrapper is discarded from the linked release because its production callers
now use the shared entry. Gains, target conversion and retarget policy stay intact.

Homing success now requires a post-stillness elapsed sample below the drive or
settle phase cap. A query or encoder operation crossing the cap can no longer
turn an expired phase into HOME_READY. This bounds the acceptance decision by
sampled firmware ticks; it cannot undo a delayed operation or guarantee physical
cutoff at a deadline. Whole-counter-wrap aliases remain explicitly deferred.

The predictor now uses the exact zero quotient for positive unsigned intervals
above INT32_MAX under the admitted-coordinate contract. This removes a signed
conversion error under exceptional synthetic gaps without choosing a new latency
threshold. It preserves existing smoothing, including decay of the old estimate.
Such a gap is not an observed camera failure or a plausible short AF move.

Only the logging-only `em_frame_period_n` increment is omitted in release. Its
sole consumer is an excluded legacy page; actual VD period measurement, I/O and
live startup diagnostics remain. Source review, release/debug parity and linked
symbol checks validate that scope. This saves 16 flash bytes and four static RAM
bytes in the measured composition, retaining the required 256-byte margin.

A shared starting sample changes the initial velocity/guard baseline and removes
one sensor transaction from main-driven motion; physical timing and optical
behavior still require tests. Stationary homing does not prove infinity. Public
captures inspected in this campaign contain no distance-query workload, so they
do not establish real query deadlines or arbitrary-load queue sufficiency.
Factory reconstruction is [partial](../../../docs/reverse-engineering/status-2026-10-15.md);
this remains the upstream controller, not a factory PID transplant.

App **0.18.0/build 22** offers **USB tools → Install Upstream AF 3.5.0**.
Explicit commands: `prepare-absolute-upstream` / `apply-absolute-upstream`.
Earlier commands keep their images. The original unedited 50mm profile is
required. Full pristine image, blank log tail and protected data verification
remain mandatory after physical reconnect; diagnostic prefix matching does not
verify installation.

The uploaded 3.2 transaction remains unresolved pending owner-confirmed physical
reconnect and strict verification. This offline release neither resolves it nor
authorizes another flash. See the [future coordinated procedure](../../../docs/upstream-absolute-test.md),
[build/test instructions](../../upstream-hardening/next35/README.md),
[manifest](contax-zeiss-50-f1-4.manifest.json) and
[complete delta from 3.4](from-34.patch). Prior releases and recovery remain exact.
