# Original stock 1.8 restoration for a loaded-lens comparison

October 11, 2026, America/New_York. **Original stock 1.8.0 upload completed;
physical reconnect and byte verification are pending. Keep the adapter off
the camera until verification succeeds.**

The owner confirmed that AF 2.3 was tested with the Contax Zeiss 50mm f/1.4 and
C/Y-to-M converter. They report eventual focus, substantial hunting and frequent
purple focus indication. The camera settings and focus trigger are unknown;
photograph sharpness, focus-lock behavior and mechanical reference are
unverified. See [the owner observation record](af-23-camera-lifecycle-2026-10-11.md).
They requested the original firmware for comparison and confirmed the adapter
was back on its USB cap with the official updater closed.

## Restoration input and bounds

The verified original **same-unit 1.8.0 backup** passed an independent offline
integrity and identity check. The committed
[stock recovery bundle](../../firmware/recovery/stock-1.8.0/README.md) remains
unchanged. Its private key and plaintext unit backup stay outside Git.

| Item | Value |
|---|---|
| Original full-flash SHA-256 | `1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01` |
| Original 20,172-byte application SHA-256 | `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564` |
| Restored application slot | 110,592 bytes, `0x5000..<0x20000` |
| Application-slot SHA-256 | `265f93797db99f2dbba5b649bf5b12bc19efadeaa8e9fe77ade5fca128d17173` |
| Planned upload reports | One START plus 1,728 acknowledged 64-byte pages |
| Release CLI SHA-256 | `614767d8e7c4f754c88c8b342d89614af837162abc282578df999619468e861e` |

This restores the entire original application slot, including the upper area
left unchanged by the recent 20 KiB AF updates. It retains the bootloader code,
the `0x4040..<0x5000` gap, factory user row, calibration and device ID. START
sets the 58 known loader metadata bytes from the original backup with version
1.8.0; six adjacent loader RAM-derived bytes are excluded from the comparison.
NVM controller status is diagnostic data and is not promised identical.

## Transaction and reconnect verification

Transaction `79DEC204-74E8-4BB4-B392-4EB8AE7D4AE3` completed at
`2026-10-11T19:42:01.717870+00:00` (15:42 local). Native upload exited successfully
after **one START and 1,728 acknowledged pages**, covering all 110,592 bytes.
The fresh pre-upload backup reports 2.3.0 and matches the earlier verified AF
2.3 application; its full-flash SHA-256 remains
`26e47f20f2b887b687cf6d80769685635957755d75999269dd3968937e604e78`.
Both flash and auxiliary data were read twice in 4,359 CHECK/READ exchanges,
followed by one final idle pre-START read. Prior recovery records, the new
durable journal and the armed-connection marker were confirmed locally.
**Zero HID reports were sent after upload while awaiting physical reconnect.**

The prototype was quit and the official updater was confirmed absent before
exclusive native access. The native command is `ea9ctl restore-stock
ORIGINAL.ea9backup --idle`, where ORIGINAL is the private original same-unit
backup. Exact paths, command output, frozen input and local snapshots are saved
in ignored private evidence.

Native upload obtains a fresh two-pass full-flash and auxiliary backup, checks
the qualified bootloader, MCU geometry and unit identity, preserves the prior
journal and applied-lens record, synchronizes recovery evidence, and performs
one final idle flash-block-zero read before START. Upload completion still
requires an owner-confirmed physical unplug/reconnect, then `ea9ctl verify
--idle`. No CHECK, READ or other report is sent between completed upload and
that power cycle.

After reconnect, native verification and an independent offline comparison
must establish original application-slot equality, known metadata equality,
unchanged protected/factory regions, new same-unit USB identity and matching
transaction records. Upload acknowledgement alone is not byte verification.
Current results and report counts are recorded in
[the machine-readable evidence](stock-18-comparison-2026-10-11.json).

## Planned camera baseline after successful byte verification

Use the loaded 50mm lens and converter, still-photo P or A mode, **AF-S**,
**Pre-AF Off**, a central focus area, lens aperture f/1.4 and the lens focus ring
at infinity. Use a well-lit stationary subject with clear contrast at roughly
3–5 m. Record the actual settings and stock displayed aperture/focal length;
the original stock metadata may differ from the custom 50mm profile.

Observe startup without focus-button input and whether motion stops. Make one
half-press and record hunting, approximate acquisition time and the indicator.
If it locks, take one photograph for subsequent sharpness/EXIF inspection.
Release the button, observe stopping, wait about ten seconds and switch off
once; record display and motor shutdown. Stop for grinding, repeated hard-stop
pushing or continuous drive for roughly two seconds; switch off and remove the
battery if driving continues. Do not retry an abnormal cycle.

These conditions establish a reproducible stock baseline. The earlier AF 2.3
report lacks matched settings, so it cannot yet support a quantitative A/B
claim. An AF 2.3 comparison under the same conditions follows separately after
the stock result is recorded. AF-C, video and factory parity remain unqualified.
