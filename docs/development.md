# Development

The firmware is C; the native companion is SwiftUI/AppKit with Swift IOHID.
Use macOS 14+ with Xcode command-line tools and Python 3.9+.

## Pinned firmware dependencies

The reproducible local toolchain layout is:

- `tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/`
- `tools/firmware-deps/CMSIS_5-5.9.0/CMSIS/Core/Include/`
- `tools/firmware-deps/samd21-dfp-2/samd21a/include/` — Microchip SAMD21_DFP 2.0.4

Official URLs and archive digests are recorded in [build dependencies](../references/build-dependencies.json).
These vendor packages are ignored build dependencies; the device-pack version is
recorded in its `Microchip.SAMD21_DFP.pdsc`. Source/header compatibility fixes
are already in the checked-in firmware. No private scratch checkout or official
firmware dump is needed to reproduce 4.5.

```sh
make firmware
# Explicit output folder; must be new and below artifacts/private:
python3 scripts/build-firmware.py --output artifacts/private/my-45-build
# Separate wider-range candidate:
python3 scripts/build-firmware.py --wide-aperture --output artifacts/private/my-46-build
make test
make app
```

The builder validates every working source hash, performs a clean release build,
checks flash/RAM bounds, excludes diagnostic/baud-switch symbols, and verifies
that the default result matches the immutable 4.5 image. Motor/peripheral units
retain their original `-O2`; the remaining units use `-Os`. No build command
accesses the adapter. Build evidence and logs stay in the new output directory.

`make app` creates `dist/Open LM-EA9.app` and `dist/ea9ctl`, signs and verifies
both locally, and verifies reference-photo digests before packaging. Photos
remain local assets with tracked credits. This is not a notarized distribution.

## Offline app preview

```sh
open -n -a "$PWD/dist/Open LM-EA9.app" --args --preview connected
# Other fixtures: disconnected, reconnect, wide, dark
```

Preview creates isolated temporary state and replaces USB discovery with a
fixture. Every USB action is disabled. Normal app state, stock recovery keys
and unit backups are never used by a preview. Do not remove the preview guard
or use real device identifiers in fixtures.

## Changes

Keep 4.5 byte-for-byte as the working reference. New camera behavior gets a
new version/image/digest and its own tests and owner-coordinated camera check.
4.6 is currently prepared, not flashed. The small legacy compatibility catalog
validates archived journals only; it cannot create retired write plans.
[Architecture](architecture.md) · [USB workflow](usb-protocol.md) · [Archive](history.md).
