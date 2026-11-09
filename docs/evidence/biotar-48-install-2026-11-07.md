# Biotar 58mm f/2 — first 4.8 installation

The Biotar installation passed full byte verification on November 8. On
November 9 the 50mm request read back as planned, and the journal contained
its committed setting. The strict USB-only check rejected that journal change.
The adapter remains on the cap while the readback is reviewed.

The owner authorized installation with the adapter on its USB cap and TECHART
Update/OpenLensAdapter closed. One adapter was detected. The fresh full read
matched pinned 4.6.0 and Biotar 58mm f/2 metadata. A second immediate two-pass
backup matched it byte-for-byte before START. Source admission, same-unit stock
qualification, blank extension region and required lock checks passed.

The native 0.29 installer sent one START and 960 application pages, 61,440 bytes
covering 0x5000–0x14000. All acknowledgments matched; the command exited cleanly.
No reports followed the final page. After the owner confirmed physical reconnect,
another matching two-pass backup verified the complete 61,440-byte result and
all other main-flash bytes except the six known loader scratch bytes. Code/bank
pins and the initial Biotar slot 6, sequence/generation 1 matched. Boot, saved
records, the opaque gap, remaining upper flash, device data, user row, calibration,
geometry and lock state are unchanged. The durable installation is verified and
its original pre-bank recovery source is retained.

The plan preserves all 24,576 bytes at 0xa000–0x10000, of which 20,529 were
non-erased. The original 58-byte metadata and complete pre-bank contents are
retained in private recovery evidence. The immutable application, extension and
bank use the published 4.8 pins; the declared mutable journal is initialized for
Biotar, sequence/generation 1. Existing profiles, backups and recovery-key files
were checked and remain unchanged.

The owner selected Contax Zeiss 50mm f/1.4 for the first metadata-only experiment.
Its fresh two-pass preflight backup matched the verified installation exactly.
The native selection engine sent one acknowledged START, zero application pages
and no follow-up reports. The request selected slot 2 at generation 2, from
Biotar slot 6 at sequence and generation 1.

After the owner confirmed physical reconnect, two matching reads found six
changed mailbox bytes and 64 changed journal bytes. The mailbox exactly matches
the request. Journal row 1 is the canonical record for slot 2, sequence 2,
generation 2. The prior journal row, loader scratch, firmware, bank, saved
records, gap, upper flash, protected auxiliary data, geometry and locks all
matched the before backup. The read establishes that the request was consumed
before verification. The source of the application startup remains unconfirmed.

The strict verifier preserves both backups and leaves the transaction pending.
The reviewed selection path requires another physical reconnect and a fresh
two-pass backup that exactly matches the reviewed flash and expected journal
transition. It keeps a separate resolution record and leaves the strict result
failed. Transport qualification still requires a strict USB-only readback.
The return-to-Biotar write follows the read-only review and has its own reconnect
check before camera use. Each START arms the loader, including a metadata-only START.

Camera startup, autofocus, capture, exposure, journal consumption and shutdown
on 4.8 remain untested. Raw dumps, approval tokens, identifiers and keys remain
private. [Machine-readable record](biotar-48-install-2026-11-07.json) ·
[Migration and qualification procedure](../bank-migration-2026-11-07.md).
