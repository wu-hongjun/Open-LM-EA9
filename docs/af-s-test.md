# First A7C II AF-S test: Contax Zeiss 50mm f/1.4

Current installation/readback state is recorded in the [AF 2.4 hardware
record](evidence/af-24-upload-2026-10-11.md). The preceding stock restoration was
resolved through an explicit reviewed-motion policy: a new two-pass read matched
the retained stock audit exactly. Its original strict failure remains archived,
not retroactively passed. The current [loaded-lens lifecycle and matched AF-S
comparison plan](evidence/af-24-camera-comparison-2026-10-11.md) separates planned
steps from actual observations.

The preceding **AF 2.3.0 installation was byte-verified after the owner's
physical USB-cap reconnect**. Two complete 128 KiB flash reads matched
the exact candidate; protected flash, upper flash and factory checks passed.
The independent offline before/after audit also passed. See the
[completed 2.3 upload record](evidence/af-23-upload-2026-10-11.md) and
[the 2.3 loaded-lens report and planned bare procedure](evidence/af-23-camera-lifecycle-2026-10-11.md).
The owner now has the converter and reports eventual focus with substantial
hunting and frequent purple focus indication. AF mode, Pre-AF and sharpness
remain unverified. AF 2.3 remains **experimental and not camera-qualified**.
A controlled stock baseline under recorded settings is still needed for a
matched comparison; the custom-firmware procedure below applies to later AF
installations. The [aperture policy](manual-aperture-policy.md) distinguishes
unknown physical aperture from a fixed numeric camera-facing declaration.

The owner reported motor movement and proper A7C II shutdown with the earlier
byte-verified 2.1 image; later 2.2 reports cover normal startup, quiet idle and motor
shutdown. Those earlier observations do not qualify 2.3 startup, shutdown,
motor behavior or focus. The historical installation remains in
[the 2.1 record](evidence/af-50-upload-2026-10-10.md), and the
[software evidence](evidence/af-reconciliation-2026-10-10.md) records its later
owner observations and 2.2 host checks.
The later REA ledger identified a retained factory copy overlapping the legacy
profile row. The final 2.2 candidate moves its profile to `0x9f00` and stops before
that region. See [the layout assessment](af-reconciliation.md); upgrading from
2.1 does not restore the upper row previously changed by legacy custom images.

## Prepared products

- App: `dist/Open LM-EA9.app`, version 0.7.0, build 10.
- CLI: `dist/ea9ctl` (signed locally, same DeviceKit transport).
- New offline 2.4: [50mm candidate](../firmware/candidates/2.4.0/README.md), 20,480 bytes, image SHA-256 `c54739a7930cdf4bc12f395a86d38fde6819633b3420821a6b51d8e0704bf6df`.
- Historical 2.1 candidate: `artifacts/firmware-milestone/af-ready-2026-10-10/contax-zeiss-50-f1-4.bin`.
- Historical 2.1 evidence: [AF readiness record](evidence/autofocus-ready-2026-10-10.md).
- Previously installed 2.3: `firmware/candidates/2.3.0/contax-zeiss-50-f1-4.bin`,
  adjacent preparation manifest. This image is 20,480 bytes with profile at `0x9f00`. Image SHA-256
  `39222b5f5b232045a7599da1afc45753bb8ea0f12c338501131f49e0dcb854a4`.
- Historical 2.2 installation: [upload/readback record](evidence/af-22-upload-2026-10-11.md)
  and [owner camera observations](evidence/af-22-camera-lifecycle-2026-10-11.md).

The historical 2.3 candidate is 20,480 bytes, with its profile at `0x9f00`.
It reports 50 mm, nominal f/1.4, lens name `Contax Zeiss 50mm f/1.4`, camera
version 2.3 and loader version 2.3.0. Its template SHA-256 is
`8996767bfc8e8625739e1c7619a54db1dd0b8da8150526b9afa4c9a490434e88`;
its personalized image SHA-256 is
`39222b5f5b232045a7599da1afc45753bb8ea0f12c338501131f49e0dcb854a4`.

The stored aperture is reported metadata, not a measurement of the aperture
ring. Stop down freely using the lens. If the saved EXIF must match that
manually chosen f-number, prepare a matching fixed camera report; the app
continues to show the actual iris as unknown. The image is reproducible from the pinned template
and profile; the uploader accepts built-in templates, not arbitrary image files.

## USB installation and verification

The original 1.8.0 restore source is also saved in the
[committed recovery bundle](../firmware/recovery/stock-1.8.0/README.md), with an
encrypted complete backup and an offline unpack tool. Retain its separate key.

App 0.7 / the current CLI explicit AF installation selects **2.4.0**. It is
the current installation stages are in the hardware record. The 2.3
upload/reconnect evidence remains historical and unchanged. The stock transaction
was closed only through the explicit reviewed resolution, with its failed
journal retained. Every new upload still requires physical reconnect and strict
verification before camera use. See [the 2.4 source/build/test record](evidence/factory-af-baseline-2026-10-11.md)
and [the new 50mm candidate](../firmware/candidates/2.4.0/README.md).
The Device dropdown preserves the verified installed variant when changing
profiles; it does not silently upgrade 2.3 to 2.4.


1. Close TECHART Update and other USB clients. Connect the adapter itself through
   the USB update cap; a camera connected by USB is a different device. Unplug and
   reconnect the cap before the first operation. Check `dist/ea9ctl inventory`.
