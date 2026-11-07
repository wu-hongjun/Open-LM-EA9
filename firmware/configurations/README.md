# Build configurations

Copy `contax-50-f14.example.json` and edit its lens name, focal length (mm × 10),
nominal widest aperture and camera-reported aperture values. The nominal lens
specification is distinct from the selectable reporting range; this adapter has
no physical iris actuator or aperture-ring sensor.

The example is an **offline, unqualified 4.8.0 recipe**, not a new release.
Its version must change if that version is published later. Working 4.5.0 and
prepared 4.6.0 retain their separate default build commands and immutable images.
See [the customization guide](../../docs/customization.md) for commands and field
encoding. Lens library JSON in `profiles/` is preserved independently.
