# A7C II photo metadata check — October 10, 2026

The owner reported that the adapter's autofocus motor did not seem to move and
provided `DSC02856.HIF` from the camera's external volume. Motor motion is disabled
in the uploaded metadata-only firmware; this observation matches the intended
test behavior and does not qualify autofocus.

The original file was read with native macOS ImageIO. Its saved EXIF contains:

| Field | Measured value |
| --- | --- |
| Camera make/model | SONY / ILCE-7CM2 (owner's A7C II) |
| Focal length | 50 mm |
| F-number | 1.4 |
| Lens model | Contax Zeiss 50mm f/1.4 |
| 35 mm equivalent focal length | 50 mm |
| Maximum-aperture APEX value | 0.96875 |
| Image dimensions | 7008 × 4672 |

This confirms the first end-to-end metadata path: the Mac-prepared profile was
uploaded through the stock USB loader, verified in flash, then reported by the
custom application to the camera and saved in a photograph. The installed image
is firmware 2.0.0, SHA-256
`2b4c06eccce389aa580177d81d28c3aca4c581ccc59f2a194a5e2814bfdfe61c`.
The F-number is declared metadata; the passive lens has no electronic aperture
sensor, so it does not independently measure the physical aperture-ring setting.

Photo capture and the three requested lens fields are confirmed. The owner
reported shooting in Auto mode and did not know the selected focus mode. The
camera's display and clean shutdown remain unconfirmed. Exposure-mode EXIF tags
do not establish focus mode. Camera qualification remains partial, and autofocus
remains disabled regardless of the camera's selected focus mode.
The separate Astra factory reverse-engineering pass is examining a possible
metadata patch that retains factory autofocus; this photo does not validate one.

The owner subsequently reported that it was connected to the computer, without
specifying whether this meant the camera or the USB update cap. Read-only OS
inventory found zero matching LM-EA9 update interfaces and sent no HID reports.
No further hardware write or loader read was attempted.

For a later controlled camera check, use P or A exposure mode and select
MENU → Focus → AF/MF → Focus Mode → Manual Focus, following
[Sony's A7C II manual-focus instructions](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405_manual_focus.html).
Sony also documents separate Focus Mode selection in
[Intelligent Auto](https://helpguide.sony.net/ilc/2360/v1/en/contents/0301B_shooting_still_images.html);
the owner's Auto setting alone does not establish that MF was selected or unavailable.
Record startup, displayed metadata and shutdown when that physical check is done.

## Reproduction and retention

The original source is
`/Volumes/EXTREME/DCIM/100MSDCF/DSC02856.HIF`. A byte-identical private copy and
the full ImageIO metadata report are retained under
`references/private/camera-check-2026-10-10/`, excluded from Git. The original
image content was unchanged. Public evidence contains selected fields and hashes,
with unit-specific metadata retained privately.

```sh
env CLANG_MODULE_CACHE_PATH="$PWD/apps/macos/.build/local-cache/modules" \
    SWIFT_MODULECACHE_PATH="$PWD/apps/macos/.build/local-cache/modules" \
    swift tools/inspect_camera_metadata.swift INPUT.HIF NEW_PRIVATE_REPORT.json
```

The reader refuses to overwrite an existing report and only reads the input
image. See [machine-readable evidence](camera-50-metadata-2026-10-10.json) and
[the USB milestone](usb-metadata-milestone-2026-10-10.md).