2. In the app choose the 50mm f/1.4 profile in the Device dropdown. Open
   **USB tools → Experimental autofocus → Install Experimental AF 2.4.0**. The confirmation names the enabled motion and unqualified camera state.
   The existing unit-specific stock-upload qualification is required. Installation
   saves and synchronizes a fresh two-pass recovery backup and journal before START.
3. After the upload, **physically unplug and reconnect the cap**. The app detects the new connection automatically; confirm the prerequisite and
   verify the pending update. Leave the updater closed throughout. The app must
   confirm the exact application/profile, protected loader, other flash, known
   metadata and factory data before calling this firmware verified.
4. Only then move the adapter to the camera, with the camera switched off.

The equivalent CLI sequence, from the project root, is:

```sh
dist/ea9ctl inventory
dist/ea9ctl apply-af contax-zeiss-50-f1-4 --idle
# Physically unplug and reconnect the USB cap here.
dist/ea9ctl verify --idle
```

`--idle` acknowledges the physical prerequisite; it does not perform a reconnect.
Do not run CHECK, READ, another client or an extra command while the loader is
armed. Even a read can become the next flash page. A lost acknowledgement or
cancellation ends the transfer without retry; reconnect before recovery. Do not
rebuild the bundled template or change the local profile between preparing,
uploading and verifying this candidate.

## Camera procedure

Before the C/Y-to-M converter arrives, use the separate
[bare-adapter startup/idle/shutdown procedure and result record](evidence/af-23-camera-lifecycle-2026-10-11.md).
That first cycle uses no focus-button input and does not qualify optical AF.
The following procedure is for the loaded 50mm lens once the converter is available.

Our initial test configuration is still photography in P or A exposure mode,
with the mechanical lens focus ring at infinity and aperture ring at f/1.4.
Choose **MENU → Focus → AF/MF → Focus Mode → Single-shot AF**, which Sony describes
as locking focus after acquisition for a stationary subject.
[Sony A7C II Focus Mode guide](https://helpguide.sony.net/ilc/2360/v1/en/contents/0405C_focus_mode.html).
Use a central focus area and a well-lit stationary subject with clear contrast.
Keep continuous/pre-focusing disabled where configured so acquisition is deliberate.

1. Switch on without pressing the shutter. Observe startup/homing: whether the
   body starts normally, the adapter moves briefly, then stops, and the displayed
   focal length/aperture. The firmware attempts bounded startup reference acquisition
   after a completed fault-free handshake, including in MF; movement alone does
   not establish a valid reference.
2. Switch off once before repeated AF testing. Record whether it shuts down
   normally, any park motion, and whether movement ends. Turn on again only after
   a normal shutdown. This establishes the basic lifecycle observations.
3. Aim at a stationary target about 3–5 m away and half-press once. Record motion,
   direction, time to focus, focus indicator and hunting. Release the button and
   check that active acquisition stops. Take one photo if focus locks; inspect
   center sharpness at full size and retain the original file for metadata checks.
4. If startup, shutdown and the first acquisition behave normally, try three
   near/distant pairs (roughly 1–2 m versus a distant target), releasing between
   attempts. Record every failure, not just the successful photos.
5. Finish with a clean shutdown observation. If the mechanism repeatedly pushes
   a stop, keeps moving, makes an abnormal sound, or the body hangs, end the test
   by switching off; remove power if switching off does not stop it. Restore stock
   after reconnecting the USB cap rather than repeatedly retrying a failed session.

Motor/peripheral faults latch until reset. A later half-press cannot retry a
faulted motor. A stationary SPI value can still be a disconnected/frozen sensor:
we detect stalled transactions, not the truth of a stable angle. No electrical
measurement, mechanical zero, A7C II timing, focus accuracy or lens loading has
been qualified by the host tests. The owner has reported motor movement and proper shutdown with 2.1, but the
remaining reference and loaded-lens observations still require camera testing. AF-C, video and heavier-lens qualification follow separately.

## Fallback and restoration

For a motor-disabled custom fallback, use **Install Metadata Only for Prepared
Lens**, or:

```sh
dist/ea9ctl apply contax-zeiss-50-f1-4 --idle
# Physically reconnect the USB cap.
dist/ea9ctl verify --idle
```

Ordinary GUI lens changes preserve a verified AF installation; the explicit
metadata action changes its firmware capability even when the lens is unchanged.

For factory AF, use **Restore Stock from Backup…** and choose this unit's original
verified 1.8.0 backup. The preserved original has been rechecked offline against
its complete manifest and recovered official application. Its private path is
recorded in `references/private/af-ready-2026-10-10/stock-recovery-source.json`.

```sh
dist/ea9ctl restore-stock /absolute/path/to/original.ea9backup --idle
# Physically reconnect the USB cap.
dist/ea9ctl verify --idle
```

Recovery admits a readable 2.1.0, 2.2.0, 2.3.0, 2.4.0 or unknown current version only with the qualified
loader and matching unit. An AF backup cannot substitute for the original stock
source. Restoration writes the saved application slot `[0x5000,0x20000)` and stock
metadata; it does not restore or write bootloader code. Stock upload/readback was
previously verified on this unit. Interrupted-write, power-loss and bootloader
recovery remain unqualified; the current AF-to-stock round trip has not been run
on hardware.

## Record the test

Use [the result template](evidence/af-s-camera-result-template.md). Preserve the
original photos and any timing video privately, with hashes and extracted
metadata in public evidence. A focus confirmation light or correct EXIF alone
cannot establish sharpness or successful motor control.
