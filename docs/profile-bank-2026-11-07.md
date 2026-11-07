# Profile bank and persistent selection — offline milestone

The experimental 4.8.0 package implements a bank and a 16-row wear-leveled
selection journal on top of the pinned working C source and 4.6 aperture range.
It has not been uploaded, camera-tested or admitted to the native updater.
No adapter discovery, USB reports, motor operation, updater launch or canonical
Application Support changes were performed for this milestone.

The existing app still labels its 4.7 fallback as a full firmware update. Its
dropdown remains local. There is no silent fallback from a settings operation
to reflashing, and no new USB command is exposed by these changes.

## Modules and application behavior

| Module | Responsibility |
| --- | --- |
| firmware/features/profile_bank/profile_bank.c | Portable bank validation, journal scanning/commit, boot request consumption |
| firmware/targets/lm-ea9/profile-bank/profile_nvm.c | SAMD21 geometry/lock/address checks, SRAM command execution and bounded polling |
| firmware/targets/lm-ea9/profile-bank/profile_layout.h | Target-specific experimental flash ownership |
| firmware/features/profile_bank/profile_runtime.c | Apply committed optical metadata before motor, sensor and E-mount initialization |
| scripts/profile_bank.py | Independent host codec and offline selection planner |
| scripts/build-profile-bank.py | Pinned-source overlays and immutable sparse-package reproduction |
| scripts/plan-profile-selection.py | Write a private proposal; cannot open a USB device |

The bank contains the seven configured prime/macro profiles from the owner's
inventory, with Biotar 58mm f/2 as default. The 28–70mm zoom stays in the library
but is omitted from this bank until its actual focal length is supplied. No
zoom position is invented. A custom inventory with an explicit active focal
length and a name of at most 63 printable ASCII characters can include it.
The legacy Biotar profile ID is retained.

Each committed selection sets focal length, startup reported aperture and the
64-byte name reply. The actual production responder then builds its usual focal
and minimum-focus fields. The Sony dial retains f/1.2–f/22 reporting and volatile
camera-aperture behavior. The physical iris remains unknown and controlled by
the lens ring. Motion tuning, lens identity, AF/servo/homing, capture/shutdown,
750 kbaud, optical tables and protocol handlers are inherited. This is not a
heavy-lens tuning change or a calibrated optical model for each lens.

Bank/setting validation and a pending journal commit occur after clocks/delay
initialization, before PA16 is raised, motor/sensors are initialized or bus
interrupts are installed. Thus no flash write runs during AF/capture. This adds
startup work and, for a new request, NVM latency; camera acceptance of that
latency remains untested. An invalid bank or missing/ambiguous committed setting
halts before enabling the motor; it does not erase unknown data or silently
guess a lens. A failed request commit retains the previously loaded setting for
that boot and leaves the request pending. A fully programmed record with a lost
completion indication may be recognized on the next boot.

## Memory ownership and installation boundary

The original same-unit backup contains 20,529 non-erased bytes in
0xa000–0x10000, including immediately above the current application. All bytes in
0x10000–0x20000 were erased in that historical backup. That is evidence about
one saved image, not authorization to assume a newly connected adapter is blank.

The package therefore has explicit, noncontiguous segments:

| Range, end exclusive | Use |
| --- | --- |
| 0x0000–0x5000 | Existing loader, metadata, stock saved records; preserved |
| 0x5000–0xa000 | Base application with small feature hooks and SRAM load image |
| 0xa000–0x10000 | Existing unit data; absent from the package and preserved |
| 0x10000–0x12000 | Feature code/read-only data, padded with erased bytes |
| 0x12000–0x13000 | Immutable 4 KiB bank |
| 0x13000–0x14000 | Dedicated 16 × 256-byte settings rows |
| 0x14000–0x20000 | Unclaimed upper flash; preserved |

The linker keeps vectors at 0x5000, feature functions in the extension and
NVM command/polling routines in SRAM. The builder checks all boundaries and
source pins. It deliberately emits four segments, not a misleading flat image
filled with FF over existing unit data.

**The current loader only uploads sequential application pages.** A future
installer must obtain a fresh qualified full backup, admit the installed source,
prove the proposed extension is blank or already owned by this format, merge the
existing gap bytes exactly, and verify application plus protected data after a
physical reconnect. A sequential upload would still erase/reprogram those gap
rows even when restoring identical bytes; sparse packaging does not avoid that
physical cost or interruption risk. No such installer is enabled here. The
package cannot be selected in the current app or treated as a normal 20 KiB image.
No bootloader, fuse, calibration or user-row modifications are implemented.

## Binary formats

All integers are little-endian; native packed structs are not serialized.
CRC32 is IEEE, with the standard 123456789 test vector. CRC detects corruption;
it is not authentication. Future device admission must bind the complete code
and bank to a known SHA-256 manifest, not trust a CRC or version alone.

The bank has a 64-byte header followed by up to fifteen existing 256-byte
EA9LENS1 records, then FF padding. Header offsets: magic OLABANK1 at 0, schema
u16 at 8, header bytes u16 at 10, record bytes u16 at 12, count/default slot u8
at 14/15, bank bytes u32 at 16, payload CRC/fingerprint u32 at 20, reserved zero
24–59, header CRC over bytes 0–59 at 60. Names, IDs, reserved bytes, record CRCs,
bounds, uniqueness and padding are validated before any selection is applied.
The nominal lens maximum stays distinct from the virtual dial endpoints.

The first 64 bytes of each journal row hold one setting: OLASET1! at 0, schema
u16 at 8, bytes u16 at 10, bank fingerprint u32 at 12, sequence u32 at 16,
consumed request generation u32 at 20, slot u8 at 24, zero 25–55, CRC over
0–55 at 56, DONE at 60. The newest valid integer sequence wins; conflicting
newest sequences fail. Counters never wrap silently. Exhaustion requires an
explicit migration, not an automatic destructive reset.

