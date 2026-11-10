# 4.8.1 motion diagnostic hardware record

The owner authorized installation through the USB cap for a Biotar 58mm f/2
and bare-adapter comparison on the A7C II. Both apps were closed. The signed
CLI used installer commit `6ef14fb`. All 77 native tests passed before USB
access, including the diagnostic plan and readback rejection controls.

The fresh two-pass preflight matched the reviewed plan on the qualified unit.
It admitted the pinned 4.8.0 code and bank, a committed Biotar selection at
sequence/generation 3, and two blank, unlocked diagnostic trace slots. The
durable intent was saved before START. One START and 832 application pages
were acknowledged at 23:52 EST on November 9 (04:52 UTC November 10). The
sequential payload was 53,248 bytes
from `0x5000` to `0x12000`, with the preserved gap included. No reports followed
the last page.

After the owner confirmed a physical reconnect, two matching full reads
verified 4.8.1 at 00:21 EST on November 10 (05:21 UTC). Both code segments
matched their published pins. The Biotar remained committed, and the mailbox,
journal, bank, preserved gap, upper flash and protected auxiliary data matched
the preflight. Flash geometry and lock bits matched. Both trace slots were
empty. The Biotar camera test is next, followed by its trace read and the
bare-adapter comparison. Raw flash, traces, identifiers and approval digests
remain private.
