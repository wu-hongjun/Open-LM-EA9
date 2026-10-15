# 3.6.0 — upstream C startup handoff, Contax Zeiss 50mm f/1.4

**Camera acceptance failed; further trials are held.** Upload and strict
verification passed; the owner then reported shutter-press freeze and shutdown
nonresponse. [Failure and surviving logs](../../../docs/evidence/upstream-36-camera-failure-2026-10-15.md).
App0.19.1/build24 disables ordinary installation. The image, manifest and patch
below remain unchanged.

The original offline preparation extends frozen
[3.5](../3.5.0/README.md) with a scoped startup receive-ownership fix.
It retains the upstream controller, gains, optical tables, aperture policy,
motor/sensor drivers, wait budgets and diagnostic storage.
[Unified evidence](../../../docs/evidence/upstream-36-handoff-2026-10-15.md).

| Property | Value |
| --- | --- |
| Loader / camera version | 3.6.0 / BCD `0x36` |
| Image | 20,480 bytes, `[0x5000,0xa000)` |
| SHA-256 | `d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f` |
| Code/data end / margin before logs | `0x9af4` / 268 bytes |
| Diagnostic storage | `[0x9c00,0xa000)`, sixteen append-only 64-byte pages; no runtime erase |
| Static RAM / reserved stack | 3,064 / 8,192 bytes |
| Conditional compiled stack envelope | 1,560 bytes; physical high-water unmeasured |
| Lens / nominal aperture | Original fixed 50mm f/1.4 profile; lens ID 234, AV 4352 |
| Physical iris / runtime profiles | Actual aperture Unknown; no runtime profile row |

Startup previously enabled EIC interrupts before calling the falling-edge
receive path in foreground to rescue the first window. A rising EIC interrupt
could reset the buffer during that copy. The new EIC setup/start boundary defers
only EIC delivery until rescue/reset finishes. UART and SysTick remain live;
PRIMASK is unchanged and pending EIC state is retained. A global interrupt-mask
proposal was rejected because it could delay a final UART byte past rescue.

Two legacy-only RAM snapshots of the live RX byte counter are omitted under
`EA9_NO_LOG`; their only readers are excluded logging pages. The live counter,
MMIO, emitted frames and startup diagnostics remain active. ARM preprocessing
and complete synthetic trace/wire comparisons verify that scope. This retains
the established 256-byte flash-margin floor without shortening logs or waits.

Independent tests cover 287 asserted cases, including 41 against exact final
3.6 source and failing controls. The compiled review verifies EIC disable,
barriers, rescue/reset, then enable, with 29 negative evidence controls. Repeat
builds and the unified firmware/decoder checks pass; all 53 Swift tests pass.
These contracts do not qualify peripheral timing, exposure, capture, shutdown
or optical AF. Edge coalescing and receive-boundary limits remain documented.

App **0.19.0/build 23** offers **USB tools → Install Upstream AF 3.6.0**.
Explicit commands: `prepare-handoff-upstream` / `apply-handoff-upstream`.
Earlier commands retain their images. Only the original unedited 50mm profile
is supported. Actual iris stays Unknown; factory reconstruction remains partial.

The prior 3.2 transaction and this 3.6 installation passed strict verification
after separate owner-confirmed physical reconnects. Camera failure does not
invalidate those byte comparisons. Do not repeat 3.6 trials. See the
[held coordinated procedure](../../../docs/upstream-handoff-test.md),
[build/test workbench](../../upstream-hardening/next36/README.md),
[manifest](contax-zeiss-50-f1-4.manifest.json) and
[complete delta from 3.5](from-35.patch). Prior releases and stock recovery remain exact.
