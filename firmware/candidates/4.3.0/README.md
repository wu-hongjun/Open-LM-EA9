# Motor-disabled startup probe 4.3.0

The probe isolates the E-mount startup exchange on the Sony A7C II. It uses
stock LM-EA9 adapter identity and stays at 750 kbaud. USB loader metadata says
4.3.0 so the native tools can identify this exact probe. Camera-side
identification reports adapter class 2, ID `0x00EA`, version 1.8, protocol
grade `0x0108`, stock capabilities and the name `TECHART LM-EA9`. The stock
speed advertisement is retained. The reply to `0x0C` is `00`, and SERCOM1
has a single baud register setting of `0xC000`.

- [Upload image](startup-probe.bin) is 20,480 bytes at `[0x5000,0xa000)`.
- [Manifest](manifest.json) pins the binary, sources and generated inputs.
- [Source](../../startup-probe/) uses the pinned upstream C reset and linker
  scaffolding, a dedicated bounded transport and reply logic derived from the
  [public stock application](../../recovery/stock-1.8.0/application.bin).
- [Background and reproduced 4.2.0 failures](../../../docs/audits/a7c-ii-november-handshake-2026-11-06.md)
  explains the experiment.

The app disconnects the four PWM pads from peripheral control and configures
them as inputs at the start of `main`. It holds PA16 low because its role is
unconfirmed and omits the stock's later high transition. PA23 is held low. The
image links no motor drive, position sensor, homing, park or AF controller.
Those GPIO choices and the existing bootloader have no new electrical
qualification. This is a startup diagnostic. Status uses stock nominal f/2
and fixed position placeholders. It does not sense position or iris, send AF
completions, operate a diaphragm, or implement normal capture and re-arm.
The physical lens's focal and aperture settings are outside this experiment.

## What the trace measures

The receiver is armed before lens CS rises. A clean, aligned prefix already
received by the first rising edge survives, and a latched first falling edge
can close the initial window. The lens holds the startup CS signal for 50 ms
from the observed first close, then releases it when body CS is clear. During
normal framed receive, the parser checks the start byte, declared 16-bit
length, checksum and terminator, then checks the supported request shapes.
Padding after the declared frame is ignored. An unknown init ID with a valid
envelope is logged as receive evidence. The single pending mailbox keeps its
first request and counts overflows.

The diagnostic distinguishes these marks. Times are firmware SysTick
milliseconds from app startup, with RX time sampled at body CS close and TX
time sampled at the UART's TXC flag.

| Mark | What it records |
| --- | --- |
| Last valid init RX | Last accepted init envelope before the first completed `0x0A` echo. Shutdown is excluded. This mark can advance even if there is no reply. |
| Last paired RX and TX | Request ID, length and time alongside the corresponding reply's ID, length and TXC time, committed only after the local hold and lens CS release. |
| Last init TXC | Last init reply that reached the UART's TXC flag. This can advance even if the hold was interrupted. |
| First normal RX | First framed `0x03` or `0x04` of an admitted length after the completed echo. Its payload is ignored. |

An exact 25-byte `0x0A` is echoed byte for byte. Only a completed local echo
enables the VD-driven `0x05` and `0x06` status loop and freezes the init
marks. Separate flags identify whether the capabilities reply, identity reply
and first status pair completed locally. Normal traffic provides evidence of
the next phase. It does not establish that the body accepted each reply or
that the shutter and shutdown work. The responder echoes framed `0x16` and
quiesces after local release, with no park request. It uses bounded waits for
the first CS/hold window (8 s total), inactivity (4 s), unfinished init (12 s
from bus ready) and peripheral synchronization.

One 64-byte CRC-protected record can be appended on terminal inactivity,
timeout, transport fault, or completed shutdown echo. The firmware quiesces
the link before touching flash. It uses only page-buffer clear and page
program inside `[0x9c00,0xa000)` and appends beyond the last occupied page,
including torn pages. There are 16 slots. There is no runtime erase,
retry, startup storage gate, or write on a silent USB-cap boot. The record
contains only message IDs, lengths, timing, counters and phase flags. It
contains no frame contents, sequences or unit identifiers. If the body cuts
power before a terminal write completes, the page can be missing or torn.
An empty log cannot identify where the link stopped. A passive bus trace
would still be needed to measure physical line levels and timing.

## Reproduce and verify offline

Use the pinned ARM, Microchip DFP and CMSIS versions in
[dependencies.json](../../dependencies.json), the existing REA Unicorn
environment, and a Git checkout with upstream commit `e054db9`.

```sh
build=artifacts/private/startup-probe-rebuild
python3 scripts/build-startup-probe.py --checkout CHECKOUT --output "$build"
cmp "$build/startup-probe.bin" firmware/candidates/4.3.0/startup-probe.bin
cmp "$build/manifest.json" firmware/candidates/4.3.0/manifest.json
python3 scripts/test-startup-probe.py "$build"
tools/rea-analysis/venv/bin/python scripts/test-startup-probe-arm.py "$build"
scripts/swift-local.sh test
```

Two clean builds matched. Host tests run the production parser and responder
under ASan/UBSan against synthetic startup and failure cases, including the
six-byte final header, corrupt frames, a shifted reply without clean CS
release, and full and torn log storage. The decoder exercises a C-generated
record and rejects bad native manifests, CRCs, impossible records, and
altered immutable firmware. Linked ARM instructions pass early-opener,
CS-arbitration, motor-pad and NVM-address controls in Unicorn. The native suite
covers pinned source admission and full application/protected-data readback,
including rejection of a pre-camera nonblank diagnostic tail. These tests
supply peripheral register behavior and do not qualify the camera, motor
electronics, or flash programming under power loss.

## Separate hardware session

Use the source-built `ea9ctl`. The guarded upload accepts the exact installed
4.2.0 trial or the recognized stock 1.8.0 application from a fresh same-unit
backup and requires the existing stock-upload qualification. Confirm the
same-unit original [recovery](../../recovery/stock-1.8.0/README.md) is available
before starting. Close both apps and attach through the USB update cap.

1. Run `ea9ctl apply-startup-probe --idle` only in the separate upload session.
   Physically disconnect and reconnect the same unit after upload.
2. Run `ea9ctl verify --idle` before mounting the adapter. This compares the
   complete application including the erased log tail, loader metadata, and
   protected data against the upload plan and backup.
3. With the camera off and its USB cable disconnected, mount the adapter and
   switch on once. Observe the live preview and aperture display. Leave the
   shutter and AF-ON untouched. If the camera is responsive, wait about
   ten seconds and switch off once. If it freezes or shows unexpected motion,
   switch off, remove the battery if necessary, and end the trial.
4. With the camera off or unpowered, return the adapter to the USB cap.
   Save a new private two-pass backup and decode it without USB access.

```sh
ea9ctl backup artifacts/private/NEW.ea9backup --idle
python3 scripts/decode-startup-probe.py artifacts/private/NEW.ea9backup
```

Keep the original backup files private. Use `backup` after the camera session
because the diagnostic tail may differ from the verified installation. Report
the latest valid slot and any torn pages. A completed local echo followed by
`0x03` or `0x04` would move the compatibility investigation beyond startup.
A stalled last exchange identifies the point to compare with stock on the
same body. The later [camera evidence](../../../docs/evidence/startup-probe-43-2026-11-06.md)
records a completed final echo, a normal body frame, and a subsequent
transmit fault. The image itself remains pinned to the offline build.
