# Upstream 750 kbaud comparison on the A7C II

## Installation

The [4.4.0 comparison](../../firmware/releases/4.4.0/README.md) was uploaded
to test the speed negotiation change against the November upstream trial.
It declines `0x0C` and keeps the UART at 750 kbaud. The original upstream
identity, optics and motor code are preserved.

The source-built native CLI found the qualified cap. Before START, it
backed up the installed 4.3.0 probe in two passes and saved the durable
update journal. The original same-unit stock backup was validated. An
independent file audit confirmed that the full pre-upload backup contains
the exact previously decoded 4.3.0 diagnostic tail.

One START and 320 application pages were acknowledged. The upload ended
at 21:51:51 UTC on November 6. The pinned 20,480-byte application SHA-256 is
`cf442fa02e4854914b602b4646c689984e9b12de2595adf20a0a1cebaa738a27`.

## Strict verification

After the owner physically reconnected, two matching flash and auxiliary
passes completed at 21:54:24 UTC using 4,359 read exchanges. Native
verification and an independent file comparison matched all application
bytes, the expected 58 metadata bytes, boot code, saved records, upper
flash, user row, calibration and device ID. The established six loader
scratch bytes are outside the metadata comparison.

## Camera comparison

The owner reports that the A7C II displays a fixed f/1.8 and autofocus
works in both still-photo and video modes. The displayed f-number matches
the upstream image's nominal aperture. In a follow-up about exposure,
the owner reported that it also works when stopped down on the lens.
This is a qualitative observation. The shooting mode, iris setting,
saved-file details, shutter speed, ISO, shutdown and camera firmware
version were not supplied.

The owner subsequently identified the currently attached lens as a **Zeiss
Jena Biotar 58mm f/2** and requested live reported-aperture selection with the
Sony camera dial. The 4.4.0 image still advertises its compiled 50mm f/1.8
defaults. This lens clarification does not retroactively identify the lens
used in every earlier trial. The separately prepared
[4.5.0 candidate](../../firmware/releases/4.5.0/README.md) targets the Biotar;
its camera behavior remains untested.

The November 4.2.0 trial failed on this body. The only behavioral change
in 4.4.0 is that the `0x0C` reply declines the speed offer and skips the
switch to 1.5 Mbaud. The upstream lens ID `0xC540`, advertised speed,
startup parser, optical defaults and motor controller are identical at
the source level. This comparison supports the speed negotiation path
as a compatibility factor on this setup. The earlier failure was
reported without a wire trace or matching camera settings, so the exact
failing edge or exchange remains unknown. [Firmware patch](../../firmware/releases/4.4.0/stock-speed.patch) ·
[Earlier trial](https://github.com/wu-hongjun/Open-LM-EA9/blob/9a6905cc99eb6ad62b7885a42a3eddf3d5f3071e/docs/evidence/upstream-november-trial-2026-11-06.md).
