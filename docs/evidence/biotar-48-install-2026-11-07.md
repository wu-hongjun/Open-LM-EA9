# Biotar 58mm f/2 — first 4.8 installation

Status: upload acknowledged; awaiting owner physical reconnect and strict byte
verification. Keep the adapter off the camera. This is not a verified installation
or a qualified metadata-only transport yet.

The owner authorized installation with the adapter on its USB cap and TECHART
Update/OpenLensAdapter closed. One adapter was detected. The fresh full read
matched pinned 4.6.0 and Biotar 58mm f/2 metadata. A second immediate two-pass
backup matched it byte-for-byte before START. Source admission, same-unit stock
qualification, blank extension region and required lock checks passed.

The native 0.29 installer sent one START and 960 application pages, 61,440 bytes
covering 0x5000–0x14000. All acknowledgments matched; the command exited cleanly.
No reports followed the final page. The durable transaction remains unverified.

The plan preserves all 24,576 bytes at 0xa000–0x10000, of which 20,529 were
non-erased. The original 58-byte metadata and complete pre-bank contents are
retained in private recovery evidence. The immutable application, extension and
bank use the published 4.8 pins; the declared mutable journal is initialized for
Biotar, sequence/generation 1. Existing profiles, backups and recovery-key files
were checked and remain unchanged.

Next: physical unplug/reconnect on the cap, both apps closed, then complete
same-unit application/metadata/protected-data verification. Only afterward will
the first experimental metadata-only switch select Contax Zeiss 50mm f/1.4.
That operation requires its own physical reconnect and full invariance check;
return to Biotar before any camera use. A queued request is not camera-verified.

Camera startup, autofocus, capture, exposure, journal consumption and shutdown
on 4.8 remain untested. Raw dumps, approval tokens, identifiers and keys remain
private. [Machine-readable record](biotar-48-install-2026-11-07.json) ·
[Migration and qualification procedure](../bank-migration-2026-11-07.md).
