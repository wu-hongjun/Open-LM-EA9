# OpenLensAdapter rename

The project and native macOS app are now **OpenLensAdapter**. The GitHub
repository is [wu-hongjun/OpenLensAdapter](https://github.com/wu-hongjun/OpenLensAdapter).
The existing repository was renamed, preserving its history and the
`archive/pre-4.5-baseline` tag. The local Git remote uses the new URL.

The app is version 0.27.0 (build 38), packaged as `dist/OpenLensAdapter.app`.
Its Swift package, executable, source target, resource bundles, window/menu
name, build scripts and maintained documentation use the new name. `ea9ctl`
keeps its existing command name. The local workspace folder need not be renamed.

The original Opus 5.5 icon is editable Swift/AppKit vector code with a checked-in
1024px PNG master and [provenance](../assets/branding/README.md). Packaging
generates all ten macOS renditions and ICNS locally. The renamed two-card window
was checked in an isolated offline preview, with all USB operations disabled.

## Data compatibility

The rename deliberately retains these stable identifiers:

- Bundle identifier and Application Support folder: `org.openlmea9.prototype`.
- Backup type `org.openlmea9.backup` and `.ea9backup` packages.
- Original stock-backup encryption associated-data string. Its old project
  spelling is a cryptographic format identifier and must not be renamed.
- Existing profile IDs, update-journal schemas, keys and shared USB lock path.

App, CLI and USB safety now share one `AdapterStorage` path definition.
No migration or copying of user data is required. Preservation checks compared
312 existing local profile/journal/backup/key files and 19 tracked profile,
release/recovery payload and bundled-firmware files against the pre-rename state.
All were unchanged. Stock recovery still passes its seven offline tests.
Local private data and keys are not included in the commit.

## Customization structure

The working source bytes moved into shared `firmware/core/` and
`firmware/targets/lm-ea9/src/`, with build rules and a target descriptor alongside
the latter. Default and wider-range builds reproduce the published 4.5.0 and
4.6.0 SHA-256 values exactly. No working firmware or existing release manifest
was changed.

`firmware/configurations/` contains an editable 50mm f/1.4 example. Custom mode
builds an unpublished version in a private output directory, records source,
target, recipe, build-rule and image hashes, and marks the image unqualified.
It does not bundle or flash the result. The example was ARM-built and checked
through the real protocol C under sanitizers, including all aperture operands
and an unmodified-Biotar failing control. [Customization guide](customization.md).

LM-EA9 remains the only implemented hardware target. Other adapters require
actual board/driver/loader work and transport qualification. No new hardware
access or camera test was performed for this rename. Working 4.5.0 retains its
owner-observed AF/photo/aperture-dial/shutdown record; 4.6.0 remains offline.

[Verification evidence](evidence/openlensadapter-rename-2026-11-07.json).
