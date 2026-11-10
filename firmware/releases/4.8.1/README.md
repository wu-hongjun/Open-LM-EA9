# 4.8.1 LM-EA9 motion diagnostic

This is a bench candidate based on the pinned 4.8.0 profile-bank firmware.
The A7C II owner reported that the Biotar 58mm f/2 stayed soft on a distant
target in MF at f/2 with the lens at its infinity stop. In AF it hunted
without locking and the mechanism jittered. The earlier two-pass USB backup
confirmed the Biotar selection was committed and the 4.8.0 code, bank and
protected data matched the verified install. The physical stop and the cause
of the jitter are still unmeasured.

The candidate preserves the 4.8 profile behavior, motor duty and thresholds,
focus mapping, E-mount protocol and shutdown sequence. Its added sampling can
affect timing. It neither calibrates the mechanical stop nor changes how the
firmware decides that homing succeeded. In an offline control, the unchanged
homing loop could set zero at a blocked position or after its 300 ms drive cap
while still short. The diagnostic makes those cases distinguishable from a
normal homing trace when there is a reference from the same unit.

## What it records

- The native 14-bit encoder at drive start, drive exit, settle start, settle
  exit and at the exact sample used to reset the tracked origin. Drive and
  settle exits distinguish the stillness rule from the time cap. Both phases
  also sample the raw encoder about every 20 ms. Raw readings wrap at 16384.
- Decoded focus commands as the controller consumes them, including Stop,
  relative/defocus operands, Scan and Drive. Commands overwritten in the
  protocol mailbox before consumption are outside this trace.
- For AF legs, the requested target, measured start and end, terminal servo
  outcome, signed drive duty and actual position about every 20 ms. The trace
  also records accepted retargets, changes in nonzero drive polarity, and
  moves skipped by the deadband. A Drive or Scan can span multiple records.
  Servo samples represent the regular control-step output. Short brake pulses
  and park are outside the AF stream.

The RAM buffer retains up to 48 homing records and the last 192 AF records;
the decoder reports how many AF records were dropped. Read raw counts before
and after homing first. Then check whether direction changes follow new
commands and accepted retargets, or occur while the effective target stays
fixed. A motor reversal alone says nothing about whether the subject was
sharp. A repeatable raw origin alone cannot establish that the reference is
the physical end stop.

## Storage and decoding

The candidate reserves two 4 KiB trace slots in `0x14000–0x16000`. The outer
main loop saves at most one snapshot per boot after the shutdown echo, PA23
signal and return from any nested motion. No trace writes run during homing,
AF or capture. A battery pull or power cut before this path can lose the whole
RAM trace. Power loss during the save can leave a partial slot.

The writer never erases trace flash. It skips any slot containing a programmed
byte, writes at most 61 pages to one erased slot, verifies each page by reading
it back and writes the checksummed commit header last. It uses the existing
SAMD21 SRAM NVM command path and bounds writes to the trace region. After both
slots are occupied, later sessions make no trace writes. Each slot holds a
64-byte header, homing records at offset 64 and AF records at offset 832.
Records are 16 bytes in little-endian order, with time, event type, detail,
auxiliary value and two signed data words. The header pins each payload with
a CRC32 and identifies the ring length and total AF records seen.

After verified installation and a normal camera shutdown, take a two-pass
read-only backup via the USB cap. Decode it locally and keep the flash and
decoded trace private.

```sh
python3 scripts/decode-motion-diagnostic.py /path/to/session.ea9backup
```

The decoder reports empty, incomplete, invalid or complete for each slot.
It can read a full 128 KiB `flash.bin` from the same backup.

## Installation boundary and planned test

The dedicated CLI installer accepts only the pinned diagnostic package.
The two pinned segments replace application code at `0x5000–0xa000` and the
extension at `0x10000–0x12000`. The package omits the live bank, journal,
metadata and trace slots. The installer admits exact 4.8.0 code and bank with a
committed profile, verifies blank and unlocked trace storage, and preserves the
live selection and all existing unit data. The sequential loader rewrites the
preserved gap with its original bytes. See the
[installer and reconnect verification](../../../docs/motion-diagnostic-install.md).

For the first slot, use the Biotar with the same converter and the camera
supported in a fixed orientation. With the physical iris at f/2 and lens ring
at infinity, let startup finish with MF and Pre-AF Off. Check the same distant
target with Focus Magnifier. If the camera and motor are responsive, switch to
AF-S for one short half-press on the same target, release and shut down
normally. No exposure is required. Take a read-only backup after shutdown.
For the second slot, remove the lens and converter with the camera off and
repeat startup and shutdown bare in the same orientation without AF input.
Compare the raw origins on that same unit. If the loaded origin is farther
out, we have direct evidence of a load-dependent retraction difference. A
matching origin leaves the common mechanical stop and the optical mount
stack to distinguish with an independent reference.

## Offline verification

```sh
python3 scripts/build-motion-diagnostic.py --output artifacts/private/motion-481
python3 scripts/test-motion-diagnostic.py --build artifacts/private/motion-481
make test
```

The targeted test requires Unicorn for Cortex-M0 emulation. It runs the
compiled homing, command-consumption, retarget and servo code with synthetic
peripherals and compares the resulting records with the decoder. The NVM
controls exercise both slots, page bounds, the final commit, ring wrap,
corruption, partial snapshots, dirty slots, locks, stuck READY and command
errors. The published segments reproduced byte-for-byte. The targeted test,
the existing compiled profile NVM checks against 4.8.1 and `make test` passed.
These checks do not establish real NVM timing, camera stability or full
retraction on the owner's adapter. No USB reports were sent for this build.
