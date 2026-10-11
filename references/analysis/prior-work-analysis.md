# E-mount prior work and evidence

Investigated October 10, 2026. Exact revisions and snapshot scopes are in
[sources.json](../sources.json). Observations below refer to those revisions.

## What each layer establishes

| Evidence | What we can use it for | What it does not establish |
| --- | --- | --- |
| Entropy512's original .sr recordings | Independent checks of electrical timing, baud changes, byte framing, checksum and observed payloads | A7C II behavior, LM-EA9 motor control, optical calibration for Contax lenses |
| Andrew Dodd's sigrok decoder | Reading the original waveforms with CS gating and automatic baud detection | Complete checksum validation or complete message-field semantics |
| LexOptical's firmware | Clear names for the header, outgoing checksum calculation, basic camera/lens dialogue | A complete autofocus controller for the LM-EA9 |
| LexOptical's text traces and protocol document | More camera/lens examples and early hypotheses about message fields | Clean uninterrupted recordings or universal agreement on field meanings |
| weiziqian's protocol research and EA9 firmware | Later field interpretations, stock-derived EA9 replies, a working servo/application reference | Verified A7C II compatibility or measured Contax optical profiles |
| REA | Tools for inspecting the updater and supported executable formats | A bare-SAMD21 firmware port or raw-flash load profile |

## Captures: primary evidence

The [capture README](../upstream/Entropy512/sigrok-dumps/lens_mounts/sony_emount/README)
identifies an A6000, a modified Meike 16 mm extension tube, and 6 MHz sampling.
The five recordings cover a Sony SEL55210 at 55 and 210 mm, Sony SELP1650 at its
power-on position, and Viltrox EF-NEX II with Canon EF 50/1.8 STM or EF-S 24/2.8
STM. These filenames identify the capture setup, not profiles for our lenses.

Each archive's metadata was read and all ZIP CRCs passed. Channels use one-byte
sample words. The original six named probes, with zero-based bit indices, are:

| Bit | Probe |
| --- | --- |
| 0 | BODY_VD_LENS |
| 1 | VCC |
| 2 | LENS_CS_BODY |
| 3 | RXD, lens to body |
| 4 | TXD, body to lens |
| 5 | BODY_CS_LENS |

The independent [sampler](../scripts/analyze_captures.py) gates each direction
by its own CS line, uses F0's five low bit times to distinguish 750 kbaud from
1.5 Mbaud, then samples 8N1 UART data at bit centers. It does not execute or
translate the GPL decoder. Its scope is these 6 MHz recordings, not arbitrary
analyzers or future high-speed protocol variants.

| Recording | Validated frames | Undecodable windows | Complete CS windows without a UART start edge |
| --- | ---: | ---: | ---: |
| a6000_ef50_viltrox_init.sr | 834 | 1 | 4 |
| a6000_efs24_viltrox_init.sr | 620 | 1 | 4 |
| a6000_sel55210_init_210.sr | 724 | 0 | 5 |
| a6000_sel55210_init_55.sr | 398 | 0 | 5 |
| a6000_selp1650_init.sr | 880 | 0 | 4 |

All **3,456 extracted complete frames** passed UART start/stop checks, declared
length bounds, the 0x55 terminator check, and the additive checksum below.
There were no validation failures among those frames. Two early Viltrox
lens-to-body windows lacked a complete F0 sync pattern and remain extraction
errors. Two windows already active at the beginning of recordings were skipped
as partial. A no-data window can be handshake activity; these counts alone do
not label its purpose.

The extracted frames include 30 at 750 kbaud and 3,426 at 1.5 Mbaud, classes
0x01 and 0x02, and types 0x01, 0x03–0x0D, and 0x10. Maximum declared length is
210 bytes. This confirms observed behavior in these recordings; the EA9
reference remains at 750 kbaud and need not adopt native-lens negotiation just
because other lenses use it.

## Frame definition supported by the bytes

For a declared total length `L`, the observed layout is:

```text
offset  0      1..2       3        4          5       6..L-4    L-3..L-2   L-1
        F0     length LE  class    sequence   type    payload   checksum LE 55

checksum = sum(frame[1:L-3]) & 0xffff
```

The checksum covers both length bytes, class, sequence, type, and payload. It
excludes F0, the two checksum bytes, the final 55, and any transfer-window tail.
LexOptical's [Constants.h](../upstream/LexOptical/E-Mount/Constants.h) names a
six-byte header and three-byte footer. Its
[Message.cpp](../upstream/LexOptical/E-Mount/Message.cpp) computes that same sum.
All eight literal initialization replies in Constants.h passed independent
length, terminator, and checksum checks; the results are in
[lexoptical-template-checks.json](lexoptical-template-checks.json).

