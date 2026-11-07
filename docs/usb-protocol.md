# USB cap protocol and workflow

The update cap uses the retained vendor loader through HID. Native `DeviceKit`
implements the inspected descriptor and bootloader checks; the application's
USB path is not a separate firmware management service.

Each report is 64 bytes. CHECK/READ reports begin `95 27 68 18`, with repeated
operation bytes `02 02` or `03 03`. READ carries its little-endian address in
bytes 6–9. CHECK identifies the loader-visible application version. Qualified
reads cover 128 KiB main flash and inspected auxiliary/register windows.

An upload START uses `95 27 68 18 01 01`, followed by 58 metadata bytes. The first
three metadata bytes carry the new USB version. After START, subsequent reports
are raw 64-byte application pages starting at `0x5000`. There is no end marker.
A 20,480-byte image uses one START plus 320 pages, ending at `0xa000`.

**The loader stays armed after upload.** No CHECK, READ, padding, retry or other
report may follow until a physical reconnect. A failed write acknowledgement
also requires reconnect, not an in-session retry. The six loader scratch bytes
at `0x403a..0x403f` are excluded from metadata comparison; all other planned and
protected regions are checked.

The native path requires closed updater, exclusive process lock, qualified
descriptor/boot/geometry, same-unit stock-upload qualification and a fresh
two-pass backup before START. A durable private journal and shared reconnect
marker survive process failure. Verification requires a new connection of the
same unit, another matching two-pass backup, exact image/metadata and unchanged
protected data. Restoring stock uses that adapter's original verified backup.

Current admission: 4.5 accepts pinned stock, 4.4 or 4.6; 4.6 accepts exact 4.5.
4.4 fallback accepts pinned stock, 4.5 or 4.6. Every path checks source bytes,
not just the version number. The offline 4.7 prototype accepts qualified pinned
stock, 4.4, 4.5, 4.6 or canonical personalized 4.7 sources. Its entire resulting
image must reconstruct exactly from the pinned template plus profile, including
all live fields and the profile record. Direct 4.7 → 4.5/4.6 rollback is admitted.
It still uses START plus all 320 pages; it is not a parameter-only operation.
Earlier images have no installation API.

```sh
dist/ea9ctl prepare-camera-aperture NEW.bin  # Offline only
dist/ea9ctl prepare-wide-aperture NEW.bin    # Offline only
dist/ea9ctl prepare-lens PROFILE_ID NEW.bin  # Offline personalized 4.7 image
# Hardware commands are owner-coordinated:
dist/ea9ctl apply-wide-aperture --idle
# Explicit whole-image update, not parameter-only switching:
dist/ea9ctl apply-lens-firmware PROFILE_ID --idle
# Physically unplug/reconnect; keep updater/app closed:
dist/ea9ctl verify --idle
```

Raw dumps, unit identity and keys stay private. Bootloader replacement and
power-loss recovery have not been qualified. The original source studies are
available in the [archive](history.md); current installation evidence is
[here](evidence/biotar-45-install-2026-11-07.md).
