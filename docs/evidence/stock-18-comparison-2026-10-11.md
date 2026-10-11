# Original stock 1.8 restoration for a loaded-lens comparison

October 11, 2026, America/New_York. **Original stock 1.8.0 is restored, and its
entire application slot matches the original backup. The owner used it on the
camera before host readback and reports much less hunting. The strict native
transaction remains unverified because saved motion settings changed.**

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
left unchanged by the recent 20 KiB AF updates. The host writes retain the
bootloader code and `0x4040..<0x5000` gap, factory user row, calibration and
device ID. The gap includes a stock application-owned saved-settings record
at `0x4100..<0x412c`; later camera use can change it. START
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

## Reconnect readback after the owner used stock on the camera

The owner responded to the reconnect request with:

> The stock firmware hunts way less, however the stock firmware seems to tell the camera it can vary the aperture but in reality it can't stop down, can we perhaps build it such that aperture is unknown?

They then confirmed “Back on USB cap; updater closed.” A new unblocked USB
registry connection was observed, with both the prototype and official updater
absent. Native `verify --idle` completed and published two matching full-flash
and auxiliary read passes in **4,359 CHECK/READ exchanges**. The loader reports
**1.8.0**. The invariant comparison then exited **1** with “Unexpected flash
changes outside the planned application and loader metadata.” No additional
reports, upload or automatic retry followed.

An independent offline audit established:

- The complete `0x5000..<0x20000` application slot, including the original upper
  application area, exactly matches the original same-unit stock backup and
  the journaled upload. Original 20,172-byte application code also matches its pin.
- Bootloader code, all 58 known START metadata bytes, user row, calibration and
  device ID match the original backup and pre-upload evidence.
- **Thirteen bytes differ from the original full-flash backup**, all within
  the recovered **44-byte saved-settings record `0x4100..<0x412c`**. Every flash
  byte outside that record matches the original backup; surrounding row bytes
  were preserved. No raw unit settings are published.
- Affected fields are encoder sample, protocol/relative position, velocity,
  target, direction and timeout count. They agree with the recovered save path
  [`0x5d68`](../reverse-engineering/stock-nvm-drivers.md) and
  [settings schema](../reverse-engineering/stock-settings-schema.csv). This is
  consistent with factory settings persistence during the owner's intervening
  camera use; the actual save call was not traced, so causal attribution remains
  an inference.

Post-camera full-flash SHA-256:
`6a89393b01cad5a931e289ee1aaf03c7a3e0b840b7bf5c1c6261d03b51575f6b`.
Private logs, two-pass backups, journal snapshots and the independent audit are
retained. Public script/log hashes and affected-field names are in the JSON.

**Application byte equality passed; strict native restoration invariants did
not pass.** The pending journal is not marked verified, the old local applied
record is not promoted as stock metadata, and the failed connection's reconnect
marker remains. The native verification guard was not relaxed. Any further USB
operation requires physical reconnect and an explicit workflow for the remaining
transaction; do not treat these offline findings as a native all-checks pass.
No additional firmware was uploaded to force the mutable settings back to their
old values. This case reinforces why upload verification precedes camera use.

## Owner comparison and aperture investigation

The owner reports much less hunting with stock than AF 2.3. The comparison lens
is understood from session context to be the same 50mm/converter setup; actual
focus mode, Pre-AF, target, lighting, ring settings, timings, startup/shutdown
and photograph sharpness remain unreported. This is useful qualitative evidence
of a performance gap, not a measured matched-conditions result.

Stock's camera aperture dial also selects focal/options settings while its
working iris remains manual. The requested unknown aperture behavior, current
fixed-range implementation and unresolved F-- encoding are documented in
[manual aperture policy](../manual-aperture-policy.md). There was no aperture
experiment or new custom firmware upload during this readback.

## Controlled camera baseline procedure for a future matched comparison

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

These conditions establish a reproducible stock baseline. Both existing owner
reports lack matched settings, so they cannot support a quantitative A/B claim.
A future AF 2.3 comparison should use the same conditions. AF-C, video and
factory parity remain unqualified.

## Later reviewed resolution

The owner subsequently requested resolution and AF 2.4 installation. After a
new physical reconnect, a fresh two-pass stock backup matched this earlier
post-camera readback in full. The explicit reviewed-motion policy accepted only
the same 13 known motion bytes, archived the failed journal with a separate
receipt and removed the active pending pointer. It did not mark this original
strict verification passed, alter the saved record or clear the old blocked
connection. See [the policy](../stock-restore-resolution.md) and [later hardware
record](af-24-upload-2026-10-11.md). The body of this record and its JSON retain
the original failed-verification observation.
