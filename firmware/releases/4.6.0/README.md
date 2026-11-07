# Wider aperture candidate 4.6.0

Prepared offline at the owner's request for **reported f/1.2–f/22**, starting
at f/2. The working [4.5.0](../4.5.0/README.md) remains unchanged and available
for direct rollback. The owner authorized installation on November 7, 2026;
upload and strict reconnect verification passed. The owner initially reported
more hunting, then improvement, and disclosed a heavier 35mm Distagon substitution.
This is not a controlled Biotar regression result. Remaining camera observations
are pending. 4.5.0 remains the working baseline.
[Installation record](../../../docs/evidence/biotar-46-install-2026-11-07.md).

The builder changes only `EM_APERTURE_MAX` from `0x1200` to `0x1080` and
`EM_APERTURE_MIN` from `0x1800` to `0x1900` in its build copy of `emount.h`.
These encode the standard marked endpoints f/1.2 and f/22. The initial value
stays `0x1200` (f/2). Declared range, aperture descriptors, nameplate and accepted
request bounds derive from those constants. No motor, focus, handshake,
completion, timing or capture/shutdown code changes.

The Biotar's **nominal lens specification stays 58mm f/2** in the native app.
The wider camera range is virtual reporting, not a physical lens capability.
Choosing f/1.2 cannot make an f/2 iris open wider. The lens ring still controls
the iris, its position remains unknown to the adapter, and selections reset
at boot/fresh session. The camera may issue automatic aperture requests too.

- Image: [biotar-wide-aperture.bin](biotar-wide-aperture.bin), 20,480 bytes.
- SHA-256: `feeef5558f053f150923791af935953df112350519e08bad86712fde6901c318`.
- [Manifest](manifest.json) records exact source and image hashes.
- Repeated clean builds match, including the simplified release-only make rules.
- Production-path aperture tests cover all 65,536 operands and their exact
  range acceptance, descriptors, replies/status, malformed frames, fractional
  values, window padding, deferred TX publication and shutdown/new sessions.
  Both deliberately broken controls fail at their expected assertions.
- Broad protocol, servo simulation, focus mapping/distance and startup tests pass.

```sh
python3 scripts/build-firmware.py --wide-aperture --output artifacts/private/wide-build
python3 scripts/test-firmware.py --build artifacts/private/wide-build \
  --output artifacts/private/wide-test
```

The native installation path admits only an exact fresh 4.5 backup after the
existing same-unit qualification. It preserves the shared lock, pre-upload
backup/journal, bounded pages and mandatory physical reconnect. Native tests
reject altered source bytes and verify direct 4.6 → 4.5 rollback admission.
A separately authorized upload and full-image/protected-data verification have
passed; the camera check remains pending. The broader advertised maximum can affect the
body's optical/metering assumptions; saved exposure, AF, capture and shutdown
must be checked on the real camera. No factory parity is claimed.