The next changed selection erases the next row modulo sixteen and programs
exactly one complete 64-byte page with CRC and commit marker in the same program
operation. It never erases the row holding the newest valid setting. Readback
must match before reporting success. A torn target row can be erased and retried
after reset while the previous committed row survives.

Using one page per erased row is deliberate: FF cannot prove a page has never
been programmed, particularly after an interrupted write or the loader's padded
initial image. A separate marker write or blindly appending into FF pages could
exceed the MCU's consecutive-write limit. Rotation spreads erase use across
sixteen rows without relying on that assumption. There are no writes for ordinary
AF/status/capture traffic, aperture clicks, unchanged requests or unchanged boots.
No remaining-life estimate is claimed. The SAMD21 has finite flash endurance;
see the [Microchip data sheet](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU32/ProductDocuments/DataSheets/SAM-D21-DA1-Family-Data-Sheet-DS40001882.pdf)
and [NVM overview](https://developerhelp.microchip.com/xwiki/bin/view/products/mcu-mpu/32bit-mcu/sam/samd21-mcu-overview/peripherals/nvmctrl/).

The hardware port only addresses these settings rows. It checks 128 KiB/64-byte
geometry and the E17A's applicable 8 KiB lock region, refuses locked writes,
requires an erased page, never unlocks storage, preserves PRIMASK/CTRLB, checks
errors and latches a command failure. Command polling has a fixed instruction
budget and runs in SRAM while interrupts are masked. This bounds software
polling; it cannot guarantee recovery from a stuck bus, brownout, failed flash
array or CPU stall. Real NVM timing, power loss and cache behavior need hardware
qualification. Settings-row ownership is a new firmware contract, not a claim
that arbitrary erased flash is safe to use.

## Metadata-only USB investigation

The saved boot prefix SHA-256 is
8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895.
The new offline experiment executes its actual 0x257c dispatcher and 0x0e78
row-merge instructions with synthetic USB/NVM backends:

- One START writes 58 report metadata bytes plus six overread scratch bytes to
  0x4000–0x4040. Its physical footprint is one 256-byte erase and four page
  programs. The remaining row contents are logically preserved in this model.
- With zero later reports, it issues no application write and remains armed
  in state 2 with pointer 0x5000. There is no verified END/disarm/launch command.
- The deliberately unsafe control sends CHECK in that state. It programs the
  CHECK bytes at 0x5000 and advances to 0x5040. That is why no query, retry or
  extra report is allowed after START; physical power cycling must come first.
- Fresh initial RAM state admits CHECK without another write. This models reset
  dispatch only; it does not establish real USB enumeration/reset behavior.

The proposed mailbox uses **only** metadata bytes 32–57: OLAC at 0, schema u8
at 4, bank slot u8 at 5, zero u16 at 6, bank fingerprint u32 at 8, request
generation u32 at 12, zero u32 at 16, CRC over 0–19 at 20, OK at 24. Prefix
bytes 0–31, including firmware version, are preserved. Scratch is never storage.
The application consumes only a valid, correctly bound, newer request; the
cap itself runs the loader, so consumption waits for application/camera boot.

**This field allocation remains experimental.** The original factory backup
has nonblank, nonzero data in that proposed area. Complete field ownership
across boot/application paths is not established. The host planner refuses
foreign/invalid bytes instead of overwriting them. An explicit migration and
full invariance checks are still required. The existing apps have no transmitter
for this path. Software instruction evidence alone does not qualify zero-page
START, lost-ACK handling, reconnect behavior or field ownership on hardware.

Even if qualified, every USB selection would erase the fixed metadata row once.
The rotating application journal does not remove that hotspot. A true journal-only
USB management service still needs a qualified way to enter the application
through the cap; none is implemented, and the loader is unchanged.

Host planning distinguishes committed selection from a newer request waiting
for camera boot. Selecting that pending slot again is a no-op; selecting the old
committed slot cancels the pending request with a newer generation. It does not
claim that a verified mailbox is already applied to the running camera.

## Reproduction and evidence

    make test-profile-bank
    # Optional original-instruction and compiled ARM tests, using local Unicorn:
    tools/rea-analysis/venv/bin/python scripts/test-profile-nvm-arm.py --build BUILD --output PRIVATE_NEW_ARM_FOLDER
    tools/rea-analysis/venv/bin/python scripts/test-metadata-only-loader.py --output PRIVATE_NEW_LOADER_FOLDER

All output folders must be new and under artifacts/private. The loader test
needs the private pinned boot backup; the bank build/portable tests need only
public sources and the pinned toolchain. See [development](development.md) for
custom banks and [evidence](evidence/profile-bank-2026-11-07.json) for results.

Coverage includes every single-bit bank corruption, every latest-record bit,
322 prefix-cut erase/program boundaries followed by reboot/retry on each of two
banks, uniform 16-row rotation, unchanged/replayed/invalid/exhausted requests,
conflicting records, failed I/O and boot consumption. Eight configured lens
fixtures reach the actual protocol's name/checksum, focal, startup aperture,
dial change and session-reset paths. Three intentionally broken implementations
must fail specific assertions. Compiled Cortex-M0 startup/NVM tests check command
order, address/geometry/lock guards, old-setting fallback, no-op reboot, SRAM
execution while simulated busy, interrupt restoration and flash invariance.

These are software models, including prefix-cut and synthetic page-buffer/
register behavior. They do not cover every analog partial-program outcome,
prove hardware endurance, or establish camera stability or factory parity.
