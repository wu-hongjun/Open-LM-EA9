# Reference collection

Firmware build dependencies are indexed in [build-dependencies.json](build-dependencies.json),
with official source URLs, pinned versions and archive digests. Their local tool
cache is outside the immutable research snapshots. The [metadata firmware fork](../firmware/README.md)
and [USB application-write analysis](../docs/usb-metadata-milestone.md) build on
the archived source without modifying it.

Collected October 10, 2026 for modular LM-EA9 firmware, a host communication
protocol, and a macOS app, targeting the Sony A7C II and the
[requested lenses](../profiles/requested-lenses.json). The stack remains
undecided; Rust-related sources support evaluation of one candidate.

## Sources saved locally

| Source | Local entry point | Contribution |
| --- | --- | --- |
| [weiziqian / E-mount-impl-on-Techart-EA9](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9) | [README](upstream/weiziqian/E-mount-impl-on-Techart-EA9/README.md) | C firmware, SAMD21 hardware, servo, uploader, host tests |
| [weiziqian / E-mount-protocol-RE](https://github.com/weiziqian/E-mount-protocol-RE) | [README](upstream/weiziqian/E-mount-protocol-RE/README.md) | Frame format, autofocus, metadata, optical-data interpretations |
| [Entropy512 / sigrok-dumps, emount branch](https://github.com/Entropy512/sigrok-dumps/tree/emount/lens_mounts/sony_emount) | [Capture README](upstream/Entropy512/sigrok-dumps/lens_mounts/sony_emount/README) | Five original A6000 logic-analyzer recordings, with electrical context |
| [Entropy512 / libsigrokdecode, emount branch](https://github.com/Entropy512/libsigrokdecode/tree/emount/decoders/sony_emount) | [Decoder](upstream/Entropy512/libsigrokdecode/decoders/sony_emount/pd.py) | Andrew Dodd's Python waveform decoder and its C library host |
| [LexOptical / E-Mount](https://github.com/LexOptical/E-Mount) | [README](upstream/LexOptical/E-Mount/README.md) | Arduino C++ implementation; header naming, checksum, manual-lens emulation |
| [LexOptical / E-Mount-Traffic-Samples](https://github.com/LexOptical/E-Mount-Traffic-Samples) | [README](upstream/LexOptical/E-Mount-Traffic-Samples/README.MD) | NEX7/A7 text traces and TypeScript/JavaScript visualizer |
| [morluto / REA](https://morluto.github.io/rea/) | [README](upstream/morluto/rea/README.md) | TypeScript reverse-engineering CLI/MCP, provider bridges and website/docs |
| Official Techart firmware 1.8.0 | [Cache provenance](private/techart/stock-1.8.0/provenance.json) | Recovered application image, release note, product manifest |
| Original Techart macOS updater | [Bundle metadata](private/techart/TECHART_Update.app/Contents/Info.plist) | Local copy of TECHART_Update.app, updater version 1.0 |
| Connected LM-EA9 read-only evidence | [Provenance](private/connected-device-2026-10-10/provenance.json) | USB registry/reports, two matching bootloader dumps and two matching installed application reads |
| USB-cap follow-up and complete main-flash backup | [Provenance](private/usb-cap-followup-2026-10-10/provenance.json) | Two matching 128 KiB reads, chip/protection/fuse/calibration/Port A snapshots, tool versions and command ledger |
| USB unplug/reconnect verification | [Provenance](private/usb-cap-reconnect-2026-10-10/provenance.json) | New registry entry with matching identity; complete flash and qualified snapshots still match; USB-only equipment recorded |

[sources.json](sources.json) records exact Git commits, retrieval URLs, included
paths, license observations, and dependency gitlinks. Source snapshots contain
tracked files without nested Git repositories or installed dependencies. Only
the Sony E-mount directory and root README are retained from sigrok-dumps; all
five relevant recordings are present. The LM-EA9 documentation submodule is
saved as its own neighboring protocol repository, with a relative directory
symlink so its original README links work. REA's external submodules
are recorded at their pinned commits but are not fetched as additional tools.

The snapshots, downloaded web documents, and updater are **local,
Git-ignored copies**. The owner's requested
[1.8.0 recovery bundle](../firmware/recovery/stock-1.8.0/README.md) is committed:
the original vendor application plus an encrypted complete same-unit backup,
with the key and raw identifiers retained privately. This index, provenance manifest, analysis, scripts, and
checksums belong to the project. The earlier copies in artifacts/private/ are
retained for existing links; this folder is the current collection entry point.

## Supporting documents

[visuals/](visuals/README.md) collects the nine photographs used in the native
app, source pages, attribution, original-file digests and a reproducible fetch
script. The original images are preserved locally and bundled for offline use;
downloaded photos are excluded from Git. Lens pictures identify example models,
not the owner's individual units.

[documents/](documents/) includes offline HTML snapshots of the REA website,
atsamd-rs repository, atsamd-hal API, Rust Embedded Book installation chapter,
eframe API, hidapi API, and egui repository. LexOptical's linked collaborative
[protocol document](documents/lexoptical-protocol-document.txt) is saved as a
plain-text export; its diagrams and original formatting are not included.

The Techart [product page](https://techartpro.com/?product=lmea9) and
[official manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf)
were readable through web research, but direct downloads returned HTTP 403.
Their links and [relevant researched notes](analysis/techart-official-documents.md)
are preserved; the original PDF and product-page HTML are not local copies.

## Analysis and verification

Start with the [product direction](../docs/product-direction.md),
[prior-work-analysis.md](analysis/prior-work-analysis.md), and broader
[firmware research](../docs/reference-research.md). The
[Rust feasibility study](../docs/rust-architecture.md) is a candidate design.
The [parallel option audits](../docs/audits/README.md) and
[system design recommendation](../docs/system-design-recommendation.md) compare
firmware, management protocol and app alternatives. Their primary citations
are catalogued in [audit-sources.json](audit-sources.json). That catalogue records
all 57 citation URLs, the document that uses each, and either a dated local document,
a pinned source file, or the download failure. Additional snapshots are in
`documents/audit/`; seven Apple responses are explicitly labeled JavaScript
shells, and eight download failures retain the original links. The collected
Microchip datasheet, USB application note and silicon errata are complete PDF downloads.

The [USB-cap investigation](../docs/usb-cap-investigation.md) adds actual device
evidence and static updater/bootloader analysis. Installed application bytes
match the recovered 1.8.0 image. Native CHECK/READ works, while the inspected
stock USB boot path supplies no supported application-launch operation. Raw
device identity, transcripts, dumps and extracted updater/disassembly text
remain private, Git-ignored reference material.

The [USB-cap follow-up](../docs/usb-cap-followup.md) adds the complete main-flash
backup and exact chip/protection measurements. The
[management-entry design](../docs/management-entry-design.md) records the
launch-extension proposal and physical/recovery checks still needed. The
offline [backup verifier](../tools/verify_ea9_backup.py) checks command bytes,
transcripts and dump equality without accessing hardware. Raw binaries and
physical identity remain private; decoded results and hashes are in
[the public evidence summary](../docs/evidence/usb-cap-followup-2026-10-10.json).

The user-reported unplug event was followed by a new registry entry and another
complete matching flash read. The
[reconnect summary](../docs/evidence/usb-cap-reconnect-2026-10-10.json) and
[USB-only development boundary](../docs/usb-only-next-steps.md) record the result
and equipment constraint. Its raw traces and verification-script copies are
private. Earlier evidence retains the limitations that applied to those runs.

The original .sr files remain unchanged. An independent Python sampler saved
[frame records](analysis/entropy512-frames.jsonl) and a
[capture summary](analysis/entropy512-capture-summary.json). These are derived
evidence, not an execution of the sigrok plugin or A7C II measurements.

```sh
python3 references/scripts/analyze_captures.py
python3 references/scripts/verify_collection.py
```

[checksums.sha256](checksums.sha256) covers the collection's files, excluding
itself and the [generated verification report](analysis/collection-verification.json).
Upstream license notices remain
in their source trees. The sigrok library is GPLv3+, its E-mount files declare
GPLv2+, and the captures have a public-domain dedication. Neither LexOptical
snapshot contains a repository license file; no license has been assigned to
that code here. Copying references does not make them part of our implementation.
