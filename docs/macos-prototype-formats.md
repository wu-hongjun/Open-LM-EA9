# Prototype profile and backup contracts

Version 1, October 10, 2026. These are local file formats and a **read-only
legacy transport**. They are separate from the proposed application management
contract and from Sony E-mount messages. This version makes no on-device
configuration/persistence claim.

## Lens library JSON

Top level: `schemaVersion` (1), `targetCamera` (1–120 characters), `profiles`
(1–256). JSON uses UTF-8; file size is capped at 1 MiB. Dates use ISO 8601 UTC.
Schema versions other than 1 fail without replacing an existing library.

| Profile field | Meaning / constraints |
| --- | --- |
| `id` | Stable unique 1–80 character ASCII identifier: letters, digits, hyphen |
| `displayName` | Local display name, nonblank, at most 120 characters; not a Sony lens-ID assignment |
| `kind` | `prime`, `macro-prime`, `zoom` |
| `minimumFocalLengthMM`, `maximumFocalLengthMM` | Finite millimetres, 1–1,000, min ≤ max; equal for prime/macro |
| `activeFocalLengthMM` | Optional manual zoom setting within the range; absent for prime/macro |
| `maximumAperture` | Finite nominal maximum-aperture f-number, 0.5–64 |
| `currentAperture` | Optional manual aperture-ring f-number, at least `maximumAperture`, at most 128 |
| `notes` | At most 2,000 characters |
| `revision` | 1–1,000,000; increases on Save |
| `savedAt` | Optional last local-save time; seeded profiles have none |

Unknown fields fail import rather than being silently discarded.
Optional values are omitted by the JSON encoder and decode as unknown; JSON
`null` is also accepted. Required fields must be present. Calibration is not
part of this metadata schema. Import preserves IDs/revisions; Save adds a new
local revision. Profile IDs and names do not encode measured optical behavior.
The user-facing editor parses the current locale's decimal separator, and
validates the resulting profile before storing it. JSON numbers always follow
JSON's numeric syntax.

Example (a single valid profile library):

```json
{
  "schemaVersion": 1,
  "targetCamera": "Sony A7C II",
  "profiles": [{
    "id": "contax-zeiss-28-f2",
    "displayName": "Contax Zeiss 28mm f/2",
    "kind": "prime",
    "minimumFocalLengthMM": 28,
    "maximumFocalLengthMM": 28,
    "maximumAperture": 2,
    "notes": "",
    "revision": 1
  }]
}
```

## Local prepared lens

`prepared-lens.json` is a separate UTF-8 document, limited to 4 KiB:

```json
{"schemaVersion":1,"profileID":"contax-zeiss-28-f2"}
```

Schema must be 1; the chosen ID must exist in the current validated library.
Save is atomic. Loading a choice whose ID was removed by import yields no
selection. Invalid, oversized or unsupported documents are preserved and the
UI ignores the choice. This record contains no adapter identity, camera lens
ID, applied revision or read-back result. It represents preparation on this Mac
only. Preparing a lens does not rewrite metadata or increment its revision.

The confirmed Biotar uses 58mm in the seed and editor; its legacy identifier
`zeiss-jena-biotar-55-f2` is intentionally stable across the owner's correction.

## Firmware observation history

`last-firmware-observation.json` is a local history document, independent of the
lens library and backup manifest. Top level: `schemaVersion: 1`, `observation`.
The observation contains `device` (the same identity fields as a backup),
`version` and `readAt` (ISO 8601 UTC). The read is capped at 64 KiB, accepted
versions are `1.8.0`, `2.0.0`, `2.1.0` and `2.2.0`; identity must carry the qualified descriptor and
TECHART/LM-EA9 names, and dates must be positive and no more than 60 seconds
in the future. Saves are atomic and the file is set to mode `0600`. It includes
the serial number; keep it private.

A cached observation associates with a connected device only through a nonempty
matching serial, manufacturer/product and qualified descriptors on both
identities. Registry identity may change across a physical reconnect. The UI
always labels the timestamp as **Last read**. History cannot authorize a USB
operation, qualify loader memory, prove installed bytes or select a mounted
lens. Unreadable/invalid history is ignored without modifying the lens library.

The standalone **Read Version** operation sends one CHECK and no READ requests.
It reuses backup's explicit idle acknowledgement, updater-absence check,
exclusive ownership, callback validation and persisted reconnect handling.
A successful backup also records its CHECK version in local history.

## Native HID qualification and wire bytes

Exact identity: VID `0483`, PID `575A`, manufacturer `TECHART`, product `LM-EA9`,
vendor usage page `FFFF`, usage 1, 64-byte input/output and 4-byte feature
descriptor. The full 53-byte descriptor is pinned in NativeHID.swift. There is
no Report ID item; the API report ID is **0**, with 64 bytes of report data.
Descriptor inspection is read-only. Feature reports are never requested.

Each request is 64 bytes, zero padded:

