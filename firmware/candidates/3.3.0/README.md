# 3.3.0 — upstream C hardening, Contax Zeiss 50mm f/1.4

**Prepared offline; not uploaded or camera-qualified.** Eleven Astra lanes
reviewed request ownership, shutdown, homing, factory contracts, transport,
motion, aperture, diagnostics, footprint, integration and the Mac host.
[Integration evidence](../../../docs/evidence/upstream-33-hardening-2026-10-15.md) ·
[All lane reports](../../../docs/audits/astra-hardening-campaign-2026-10-15.md).

| Property | Value |
| --- | --- |
| Upstream base | `d52ed06cc449918f938e0695fbf29a0c4141f2b2`, frozen 3.2 inputs |
| Loader / camera version | 3.3.0 / BCD `0x33` |
| Image | 20,480 bytes, `[0x5000,0xa000)` |
| SHA-256 | `adc4b5de9a717b1a573425006ef565962bf5c56ab2233a4eca9192feb7ad11cd` |
| Code plus initialized-data end / margin | `0x9a68` / 408 bytes before diagnostics |
| Diagnostic storage | `[0x9c00,0xa000)`, sixteen append-only 64-byte pages; no runtime erase |
| Static RAM / reserved stack | 3,076 / 8,192 bytes; physical high-water unmeasured |
| Largest compiler-reported function frame | `em_transmit`, 304 bytes; not total call-chain/ISR stack |
| Lens / aperture | Original fixed 50mm f/1.4 profile, lens ID 234, nominal AV 4352 |
| Physical iris / runtime profiles | Actual aperture Unknown; no runtime profile row |

This release retains the upstream C controller and focus mapping, adding full
frame admission, immutable request ownership, priority shutdown, session-tagged
motion, success-only homing readiness, guarded pin remux and bounded peripheral
work. Cross-lane tests found and corrected stale request/readiness publication.
Factory evidence rejects a blanket ordinary-reply sequence rewrite. Ordinary
stored replies preserve their template sequence; status and raw capture retain
their respective audited rules. No factory PID or guessed physical origin was
transplanted.

Shutdown deliberately inhibits new motion without a new parking drive. Homing
can fail/cancel without claiming ready, requires fresh work to retry cancellation,
and remains limited to two attempts per boot. Stationary feedback does not prove
physical infinity. Optical tables retain the baseline's rescaled donor curve,
which is not a measured Contax optical calibration. Exposure, focus reliability,
physical timing and clean capture/shutdown on A7C II remain unqualified.

Trace v2 keeps first 24 and latest 24 RAM events, writes a summary first, and
persists only after UART shutdown or terminal failure. Battery removal can leave
blank logs. The offline decoder separately pins this image, manifest and immutable
prefix; **initial USB verification still requires the complete pristine image,
including all blank diagnostic pages**.

App **0.16.0/build 20** offers **USB tools → Install Upstream Hardening 3.3.0**.
The explicit CLI commands are `prepare-hardened-upstream` and
`apply-hardened-upstream`. `prepare-startup`/`apply-startup` still select 3.2;
`prepare-upstream`/`apply-upstream` still select held 3.1; AF commands retain 3.0.
Other or edited profiles fail before upload.

The adapter's previous 3.2 upload is still pending owner-confirmed reconnect and
strict verification. This offline release does not resolve that transaction.
Flash separately after coordinating that gate; do not discard its journal.
See [future camera/log procedure](../../../docs/upstream-hardening-test.md),
[build reproduction](../../upstream-hardening/README.md),
[manifest](contax-zeiss-50-f1-4.manifest.json) and
[complete source delta from 3.2](from-32.patch).
