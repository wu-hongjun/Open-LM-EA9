# Upstream 750 kbaud comparison on the A7C II

## Installation

The [4.4.0 comparison](../../firmware/candidates/4.4.0/README.md) was uploaded
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

The image is awaiting physical reconnect and strict byte verification.
Camera observations are pending.