| Offset | CHECK | READ |
| --- | --- | --- |
| 0–3 | `95 27 68 18` | same |
| 4–5 | `02 02` | `03 03` |
| 6–9 | zero | 32-bit address, little endian |
| 10–63 | zero | zero |

CHECK must return prefix `95 27 68 18 02 02 01 08 00`, the qualified idle 1.8.0
response. READ replies are exactly 64 raw bytes, with no address/sequence tag.
There is one outstanding request, no retry, a five-second reply deadline and
short run-loop drains before/after exchanges to detect stray/duplicate input.
A late untagged reply cannot be safely assigned to a new request. The app
requires a new physical USB connection after uncertainty. Drain intervals are
not a proof that arbitrarily delayed reports cannot occur.

Software permits aligned main-flash blocks from `00000000` through `0001FFC0`.
Before any register READ, it reads `[0,4000)` and requires SHA-256:

```text
8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895
```

This pins the inspected loader code/padding while excluding unit metadata at
`4000`. The only auxiliary windows are these named 64-byte reads:

| Name | Address | Qualification |
| --- | --- | --- |
| Device ID | `41002018` | DID plus reserved bytes; avoids DSU DCC mailboxes |
| NVM status | `41004000` | Qualified byte reads of NVM register block |
| User row | `00804000` | 64-byte user-fuse window |
| Calibration | `00806000` | 64-byte AUX1 window, including USB calibration |

DID must be `1001030B`, ATSAMD21E17A revision D. NVM.PARAM at offset 8 must
report 2,048 pages and page-size encoding 3 (64 bytes), for 128 KiB main flash.
Register snapshots are bytewise and not atomic. These whitelist decisions are
supported in [the hardware follow-up](usb-cap-followup.md), including register
width/read-side-effect analysis. Generic addresses and DSU's debug mailboxes
are unavailable through the prototype API.

Sequence: CHECK (1), boot-code qualification (256 blocks), DID/NVM (2), flash
passes (4,096 blocks), user/calibration repeat reads (4). **4,359 exchanges** in
a successful backup. The first full-flash prefix must also equal the separately
qualified loader code. All checks precede package publication.

## `.ea9backup` package

A directory/package containing:

| File | Bytes | Purpose |
| --- | --- | --- |
| `flash.bin` | 131,072 | One retained copy after two identical full-flash passes |
| `user-row.bin` | 64 | User-fuse window, two identical reads |
| `calibration.bin` | 64 | AUX1 window, two identical reads |
| `device-id.bin` | 64 | Qualification register snapshot |
| `nvm-status.bin` | 64 | Flash-geometry snapshot |
| `manifest.json` | variable | Version, UTC time, identity, reported version, chip, read counts, hashes and scope |

Manifest schema 1 includes `applicationVersion`, `createdAt`, `device` (registry
ID, product/manufacturer, **serial**, location, descriptor qualification),
`reportedFirmwareVersion`, `chip`, `deviceID`, `flashBytes`, `flashReadPasses`,
`auxiliaryReadPasses`, `reportExchanges`, `bootCodeSHA256`, `files` (per-file
`bytes`/`sha256`), `scope`, and `restorationQualified: false`.
The CHECK version is reported identity, not proof of the installed application's
digest or camera behavior. A digest establishes byte identity/integrity, not
vendor signature or recovery capability.

Both full reads stay in memory until they match. Files are written to a new
hidden sibling directory, read back from disk, and the completed directory is
moved to an unused destination. An error removes the staging directory;
existing destinations are preserved. A process crash during disk staging can
leave `.ea9-partial-<UUID>` beside the chosen destination. It is not a complete
backup and can be removed after the app is closed. Rename publication avoids a
visible partial package; power-loss durability of storage hardware is not
claimed. Backups contain private unit-specific evidence and are Git-ignored
when stored under `artifacts/macos-prototype`.

There is no restoration tool in this prototype. Retain original backups outside
build-product folders; `dist` is regenerated by the packaging script.

## AF 2.2 admission and refresh

Prototype 0.5.0 preserves the metadata 2.0 and frozen AF 2.1 resources/pins and
adds a separate `ea9-af-reconciled-template.bin`/`TrustedReconciledAFTemplate` for
2.2.0, camera BCD `0x22`. Its profile is at `0x9f00` and application ends before
`0xa000`; legacy 2.0/2.1 retain their old row at `0xa000` and end `0xa100`.
Image/journal/inspection bounds are version-specific. Existing pending journals and applied-lens records retain
their exact variant. Ordinary GUI profile changes preserve that variant; explicit
AF installation and CLI `prepare-af`/`apply-af` select 2.2. The closed image
allowlist, profile schema/CRC, same-unit qualification, recovery source pin and
physical-reconnect verification rules remain in force. No management-service
wire format or mutable factory-reference record was introduced.

The two-second monitor reads only OS descriptors and bounded local files,
including CLI-published journals and dated firmware history. It sends no HID
feature reports. See [Device workflow](macos-device-workflow.md) and
[AF reconciliation](af-reconciliation.md).
