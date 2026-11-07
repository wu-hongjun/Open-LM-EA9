# Local artifacts

Keep active source, published releases/manifests, original stock recovery,
profiles and reference collections in their existing locations. Builds and
private trial material go under ignored `artifacts/private/`. Raw camera frames,
unit identifiers, recovery keys and original unit backups never belong in Git.

On November 7, 2026, the owner requested cleanup of old artifacts. Retired local
artifact trees and the Swift build cache were moved out of the checkout to:

`~/Library/Application Support/OpenLensAdapter/ArtifactArchive/biotar-46-install-20261107-172902/`

The archive has private directory permissions. It contains **973 moved entries,
195,460 files and 3,019,779,881 bytes** (about 3.02 GB), including all 42 backup
directories found among the retired material. Moves used same-filesystem rename;
no files were permanently deleted. The previous artifact hierarchy is retained
inside the archive; the Swift cache is under `build-cache/macos/`.

The current 4.6 installation/verification/cleanup evidence remains in
`artifacts/private/biotar-46-install-20261107-172902/`, including a private plan
and per-move journal mapping every original path to its archived path. Canonical
Application Support data has no references to the moved artifact paths.
To recover an old artifact, consult that journal and move the desired entry
back to its recorded source path, without replacing a newer file.

This cleanup removes old outputs from the checkout; it does not free the
archive's disk space. Profiles, canonical USB backups/recovery keys, all published
firmware and stock recovery remain in place. A hash comparison confirmed that
308 existing profile/backup/key files were unchanged. Reference snapshots and
pinned compiler/header dependencies were retained.

The current signed app and CLI remain in `dist/`. After archiving the cache,
the standalone CLI still emitted the exact pinned 4.6 image without USB access,
and both packaged signatures verified. `make app` recreates the Swift cache.
Future cleanups should retain active trial evidence and archive retired outputs
with an explicit path journal; do not remove backups or keys to save build space.
