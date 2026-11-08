# 4.8 metadata migration, installer and app switching

The first owner-authorized hardware upload is recorded
[separately](evidence/biotar-48-install-2026-11-07.md). The software/audit milestone
below was completed offline; its validation does not substitute for hardware checks.

The native app now supports explicitly acknowledged experimental 4.8 installation,
metadata-only lens selection and verified pre-bank rollback. This milestone was
completed offline: no adapter discovery/opening, HID reports, flashing, motor
operation or updater launch. Published 4.8 segments and their manifest are unchanged.
Hardware USB reset, NVM power loss and camera behavior remain unqualified.

## Ownership decision and evidence

The old vendor suffix is opaque data to preserve, not blank spare space.
Ownership of 0x4020–0x4039 transfers to the pinned 4.8 application only during a
complete, reviewed migration from an exact supported source. Settings switching
cannot claim that area on stock or legacy firmware. The entire original 58-byte
metadata stays in a private, unit-bound backup for rollback.

The audit executes the original boot prefix, SHA-256
8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895:

- All 65,536 idle command pairs: START has a fixed metadata destination; CHECK
  copies only the first 16 metadata bytes; READ is an addressed opaque byte
  transfer; other pairs are ignored. No suffix interpretation was found here.
- Both PA23 startup branches: the cap enters the USB receive loop; the other
  branch executes the original jump using vectors at 0x5000 and sets VTOR there.
  Neither branch reads metadata. GPIO/USB/HAL initialization is stubbed.
- The initialized metadata pointer was separated from the upload pointer and
  RAM USB registration node. A CHECK mutant copying 58 bytes triggers the
  suffix-read tracer, demonstrating that this test detects the missing boundary.
- Original helper 0x1080 checks lock bits using address shifted by 14. The host
  checks those bits and the actual 8 KiB physical regions for this 128 KiB device.
  No unlock command is issued. See Microchip's lock-region table in
  [DS40001882, section 22.6.3](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU32/ProductDocuments/DataSheets/SAM-D21-DA1-Family-Data-Sheet-DS40001882.pdf).

This covers the pinned loader's audited protocol/startup paths, not a formal
whole-program alias proof or complete electrical USB simulation. It does not
prove that the old vendor application never used the suffix. That application
is replaced in the same migration, and rollback restores its original metadata.
Unknown loaders and modified/unsupported source images fail before START.

## Installation and selection

The app prepares a concrete plan from a verified Read on the current connection.
Its approval digest binds the full before-flash snapshot, protected auxiliary
hashes, geometry/lock state, connection, selected profile, new metadata and
complete outgoing payload. After confirmation, a fresh two-pass backup and
reconstructed plan must match that approval. Any change stops before START.

Installation requires existing same-unit stock-upload qualification and an
experimental acknowledgment. Only pinned stock or exact 4.4–4.7 sources are
admitted. The new region 0x10000–0x14000 must be entirely FF, and all required
write regions must be unlocked. Nonblank storage is not claimed automatically.

The sequential payload is 61,440 bytes, 0x5000–0x14000: pinned base application,
the exact before-backup bytes in 0xa000–0x10000, pinned extension/bank and the
initial journal. This physically erases/reprograms the gap while restoring its
contents; it is not a sparse-write loader. Boot, saved records, remaining upper
flash, user row and calibration must remain unchanged.

Metadata bytes 3–31 are preserved, 0–2 become 4.8.0, and 32–57 receive the bound
OLAC request. A canonical journal seeds the selected profile at sequence 1,
consumed generation 1; the mailbox uses the same generation. Initial application
startup therefore does no settings write. The published generation-zero seed
file stays immutable; the installer changes only the declared mutable settings.

Before START, recovery evidence is synchronized and a durable intent is saved.
A final READ of address zero sets the loader's overread address scratch. Install
sends one START and 960 pages. No query, retry, END or padding follows. Lost ACKs
and cancellation leave the intent pending and require physical reconnect.

A profile switch requires exact installed code/extension/bank pins, a canonical
mailbox and recoverable journal. The local profile must exactly match a bank
entry; edits/unconfigured zooms do not silently trigger firmware rewriting. The
bank contains seven configured lenses. Adding the 28–70mm zoom requires a chosen
focal length and separate bank update.

A changed selection increments generation and sends one START, zero application
pages. Prefix 0–31 stays unchanged. The loader remains armed: keep the adapter off
the camera, physically unplug/reconnect through the cap, then verify. A registry
change alone does not prove a power cycle; UI/CLI acknowledgment requires the
physical action. The first switch is an explicit experimental test. Only completed
same-unit, new-connection, full readback of that selection creates the transport
proof used by normal switches. Installation, a version read or an ACK alone does
not qualify it. That proof does not qualify camera autofocus.

