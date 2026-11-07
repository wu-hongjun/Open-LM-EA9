# LM-EA9 firmware

[4.5.0](releases/4.5.0/README.md) is the owner-confirmed working baseline on the
A7C II with the Biotar 58mm f/2. `src/` contains its exact pinned C sources.
The reorganized build reproduces the published image byte for byte.

[4.6.0](releases/4.6.0/README.md) is the separate, offline f/1.2–f/22 aperture
candidate. The builder overlays only the two reporting-range constants; the
working sources and 4.5 image stay unchanged. The actual iris remains manual.

```sh
python3 scripts/build-firmware.py
python3 scripts/build-firmware.py --wide-aperture
python3 scripts/test-firmware.py
```

Run from the repository root. Outputs use new private artifact directories;
no command above opens USB. See [development](../docs/development.md).
New behavior requires a new release and native digest pin. Never overwrite an
existing image or silently change the stock recovery.
