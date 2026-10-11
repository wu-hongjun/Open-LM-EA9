# AF 2.4.0 — Contax Zeiss 50mm f/1.4 factory baseline

This is a **prepared offline candidate**, not an installed or camera-qualified
firmware. It uses independently implemented factory 1.8 target/speed/PID/Stop/
completion/callback semantics behind bounded hardware and protocol policies.
The [design](../../../docs/reverse-engineering/factory-af-baseline.md) records
all known differences; the [validation record](../../../docs/evidence/factory-af-baseline-2026-10-11.md)
connects the original-instruction oracle, wrapper checks, app and exact image.
Reduced hunting is the intended comparison outcome, **not a measured result**.

| Property | Value |
| --- | --- |
| Loader / camera version | 2.4.0 / BCD 0x24 |
| Application writes | `0x5000..<0xa000`, 20,480 bytes |
| Profile | `0x9f00..<0xa000`, CRC-protected 256-byte version-1 row |
| Lens metadata | 50mm, fixed nominal f/1.4, Contax Zeiss name, revision 1 |
| Actual iris | Unknown; set manually on the lens |
| Template SHA-256 | `db9f9f3575ededbd38cc2366eb9efea15d2af6f43df5ee7b6a67a2e500fb6cdf` |
| Personalized image SHA-256 | `c54739a7930cdf4bc12f395a86d38fde6819633b3420821a6b51d8e0704bf6df` |
| Hardware reports during preparation | 0 |

The [adjacent manifest](contax-zeiss-50-f1-4.manifest.json) records profile and
image digests. The [build manifest](../../../docs/evidence/af-factory-build-manifest-2026-10-11.json)
pins source and toolchain inputs. Native `ea9ctl prepare-af` and Python
personalization produce identical bytes for the seeded profile.

Reproduce offline after restoring the documented photo/dependency caches:

```sh
python3 scripts/build-firmware.py --variant factory-af
./scripts/build-macos-app.sh
dist/ea9ctl --state-directory /new/local/profile-state prepare-af \
  contax-zeiss-50-f1-4 /new/output/50mm.bin
```

Alternatively prepare a metadata image using `ea9ctl prepare`, then run
`scripts/prepare-af.py METADATA_IMAGE NEW_OUTPUT --variant factory-af` to save an
adjacent manifest. Output paths must be new. The packaged uploader admits its
own digest-pinned template and a validated profile, not arbitrary external files.

Original stock 1.8 currently remains on the owner's adapter. Its full application
slot matches the original backup, while strict native restoration verification
remains flagged for the saved-motion-record change after camera use. No guard
has been waived and no 2.4 upload occurred. Resolve that transaction and physically
reconnect before a further device operation. Follow the [AF-S runbook](../../../docs/af-s-test.md)
for separately requested upload, immediate USB reconnect/readback, matched stock
comparison, lifecycle observations and stop conditions.

The fixed camera f-number does not operate or lock the iris. Manual stopping
down remains possible; the report/EXIF can differ from the physical setting.
F-- on the camera is not established. Keep the [original 1.8 recovery bundle](../../recovery/stock-1.8.0/README.md)
and its separate private key. Recovery and frozen 2.0–2.3 resources remain unchanged.
