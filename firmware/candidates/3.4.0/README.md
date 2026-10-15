# 3.4.0 — bounded upstream C, Contax Zeiss 50mm f/1.4

**Prepared offline; not uploaded or camera-qualified.** This extends frozen
[3.3](../3.3.0/README.md) with demonstrated query lifetime/retention and numeric
fault-readiness fixes. It retains the upstream C servo, predictor, optical maps,
packet templates and aperture policy. [Evidence](../../../docs/evidence/upstream-34-bounded-2026-10-15.md).

| Property | Value |
| --- | --- |
| Loader / camera version | 3.4.0 / BCD `0x34` |
| Image | 20,480 bytes, `[0x5000,0xa000)` |
| SHA-256 | `fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9` |
| Code plus initialized-data end / margin | `0x9aec` / 276 bytes before logs |
| Diagnostic storage | `[0x9c00,0xa000)`, sixteen append-only 64-byte pages; no runtime erase |
| Static RAM / reserved stack | 3,076 / 8,192 bytes |
| Conditional compiled whole-chain stack envelope | 1,560 bytes; physical high-water unmeasured |
| Lens / aperture | Original fixed 50mm f/1.4 profile, lens ID 234, nominal AV 4352 |
| Physical iris / runtime profiles | Actual aperture Unknown; no runtime profile row |

The query worker captures the session with its dequeue, checks ownership again
before publication, and processes at most four queries per call. It retains
queries when the answer queue is full and runs inside the existing motion/homing
pump without requiring a valid encoder origin. These operand-only conversions
do not sample the encoder or reenter the pump. Finite tests reproduce stale
answers, dropped replies and delayed motion-time replies in controls, then verify
the fix on actual encoded status frames.

The encoder admits software coordinates only within `[-65536,65536]`, checking
before addition. Exceeding this arithmetic capacity retains the last admitted
coordinate and latches existing motor inhibition. It is **not a physical travel
limit or infinity calibration**. A reviewed range certificate covers the fixed
production configuration, target arithmetic, servo and predictor without changing
their normal calculations. Homing now treats any sticky motor inhibition as a
terminal failure; a fault cannot be turned into a new zero or HOME_READY.

Consecutive target/servo encoder reads can still shift the internal relative
servo target outside the advertised optical range. Donor optical tables are not
a measured Contax calibration. Extraordinary time gaps retain an implementation-
defined unsigned-to-signed conversion. Timing, exposure, optical AF, capture,
shutdown and mechanical origin require physical qualification. No factory PID
or guessed compensation was added.

App **0.17.0/build 21** offers **USB tools → Install Bounded Upstream 3.4.0**.
Explicit CLI commands are `prepare-bounded-upstream` / `apply-bounded-upstream`.
All earlier commands retain their original images. Other or edited lens profiles
fail before USB access in the prepare path. Initial installation verification
still requires the complete pristine image, including blank diagnostic pages;
the decoder's prefix check is only for post-camera logs.

Uploaded 3.2 still awaits owner-confirmed physical reconnect and strict
verification. This release does not resolve that journal or authorize a flash.
See the [future coordinated procedure](../../../docs/upstream-bounded-test.md),
[build/test instructions](../../upstream-hardening/next/README.md),
[manifest](contax-zeiss-50-f1-4.manifest.json) and
[complete delta from 3.3](from-33.patch). Earlier releases and recovery remain exact.
