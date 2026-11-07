# 4.8.0 profile-bank experiment — offline sparse package

Seven configured lens profiles, a sixteen-row wear-leveled selection journal,
and boot-time consumption of an experimental metadata mailbox. Biotar 58mm f/2
is the default; the zoom requires an explicitly selected focal length first.
Reported aperture remains f/1.2–f/22. AF/motor/protocol code derives from the
working 4.5 source plus the 4.6 range overlay; startup now includes settings work.

**Not uploaded or camera-qualified. Not accepted by the current updater.**
The four files are addressed segments, not individually installable applications.
The existing 0xa000–0x10000 unit data must be preserved. The proposed upper
region must be qualified against a fresh backup before a new installer can be
enabled. The stock loader uploads sequentially, so preserving a gap's contents
would still require physically rewriting its rows during initial installation.
No USB metadata-only transmitter or bootloader modification is provided.

The metadata field allocation is unqualified and contains foreign data in the
historical factory backup. Do not send a zero-page START manually: it arms the
loader, and subsequent reports can overwrite the application. The settings
journal cannot remove the fixed metadata row's wear cost.

The manifest pins each segment and every assembled source/build input.
Reproduce using scripts/build-profile-bank.py with a new private output folder;
run make test-profile-bank. Preserve this version and use a new version for
changes. See [the design and evidence](../../../docs/profile-bank-2026-11-07.md)
for layout, formats, test coverage, limitations and qualification still required.
