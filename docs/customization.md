# Customizing OpenLensAdapter

The [4.8 host workflow](bank-migration-2026-11-07.md) uses a pinned bank. Ordinary
switches change only a slot request, never reflash or rewrite the bank. Local
notes/revision changes are ignored when matching optical fields; changing name,
focal length, nominal aperture or startup report needs a separate bank build.
The unknown zoom position is never inferred.

Use build-profile-bank.py with a copied inventory and an unpublished version
for a custom bank. Current native admission deliberately supports the published
4.8 package only. A new package needs reviewed ProfileBank resource pins/layout,
BankPlan/version admission, packaging and tests before exposing installation.
Run the native-to-ARM byte contract, transaction/fault controls and coordinated
hardware qualification. Do not overwrite 4.8 segments or reuse its transport
proof for changed loader/protocol behavior.

The repository separates three choices: the lens you report, firmware behavior,
and the hardware that runs it. LM-EA9 is the only implemented hardware target.
Working 4.5.0 remains the reference for the owner's A7C II/Biotar combination.

## Your lens

Copy `firmware/configurations/contax-50-f14.example.json` to your own file. Choose
an unpublished three-byte version and `target: "lm-ea9"`. Set:

| Field | Meaning |
| --- | --- |
| `lens.name` | 1–63 printable ASCII characters for the camera's lens-name reply |
| `lens.focalMM10` | Fixed focal length in tenths of a millimeter, 10–10000 |
| `lens.nominalMaximumFNumber` | Physical lens specification, retained as manifest metadata |
| `reportedAperture.maximumAV` | Largest selectable opening, smallest encoded value |
| `reportedAperture.minimumAV` | Smallest selectable opening, largest encoded value |
| `reportedAperture.initialAV` | Value reported at startup and a new session |

Encoding is `4096 + 512 × log2(f-number)`. Configuration values use multiples of
32 (one eighth stop) within 4096–7168; boot must be inside the range. The largest
opening is currently limited to AV 5632 (f/8) because of the inherited nameplate
BCD table. Common display labels are rounded: 4224 → f/1.2, 4352 → f/1.4,
4608 → f/2, 5120 → f/4, 6144 → f/16, 6400 → f/22. Camera commands retain their
fractional values; only configuration endpoints/boot use this grid.

```sh
python3 scripts/build-firmware.py --config firmware/configurations/contax-50-f14.example.json \
  --output artifacts/private/my-custom-firmware
python3 scripts/test-firmware-config.py --build artifacts/private/my-custom-firmware
```

The supplied test checks the example's expected 50mm name/focal length, boot
value, range and real protocol replies under sanitizers, plus invalid-input
controls. Adapt expected values for another lens. These are synthetic body
requests; optical tables and autofocus calibration are inherited, not measured
for the new lens. A zoom needs an explicit fixed reporting choice; this recipe
does not add zoom sensing.

Only the copied `emount.h` constants and name frame are changed by lens
configuration. The builder leaves the checked-in sources and releases untouched.
The output contains `custom-firmware.bin`, the effective configuration, source
and build-rule hashes, target hash, image hash and build log. Both
`cameraQualified` and `uploadQualified` start false. `loaderVersion` is intended
update metadata; the vendor loader stores its version separately from this
application image. The camera's version byte and lens identity stay inherited.

Native Lens Library edits remain local. They do not silently change the build
recipe or upload firmware. The physical iris remains controlled by the lens ring;
the camera dial chooses metadata, and the app cannot read the actual iris.

## Firmware behavior

Edit `firmware/core/` for E-mount framing/status, reported aperture, optical data
or focus mapping. Edit `firmware/targets/lm-ea9/src/` for its board/peripheral and
motor implementation. Use a custom config/new version for any change. Default
build mode requires the working source pins and exact 4.5.0 image; it refuses an
edited baseline. The build copy preserves upstream translation-unit/link order
and the mixed optimization flags that reproduce the working firmware.

Run `make test` against an unmodified baseline and add production-path tests for
behavior changes. The baseline test harness assumes the Biotar profile; use an
isolated custom build for custom tests. Do not repin an existing release to make
a failing test pass.

## Another adapter

Add a directory under `firmware/targets/` with a unique ID. Its `target.json`
selects application/flash/RAM limits, include dependencies, makefiles and ELF.
Replace hardware code and build flags; merely renaming the target does not port
the pinout, timing, motor, encoder, power sequence or bootloader. Core currently
uses the platform interfaces declared by the LM-EA9 headers; port those contracts
or introduce tested interfaces when another real target requires them.

The builder supports the current ARM GNU/SAMD21 dependency layout and contiguous
application format. Extend it explicitly for a different architecture or loader.
The native app's `DeviceKit` transport, descriptors, flash layout, protected-data
checks and recovery qualification must also be implemented for another adapter.

## Native app lens selection

The Lens card can prepare a library profile using the offline 4.7 template. This
changes the name, focal/startup fields and profile record without a compiler,
but its explicit firmware-update fallback still rewrites the complete image.
It is not the low-write profile-bank/settings design. Zooms require a saved
current focal length. [App workflow](app-lens-card-2026-11-07.md).

## Adding a custom image to the app

Custom output is not accepted as an arbitrary flash file. Register a new immutable
image/version/digest and target/profile metadata in `DeviceKit`'s firmware catalog,
bundle the pinned image and extend the exact packaged-resource admission checks.
Add its source/manifest/release notes and protocol tests. Preserve the two-pass
backup, durable journal, same-unit physical reconnect, complete byte verification,
protected data and restore path. Camera qualification is a separate recorded
hardware result; offline tests never establish it.

Keep original unit backups and recovery keys private. Use your own unit's recovery
material; the checked-in stock application is a reference, and encrypted same-unit
recovery requires the original private key. [USB workflow](usb-protocol.md).
