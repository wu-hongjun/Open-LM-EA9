# AF 2.6.0 — Contax Zeiss 50mm f/1.4

**Historical candidate; superseded by AF 2.7 after the overnight audit.**
The [audit](../../../docs/audits/night-firmware-correctness-2026-10-12.md)
reproduced Stop-queue overflow and repeated-target budget faults. The original
binary, pin and evidence remain unchanged; do not select it for new tests.
It had been prepared offline for a separately coordinated upload and camera test. The
adapter was disconnected for this milestone. No USB reports or uploads were
performed; A7C II exposure, aperture display and optical AF remain unqualified.

This candidate implements the [audited aperture design](../../../docs/audits/aperture-protocol-design-2026-10-11.md):
known aperture channels use a fixed declaration, while unknown `0x34` returns
the stock opaque operand echo. A request without both operand bytes is rejected
instead of treating checksum bytes as data. The original legal request grammar
remains unresolved; the minimum bound is not an exact-length prescription.
The AF completion fixes from 2.5 are retained unchanged. Frozen 2.5 stays held
and is preserved for diagnosis.

| Property | Value |
| --- | --- |
| Loader / camera version | 2.6.0 / BCD 0x26 |
| Application range | `0x5000..<0xa000`, 20,480 bytes |
| Profile | `0x9f00`, 256-byte CRC-protected version-1 row |
| Lens declaration | Contax Zeiss 50mm f/1.4, fixed nominal f/1.4 |
| Physical iris | Unknown; set manually on the lens |
| Template SHA-256 | `276a134db2db04e4ea41e6bfb622e0b4f3c5421a6e3bfb6e40428cfce07fe265` |
| Personalized image SHA-256 | `1447e37e9bd528c072ace96a23449e7399eb011393e78202de907966d69053d6` |
| Profile SHA-256 | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340` |

The original 0.9.0 native preparation and Python personalization produced identical bytes.
See the [image manifest](contax-zeiss-50-f1-4.manifest.json),
[build inputs](../../../docs/evidence/af-audited-build-manifest-2026-10-11.json),
[implementation and verification](../../../docs/evidence/af-26-candidate-2026-10-11.md)
and [camera procedure](../../../docs/af-s-test.md).

At that milestone, app 0.9.0/build 12 and CLI explicit AF installation selected 2.6.
The current app selects 2.7; historical personalization requires an explicit
Python `--variant audited-af`. Normal Device
dropdown changes preserve the verified installed variant. The app displays
**Actual aperture: Unknown**; its numeric f-number is declared camera metadata.
Select this lens once and operate the physical ring without editing metadata
for every stop-down. This workflow still requires camera qualification.
Retained stock optical rows are not a measured Contax calibration; `pl[46]`
tracking the declared maximum is an explicit compatibility hypothesis.

Reproduce offline from the project root with the documented dependency caches:
The oracle/negative-control tests also require the retained Git history
containing original commit `7efac6b`; a full repository clone includes it.

```sh
python3 scripts/build-firmware.py --variant audited-af  # Verify the frozen resource.
tools/rea-analysis/venv/bin/python scripts/test-audited-candidate.py --output /new/frozen26-results
# Current metadata preparation is still offline; explicit Python selects frozen 2.6.
dist/ea9ctl --state-directory /new/profile-state prepare contax-zeiss-50-f1-4 /new/metadata.bin
python3 scripts/prepare-af.py /new/metadata.bin /new/50mm26.bin --variant audited-af
```

The build fits the existing application/profile boundary exactly: initialized
code/data ends at `0x9f00`. Further growth requires code-size reduction rather
than expanding into retained flash. No diagnostic flash writers or legacy servo
are linked. Stack high-water and physical timing remain unmeasured.

Keep the [original stock 1.8 recovery bundle](../../recovery/stock-1.8.0/README.md)
and its separate private key available. Installation will use the backed-up
native path after confirming the USB cap/updater prerequisites, followed by
physical reconnect and strict byte verification. Camera use follows readback:
loaded-lens MF lifecycle/display, saved exposure at physical f/1.4 and f/4 in
A/P/Auto without changing the declaration, then bounded AF-S. A reported failure
fails acceptance even without a retained photograph. A 2.6-to-stock round trip
has not been performed; historical restoration evidence remains unchanged.
