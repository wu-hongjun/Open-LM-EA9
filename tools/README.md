# Read-only USB-cap research tools

The production firmware stack remains undecided. The native Mac prototype now
has its own Swift IOHID service; the C probe below remains the original research
tool. See [the app guide](../docs/macos-prototype.md) for build and usage.

## Native IOHID probe

```sh
clang -std=c11 -Wall -Wextra -Werror tools/ea9_readonly_probe.c \
  -framework IOKit -framework CoreFoundation \
  -o /private/tmp/ea9_readonly_probe

/private/tmp/ea9_readonly_probe inventory
/private/tmp/ea9_readonly_probe check
/private/tmp/ea9_readonly_probe read 0x5000 64 /private/tmp/ea9-app-vectors.bin
```

Inventory filters VID/PID `0483:575A`. Requests require exactly one device,
product `LM-EA9`, and 64-byte input/output report sizes. CHECK and whitelisted
memory READ are the only implemented commands. There is no START,
firmware DATA, arbitrary-report, feature-report, reset or application-run mode.
Do not run another updater concurrently or use this probe during an upload.
The stock loader interprets every report as image data once an upload is armed.

READ must start on a 64-byte boundary, use a positive multiple-of-64 length,
and fit below the reference map's `0x20000` guard. That guard does **not** query
physical flash capacity. Use only established ranges on the selected device.
The follow-up measures this unit's 128 KiB capacity and reads the complete
`[0, 0x20000)` range twice. Every memory-read session also requires the inspected
stock `1.8.0` CHECK triplet; another firmware/loader must be qualified separately.

Named snapshots allow only the fixed windows qualified in
[the follow-up](../docs/usb-cap-followup.md):

```sh
/private/tmp/ea9_readonly_probe snapshot device-id /private/tmp/ea9-device-id.bin
/private/tmp/ea9_readonly_probe snapshot nvm-status /private/tmp/ea9-nvm-status.bin
/private/tmp/ea9_readonly_probe snapshot user-row /private/tmp/ea9-user-row.bin
/private/tmp/ea9_readonly_probe snapshot calibration /private/tmp/ea9-calibration.bin
/private/tmp/ea9_readonly_probe snapshot port-a /private/tmp/ea9-port-a.bin
```

There is no arbitrary register-address mode. The device-ID window excludes
DSU debug mailboxes. Register reads occur a byte at a time; GPIO input snapshots
are not atomic or analog voltage measurements. Save all raw output privately.

Every read session first requires a valid CHECK reply. Output uses native
report ID zero with 64 payload bytes; no Linux hidraw prefix is included.
An unsolicited/malformed report or timeout ends the session without retries.
READ replies are untagged, so reconnect/resynchronization after an uncertain
operation must not be improvised. Save transcripts privately: the metadata
contains a device serial string, and replies contain proprietary flash bytes.

The output file is created exclusively only after the entire read succeeds.
The real-device results and file hashes are documented in
[the investigation](../docs/usb-cap-investigation.md). macOS access may be
restricted by an execution sandbox; enumeration failure does not establish
that the adapter is absent.

## Offline backup verification

For the app's versioned `.ea9backup` package:

```sh
python3 tools/verify_macos_backup.py /path/to/backup.ea9backup
```

It verifies sizes/digests, loader/chip/geometry and recorded scope/counts without
USB access or serial-number output. It does not authenticate the manifest or
independently establish its claimed hardware-read history. The older research
transcript verifiers below support the previously collected evidence layout.

```sh
python3 tools/verify_ea9_backup.py references/private/usb-cap-followup-2026-10-10 \
  --stock references/private/techart/stock-1.8.0/EA9-VER-1-8-0.bin \
  --previous references/private/connected-device-2026-10-10 \
  --output /private/tmp/ea9-verified-summary.json
```

This checks every request/reply against the whitelist, reconstructs dump files
from replies, compares both reads, verifies capacity and installed firmware,
and produces a summary without serial strings or proprietary image bytes.
It does not connect to hardware or prove that a backup can be restored.

To reproduce the post-reconnect comparison:

```sh
python3 tools/verify_ea9_reconnect.py references/private/usb-cap-reconnect-2026-10-10 \
  --baseline references/private/usb-cap-followup-2026-10-10 \
  --output /private/tmp/ea9-reconnect-summary.json
```

This compares identity, a full flash pass, vectors and named snapshots to the
earlier evidence, and checks every CHECK/READ report. The unplug event is the
user's report; the new registry entry and repeat reads are measured evidence.

## Offline Thumb disassembly

```sh
python3 tools/disassemble_thumb_image.py /path/to/flash.bin \
  --base 0x5000 --output /private/tmp/ea9-app-disassembly.txt
```

This wraps the raw bytes in an analysis-only ELF, invokes Xcode's LLVM
disassembler for Thumb Cortex-M0, and annotates PC-relative literals. It never
executes firmware. Choose base zero for a bootloader dump. Linear disassembly
also decodes data as instructions; trace reachable code before interpreting
the output. The generated ELF is not a flashable image.