The app distinguishes the journal's committed profile from a newer request
waiting for camera startup. Reconnecting through the cap does not run the app.
Read after camera use to verify consumption. Selecting the configured slot is a
no-op; choosing the old committed slot while another request is pending creates
a newer cancellation request. Counters fail on exhaustion instead of wrapping.

Each changed USB selection still erases the fixed metadata row once. The 16-row
application journal does not remove that hotspot. Later camera consumption
rotates one settings row; ordinary AF, aperture clicks and unchanged boots cause
no settings writes. Full backups before/after remain deliberately conservative:
the prototype reduces write footprint, not yet USB read latency.

## Verification, history and recovery

A new connection of the same qualified unit and another matching two-pass backup
are required. Every flash byte must match the reconstructed result except known
scratch 0x403a–0x403f. Device data, user row, calibration, geometry and lock state
must match. A metadata-only switch must leave the whole application, bank,
journal and upper flash unchanged. Camera use before verification can legitimately
consume the request and invalidate this strict cap-only comparison.

Schema-1 bank transactions are separate from legacy uploads. Plans, snapshots
and completed proofs are reconstructed on load. Slot/digest/schema/timestamp and
original-connection mismatches fail closed. Forged verified flags and legacy
applied-lens caches cannot qualify 4.8. Files are private, bounded and durable.
Full inspection archives the old bank observation first, even for the same
version. A failed read leaves the profile unknown and retains its history/backup.
Pending bank/legacy operations block new writes across clients using the shared
USB lock and reconnect marker. Automatic refresh reads descriptors/local history
only; dropdown changes never send a report.

After verified installation, Restore pre-bank firmware reconstructs original
0x5000–0x20000 and all 58 original metadata bytes from its installation backup,
including the region claimed by the bank. It sends 110,592 bytes and requires
reconnect/full verification. Boot and protected auxiliary checks still apply.

An interrupted first installation stays pending and is never resumed automatically
or declared safe for camera use. Partial code may not admit normal bank rollback.
The existing Restore original stock route remains recovery through a freshly
connected cap using this unit's original verified backup. Only strict stock
verification archives a superseded bank intent; backups are retained. Loader
modification and power-loss atomicity are not claimed. Independent recovery from
a damaged loader remains unqualified; this installer does not write the loader.

## App and CLI

The Adapter card shows connection, last-read firmware and configured profile.
The Lens card installs the bank once, then switches profiles. Queued selections
are labeled as waiting for camera startup. Physical aperture remains Unknown;
the lens ring controls it. Legacy per-lens flashing and recovery stay in USB tools.

These are future owner-coordinated hardware steps, not commands run here. Keep
the updater closed and use the physically reconnected cap. Stock-upload
qualification must already exist:

    dist/ea9ctl inspect --idle
    dist/ea9ctl bank-plan install zeiss-jena-biotar-55-f2
    # Review the plan and use its digest:
    dist/ea9ctl bank-install zeiss-jena-biotar-55-f2 APPROVAL --idle --experimental
    # Physically unplug/reconnect, then:
    dist/ea9ctl bank-verify --idle
    dist/ea9ctl bank-plan select contax-zeiss-50-f1-4
    dist/ea9ctl bank-switch contax-zeiss-50-f1-4 APPROVAL --idle --experimental
    # Physically reconnect again, then bank-verify --idle.

bank-plan is disk-only and never enumerates USB. Approval is connection-bound;
a new connection needs a new explicit Read/plan. After qualification, normal
switches omit --experimental. For verified pre-bank rollback:

    dist/ea9ctl bank-plan rollback -
    dist/ea9ctl bank-rollback APPROVAL --idle
    # Physically reconnect, then bank-verify --idle.

## Offline validation

Production Swift tests cover source/lock/ownership rejection, opaque-gap migration,
initial settings, one-report switching, queued/consumed/cancel/no-op states, ACK
loss, cancellation, partial install, unit/connection mismatch, protected-data
tampering, full rollback, edited histories and experimental acknowledgment. Three
isolated source mutants—erase the gap, append a page after START, ignore protected
flash—must fail their production-path tests.

Native migration/selection bytes also run through unchanged compiled 4.8 ARM
startup/NVM code. Initial startup emits no settings command; the switch produces
the exact native decoder's canonical journal record; replay emits no extra
command. This is a synthetic CPU/register/page-buffer model, not physical flash.

Firmware regressions, reference checks, original recovery and native tests pass.
The bank cards/dropdown and pending-camera labels were reviewed in isolated,
USB-disabled previews, which were closed afterward. Machine-readable
[evidence](evidence/bank-migration-2026-11-07.json) records results/source hashes.
The [initial bank design](profile-bank-2026-11-07.md) remains a preparation-stage
record; its published images and pins are preserved.