The old capture README calls the byte after F0 a command ID and describes fixed
command lengths. The decoded bytes and the later code identify that position
as the first length byte. Preserve the original README, but do not turn that
early description into our frame specification.

**395 validated body-to-lens windows have nonzero bytes beyond the declared
frame**. These nonzero tails reach 10 bytes; the longest tail of any kind in the
corpus is 15 bytes. For example, one valid
22-byte 0x04 frame is followed by `00130055000000000000`. This contradicts a
strict zero-only padding assumption in the early documentation. Our sampler
records these bytes without assigning them semantics. Their presence is a
reason to honor the declared frame boundary, not a reason to dispatch them as
additional commands. End-marker bytes also occur inside payloads: do not scan
for the first 0x55 to determine length.

## Decoder: useful, with limits

The [E-mount decoder](../upstream/Entropy512/libsigrokdecode/decoders/sony_emount/pd.py)
is **Python**, integrated with a **C** libsigrokdecode host. It takes raw logic
channels directly (`inputs = ['logic']`); it is not stacked on a separate UART
decoder. Its four channel IDs map to capture probes as follows:

| Decoder channel | Capture probe |
| --- | --- |
| rx | RXD, probe4 |
| tx | TXD, probe5 |
| rx_cs | LENS_CS_BODY, probe3 |
| tx_cs | BODY_CS_LENS, probe6 |

It detects the F0 sync rate inside a CS window, then labels length, class
(`ftype`), sequence (`snum`), speed, direction, extra-byte count, checksum and
remaining data. Its packet buffer omits the already-consumed F0; this explains
the internal one-byte length adjustment. The first byte in its reported `data`
is the message type. Account for this when comparing annotation text to full
frames or payload-only offsets.

It unpacks and displays the checksum; it does not calculate the expected sum
or reject a mismatch. The packet unpacking also assumes enough bytes exist.
Keep it as a historical analysis reference; our parser should have its own
bounded length, checksum and terminator validation. No sigrok runtime replay
was performed here; the retained extractor provides independent byte evidence.

## LexOptical: protocol structure, not EA9 autofocus

The [README](../upstream/LexOptical/E-Mount/README.md) targets Arduino/Teensy 3.5
and reports manual-focus/manual-aperture lens emulation sufficient for a NEX7.
The `.ino`, classes, `Arduino.h`, and `Serial` APIs establish **C++**, not Rust.
The main implementation has no EA9 encoder, PWM motor drive, homing, or servo.
It includes useful header naming, initialization reply examples, status
construction, and a listen-only mode that changes UART speed when it sees 0x0C.

The receive parser in [E-Mount.ino](../upstream/LexOptical/E-Mount/E-Mount.ino)
calculates the two-byte length when `position == 2`, before receiving the byte at
buffer index 2. It also reads but does not verify the incoming checksum. These
are implementation limits, not protocol requirements. Avoid mechanically
porting its streaming parser into the selected implementation.

The additional [traffic repository](../upstream/LexOptical/E-Mount-Traffic-Samples/README.MD)
contains **TypeScript/JavaScript** tools and NEX7/A7 traces, including Voigtlander
15 mm focus/aperture changes and native Sony/Zeiss examples. Its README explains
that timing prints can interrupt messages. Preserve source text and annotate
any repairs instead of silently treating those traces as clean frame fixtures.
The linked [collaborative document](../documents/lexoptical-protocol-document.txt)
credits both @bostwickenator and @entropy512. Its hypotheses and indexing should
be reconciled with the newer EA9 protocol research before using field names as
motor instructions or optical-calibration inputs.

## How to use this for the eventual stack

The stack is undecided; the [product direction](../../docs/product-direction.md)
defines the product and selection process. These findings apply across languages.

1. Use the validated frame records as an initial host-side codec corpus.
   Read length as unsigned little-endian, enforce `9 <= L <= available`, verify
   the checksum/terminator, and preserve the CS-window tail separately.
2. Add intentionally corrupted and truncated cases when implementing the codec.
   These recordings provide positive evidence; they do not cover every failure
   mode or maximum permitted packet length.
3. Keep raw-frame offsets, payload offsets, and decoder annotation offsets
   explicit in field specifications. Track the capture, direction, sequence,
   and sample range supporting each interpretation.
4. Port the EA9 transport and motion responsibilities using its hardware map,
   while keeping framing and profile serialization in host-testable modules.
   Evaluate code sharing after choosing firmware and host stacks. Camera
   measurements, optics, and motor calibration remain separate.
5. Collect our own stock-1.8.0 A7C II traces before claiming camera compatibility
   or focus improvements. Test metadata and optical behavior with the user's
   actual C/Y lenses, especially the zoom and macro.

The retained old-camera traces help establish bytes and behavior. They do not
justify invented Contax optical tables, guarantee modern video AF, or replace
measurements of this camera and adapter.
