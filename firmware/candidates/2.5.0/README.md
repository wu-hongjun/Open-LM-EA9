# AF 2.5.0 — Contax Zeiss 50mm f/1.4

**Audit amendment: hold this frozen candidate from hardware installation.**
Independent documentation review found that message `0x34` has unresolved
semantics. The original handler proves a request-word echo, not that the word
is aperture; the 2.5 override is therefore an unqualified protocol experiment.
The regression establishes the chosen implementation policy, not an exposure
repair. Preserve these binaries and pins for diagnosis. The
[aperture design audit](../../../docs/audits/aperture-protocol-design-2026-10-11.md)
defines the baseline for the next separately versioned candidate.

Prepared and tested offline. **Not uploaded or camera-qualified.** This separate
candidate implements a proposed fixed-aperture reply policy and repairs the reproduced 2.4
completion counterexamples. The exact cause of the owner's stock exposure
failure remains unproven. Camera metering, aperture display and optical AF must
still pass acceptance; the missing earlier photograph does not block this work.

| Property | Value |
| --- | --- |
| Loader / camera version | 2.5.0 / BCD 0x25 |
| Application range | `0x5000..<0xa000`, 20,480 bytes |
| Profile | `0x9f00`, 256-byte CRC-protected version-1 row |
| Lens | Contax Zeiss 50mm f/1.4; fixed declared f/1.4 |
| Physical iris | Unknown to firmware/app; set with the lens ring |
| Template SHA-256 | `448f827b4766f9ecb96c470d48d706650eb30d2fc41aea620369e22989d714c7` |
| Personalized image SHA-256 | `febfa9ff411af46bff225633984e84d4d5ff6d10580514a5bdf429e76f719522` |
| Profile SHA-256 | `5ba55741d3f45b842e19630621c284ed56a1b4a905c6794b8551993529be9340` |

Native `ea9ctl prepare-af` and Python personalization produced identical images.
The [adjacent manifest](contax-zeiss-50-f1-4.manifest.json) and
[build manifest](../../../docs/evidence/af-refined-build-manifest-2026-10-11.json)
record the pinned inputs. See [implementation and validation](../../../docs/evidence/af-25-candidate-2026-10-11.md).

App 0.8.0/build 11 and the CLI offer 2.5 through an explicit experimental AF
installation action. Normal profile changes preserve the verified installed
variant. Older templates, the frozen 2.4 image and stock 1.8 recovery remain
unchanged. The application limit, protected-gap checks, same-unit backups,
durable journal and physical reconnect requirement are unchanged.

```sh
python3 scripts/build-firmware.py --variant refined-af
./scripts/swift-local.sh test
python3 scripts/test-firmware.py --af
tools/rea-analysis/venv/bin/python scripts/test-refined-candidate.py --output /new/regression-directory
./scripts/build-macos-app.sh
# Create the output directory first; the CLI refuses existing output images.
dist/ea9ctl --state-directory /new/profile-state prepare-af contax-zeiss-50-f1-4 /new/50mm.bin
```

No hardware reports are sent by this preparation sequence. Installation is a
separate operation after confirming the adapter is on the USB cap and the
updater is closed. Verify after physical reconnect before camera use. Start
the camera check with MF, A mode and physical f/1.4; record the actual camera
f-number and exposure, then startup/idle/shutdown. Test one bounded AF-S attempt
only after the initial lifecycle is normal. A future saved image helps EXIF and
quantitative comparisons, but an owner-reported failure is sufficient to fail
acceptance. Keep the [stock recovery bundle](../../recovery/stock-1.8.0/README.md)
and its separate private key available.
