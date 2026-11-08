# Development

The macOS 0.29 bank integration adds an experimental migration/selection flow for
unchanged firmware 4.8. The first install/switch is explicitly acknowledged and
normal switches require verified transport evidence. It has not been exercised
on hardware. See [the workflow and CLI commands](bank-migration-2026-11-07.md).
The older offline-only preparation descriptions below record the earlier stage.

The firmware is C; the native companion is SwiftUI/AppKit with Swift IOHID.
Use macOS 14+ with Xcode command-line tools and Python 3.9+.

Shared firmware lives in `firmware/core/`; LM-EA9 hardware source and build rules
live in `firmware/targets/lm-ea9/`. The builder assembles an isolated flat source
directory, preserving the working source bytes and link order.

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
# Separate offline 4.7 profile-personalization template:
python3 scripts/build-firmware.py --lens-profile-template --output artifacts/private/my-47-template
# Editable custom recipe, with an unpublished version:
python3 scripts/build-firmware.py --config firmware/configurations/contax-50-f14.example.json \
  --output artifacts/private/my-custom-firmware
python3 scripts/test-firmware-config.py --build artifacts/private/my-custom-firmware
make test
make app
```

The builder validates every working source hash, performs a clean release build,
checks flash/RAM bounds, excludes diagnostic/baud-switch symbols, and verifies
that the default result matches the immutable 4.5 image. Motor/peripheral units
retain their original `-O2`; the remaining units use `-Os`. No build command
accesses the adapter. Build evidence and logs stay in the new output directory.
Custom mode records the chosen target, edited source and generated lens metadata
instead of requiring baseline source hashes. It never replaces a published image
or adds one to the uploader. [Customization guide](customization.md).

`make app` creates `dist/OpenLensAdapter.app` and `dist/ea9ctl`, signs and verifies
both locally, and verifies reference-photo digests before packaging. Photos
remain local assets with tracked credits. This is not a notarized distribution.
The icon is an original Opus 5.5 Swift/AppKit drawing, regenerated during packaging.
Its source and provenance are in [branding](../assets/branding/README.md).

## Profile-bank experiment

4.8.0 is a separate offline sparse package. It keeps existing upper-flash data
out of its segments and is not admitted to the updater. Build and exercise its
actual portable C and protocol paths without USB:

```sh
make test-profile-bank
python3 scripts/build-profile-bank.py --output artifacts/private/my-bank
python3 scripts/test-profile-bank.py --build artifacts/private/my-bank --output artifacts/private/my-bank-tests
# Custom bank: copy the inventory, choose a zoom focal length if including it,
# and use an unpublished version. Name payloads must fit 63 ASCII characters.
python3 scripts/build-profile-bank.py --inventory /absolute/path/my-lenses.json \
  --version 4.9.1 --default-profile contax-zeiss-50-f1-4 --output artifacts/private/my-custom-bank
```

The standalone selection planner accepts snapshots from this bank format only;
it cannot read or write the adapter. It validates the package and refuses a
foreign metadata extension. Its output contains private metadata:

```sh
python3 scripts/plan-profile-selection.py --package artifacts/private/my-bank \
  --journal /absolute/path/private-settings.bin --metadata /absolute/path/private-metadata58.bin \
  --profile-id contax-zeiss-50-f1-4 --output artifacts/private/my-selection-plan.json
```

The current adapter does not contain this journal. These commands do not make
the experimental metadata allocation or installation path hardware-qualified.
See [design, storage formats and remaining gates](profile-bank-2026-11-07.md).

## Offline app preview

```sh
open -n -a "$PWD/dist/OpenLensAdapter.app" --args --preview connected
# Other fixtures: disconnected, reconnect, wide, dark
```

Preview creates isolated temporary state and replaces USB discovery with a
fixture. Every USB action is disabled. Normal app state, stock recovery keys
and unit backups are never used by a preview. Do not remove the preview guard
or use real device identifiers in fixtures.

## Changes

Keep 4.5 byte-for-byte as the working reference. New camera behavior gets a
new version/image/digest and its own tests and owner-coordinated camera check.
4.6 is installed and byte-verified; the owner reports improvement after an initial
hunting report involving a substituted heavier lens. The camera check is incomplete.
The small legacy compatibility catalog
validates archived journals only; it cannot create retired write plans.
[Architecture](architecture.md) · [USB workflow](usb-protocol.md) · [Archive](history.md).
