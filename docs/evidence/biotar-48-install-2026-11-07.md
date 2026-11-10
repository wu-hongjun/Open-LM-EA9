# Biotar 58mm f/2 — first 4.8 installation

The Biotar installation passed full byte verification on November 8. On
November 9 the 50mm request read back as planned, and the journal contained
its committed setting. The strict USB-only check rejected that journal change.
The owner reconnected again through the cap. The fresh read matched the reviewed
backup byte for byte and closed the pending 50mm transaction.

The subsequent return to Biotar passed strict USB-only verification. This
adapter has a transport proof for the pinned 4.8 package. The Biotar request
is queued for the next application startup.

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

After another owner-confirmed physical reconnect, the read-only review obtained
two matching reads from the same unit on a third connection. Every flash byte
matched the reviewed backup. The review also checked the expected journal
transition, protected auxiliary data, geometry and locks. The durable resolution
records the committed 50mm setting and retains the failed strict result and all
backups. Routine transport qualification still requires a strict USB-only pass.

The experimental return to Biotar passed its fresh preflight and sent one
acknowledged START with zero application pages. The requested setting is Biotar
slot 6 at generation 3. After the owner physically reconnected again, two full
reads confirmed the expected six changed mailbox bytes. Every other main-flash
byte matched the preflight backup, including the six loader scratch bytes. The
protected auxiliary data, geometry and locks matched as well. The journal still
contains the committed 50mm entry at sequence 2 and generation 2. This verified
queued state is the strict transport proof that the app uses for routine profile
switching on this adapter.

## November 9 camera follow-up

After camera use, a new connection and two matching full reads confirmed
Biotar slot 6 at sequence 3 and generation 3. The expected 64-byte journal
entry was the only main-flash change from the queued snapshot. Code and bank
pins, protected auxiliary data, geometry and locks matched.

The owner confirmed the Biotar at f/2 stayed soft at its infinity stop in MF.
At the same distant target, AF hunted without locking and the motor jittered.
The production 4.8 build has no saved motor trace. The mechanical end position
and cause of the jitter are open. See the [4.8.1 motion diagnostic](../../firmware/releases/4.8.1/).

Raw dumps, approval tokens, identifiers and keys remain private.
[Machine-readable record](biotar-48-install-2026-11-07.json) ·
[Migration and qualification procedure](../bank-migration-2026-11-07.md).
