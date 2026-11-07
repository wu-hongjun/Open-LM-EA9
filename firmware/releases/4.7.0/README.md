# 4.7.0 lens-personalization prototype — offline

This is an interim **full firmware update** path for selecting a library lens in
the native app. It is not a settings-only USB service or multi-lens bank.
The preferred design is [bank plus settings](../../../docs/lens-profile-persistence.md).
No 4.7 image has been uploaded or camera-tested.

The template derives from working-source 4.5 plus the exact 4.6 range overlay.
Its only new firmware behavior reads startup aperture from a separate flash word
instead of folding f/2 into reporting instructions. The host personalizes that
word, the existing focal-length word and the 64-byte lens-name payload.
An encoded profile with CRC occupies the previously blank final 256 bytes;
it is host readback/provenance data, not a bank parsed by the firmware.
Motor, servo, homing, capture/shutdown, UART speed and optical tables are inherited.

- Template SHA-256: 5b5267d8a25e0fbad0de2f5072455dc838bf217e9cbcb602c8985c2d24537344.
- Application: 20,480 bytes, flash 0x5000–0xa000.
- Code/data end: 0x9dd8; profile record: 0x9f00–0xa000.
- Reported range: f/1.2–f/22; startup report derives from the chosen profile.
- The physical iris and currently mounted passive lens are not sensed.
- Manifest offsets come from the ELF symbol/load map, not byte-pattern searches.
- The blank, unpersonalized template is not an installable profile image.

The Swift builder pins the template, validates the profile and modifies only
the specified slots. It validates a readback by reconstructing **all** its bytes
from the template and decoded profile, binding live fields to their record and
rejecting any other code, data or padding change. Zooms require a selected focal
length. The new fields do not calibrate defocus scaling or inherited optical tables.

Upload retains qualified fresh two-pass backup/source admission, shared lock,
durable journal, no reports after START/pages, same-unit physical reconnect,
complete application/protected-data verification and original stock recovery.
Canonical current 4.7 images can switch to another personalized image, or roll
back to the pinned 4.5/4.6 images. Known stock requires existing upload qualification.

Offline tests cover the production protocol, all 65,536 aperture operands,
TX interleaving/IRQ preservation and specific failing controls. Eight profile
fixtures exercise production C startup, focal/name replies, aperture change and
session reset. Ignoring the selected startup word fails the required assertion.
Native tests cover canonicalization, tampering, source admission and verification.
These do not qualify camera autofocus, exposure or stability.

Reproduce without USB:

    python3 scripts/build-firmware.py --lens-profile-template --output artifacts/private/profile-template
    python3 scripts/test-firmware.py --build artifacts/private/profile-template --output artifacts/private/profile-tests
    python3 scripts/test-lens-profile-template.py --build artifacts/private/profile-template --output artifacts/private/profile-runtime-tests

The app prepares personalized images without requiring a compiler on the user's
Mac. A future low-write bank/settings transport requires its own firmware version,
storage layout and qualification.
