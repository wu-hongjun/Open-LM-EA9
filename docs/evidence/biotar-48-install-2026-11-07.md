# Biotar 58mm f/2 — first 4.8 installation

Status: installation byte-verified on November 8 after the owner's physical
reconnect. The first experimental 50mm metadata-only switch was acknowledged;
it now awaits a separate physical reconnect and strict invariance check.
Keep the adapter off the camera; the metadata-only transport is not qualified yet.

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
and no follow-up reports. The requested mailbox is slot 2, generation 2; the
last committed journal remains Biotar slot 6, sequence/generation 1 until camera
boot consumes a request. This is an acknowledged write, not verified readback
or camera application. A durable unverified selection record is retained.

Next: physically unplug/reconnect through the cap with both apps closed, then
verify that the complete application, bank, journal, upper flash and protected
data are unchanged and only the planned mailbox/scratch bytes differ. After
that passes, switch back to Biotar and repeat reconnect/verification before
camera use. Each START arms the loader, including a metadata-only START.

Camera startup, autofocus, capture, exposure, journal consumption and shutdown
on 4.8 remain untested. Raw dumps, approval tokens, identifiers and keys remain
private. [Machine-readable record](biotar-48-install-2026-11-07.json) ·
[Migration and qualification procedure](../bank-migration-2026-11-07.md).
