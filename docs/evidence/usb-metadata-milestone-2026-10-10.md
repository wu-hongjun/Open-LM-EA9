# USB metadata milestone evidence

Started October 10, 2026. This record distinguishes compiled/tested behavior,
USB byte verification and camera behavior. It is updated as measurements occur.

- Reference source: `d52ed06cc449918f938e0695fbf29a0c4141f2b2`; archived copy unchanged.
- Metadata-only candidate links at `0x5000`; profile at `0xa000`; binary 20,736 bytes.
- Current template SHA-256: `d7f85bb53897d6b83f30c528d7790ec37e7164090d882251b917060cc300f293`.
- Arm size output: text 7,992; data 1,276; bss including 8 KiB stack reservation 9,564 bytes.
- No `diag_*`, `trail_*`, motor-drive/brake/homing or servo symbol survives linking.
- Swift tests: 7 LensCore + 21 DeviceKit passed before first hardware write.
- C host checks: inherited framing/shutdown, servo, no-body/slow-body, init rescue,
  focus mapping/distance/prediction and seven Swift-generated prime profile images passed.
- C profile tests reject each single-byte corruption of the 256-byte block and
  check actual transmitted name, focal pairs, aperture fields and checksums.
- Stock upload completed: 110,592 saved application bytes, 1,729 acknowledged reports.
  Its fresh preflight backup used 4,359 exchanges and matched the preserved full-flash baseline.
  After the owner confirmed physical reconnect, two-pass post-upload read-back
  passed exact application, protected-region, known metadata and factory-data checks.
  The custom 50mm image upload then completed after a fresh two-pass backup:
  20,736 bytes, 325 acknowledged reports. After a second owner-confirmed physical
  reconnect, two-pass readback verified the exact custom image, known metadata,
  unchanged protected flash and factory snapshots. Firmware CHECK returned 2.0.0;
  the verified applied-lens record is Contax Zeiss 50mm f/1.4, 50mm, AV 4352.
  See [custom upload evidence](custom-50-upload-2026-10-10.json).
  See [stock-upload evidence](stock-upload-2026-10-10.json).
- A7C II photograph capture and saved EXIF: confirmed 50mm, f/1.4 and
  `Contax Zeiss 50mm f/1.4`. The owner reported Auto exposure mode; selected
  focus mode, camera display and clean shutdown remain unconfirmed.
  See [camera metadata evidence](camera-50-metadata-2026-10-10.md).
- Autofocus: intentionally disabled in this metadata qualification build.
- Bootloader restoration and arbitrary interrupted-power recovery: unqualified.

Private logs and generated fixtures are in `artifacts/firmware-milestone`.
Unit-specific application backups and journals remain in Application Support.

## macOS app validation

Prototype 0.3.0 (build 4) was built, ad-hoc signed and passed strict signature
verification. The installed DeviceKit resource matches the tested template hash.
The native UI was inspected after a restart: selecting Contax Zeiss 50mm f/1.4
from the photographed secondary library returns to Device and persists that local
selection. Device shows the pending reconnect state; Prepare and Verify remain
disabled on the same armed connection. No version, lens or backup read was
triggered by launch, navigation or local selection. The Device layout was made
more compact to keep connection, firmware and lens information visible together.

The app includes stock upload qualification, lens apply, reconnect verification,
read-only lens inspection and stock restoration from a unit-matched backup.
The custom candidate has passed the byte checks and photograph metadata check
recorded below. Broader camera behavior and autofocus remain unqualified. A
physical reconnect is required between each upload and post-upload read.

## Astra audit follow-up

The [independent audit](../audits/astra-implementation-audit-2026-10-10.md)
identified and re-reviewed corrections to shared host safety, durable recovery
publication and recovery/cancellation UI. Build 5 and the expanded offline checks
are documented in [remediation evidence](astra-audit-remediation-2026-10-10.md).
The separate Astra REA research thread studies the official image offline.

Build 5 was restarted after the custom upload. The native Device screen shows
the previously read stock version with its timestamp and a separate pending
reconnect/verification state for the prepared 50mm lens. Both Apply and Verify
remain disabled on the armed connection. Launch performed OS discovery only;
no post-upload HID report was sent.

## Custom byte verification

The custom image passed USB verification after the owner confirmed another
physical power reconnect. Two full flash passes and factory-data snapshots were
saved in a separate private `after-*.ea9backup`; 4,359 report exchanges completed.
The full application `[0x5000,0xa100)` matches SHA-256
`2b4c06eccce389aa580177d81d28c3aca4c581ccc59f2a194a5e2814bfdfe61c`.
The protected regions, 58 known START metadata bytes and stable factory snapshots
passed their exact comparisons. The previously documented final six metadata
bytes remain a loader-overread exception, retained in the full backup.

Only this success published `applied-lens.json` and marked the pending transaction
verified. The completed read-only verification cleared this new connection's
temporary reconnect block. No further write was performed. At this stage the
camera check was pending; the subsequent photograph result is recorded below.
Motor motion remains disabled.

Build 6 refreshes the bounded local firmware-observation cache along with lens
and pending-update state, so CLI verification can update an already-open app's
display without another CHECK. It does not add automatic USB reports.

Build 6 was rebuilt, signed and passed strict signature validation for the app
and standalone CLI. Native accessibility and a screenshot confirmed **Connected**,
firmware **2.0.0**, and **Contax Zeiss 50mm f/1.4 · 50 mm · reported f/1.4** with
**On adapter · Last verified** and a USB verification timestamp. Refresh preserved
these values through OS inventory and local record loading only. The physical
reconnect acknowledgement checkbox remains unchecked; no extra HID report was
sent by launch or Refresh, and no new upload is pending.

## Camera photograph metadata

The owner captured `DSC02856.HIF` on the A7C II with the 50mm lens and reported
no apparent motor movement. Native ImageIO read the saved EXIF as 50mm, f/1.4 and
`Contax Zeiss 50mm f/1.4`, confirming the USB-applied profile reaches a saved
camera photograph. A byte-identical image copy and complete metadata report are
retained privately; the source image was unchanged. See
[camera evidence and reproduction](camera-50-metadata-2026-10-10.md).

The owner reported Auto exposure mode and an unknown focus mode; clean shutdown
and displayed metadata remain unconfirmed. The absent motion matches the
deliberately disabled motor code. This result does not qualify autofocus or
measure the passive lens's physical aperture setting. Subsequent OS inventory
found no matching USB-cap interface and sent no HID reports.
