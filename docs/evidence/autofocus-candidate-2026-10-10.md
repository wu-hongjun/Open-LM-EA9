# Offline autofocus candidate — October 10, 2026

The first opt-in upstream-AF candidate was compiled and checked offline. It was
not uploaded, and no HID report, updater launch or hardware motion was performed.
The installed 2.0.0 metadata firmware and app upload admission remain unchanged.

| Measurement | Result |
| --- | --- |
| Target | SAMD21E17A, Cortex-M0+, application at `0x5000` |
| Binary/profile layout | 20,736 bytes; 256-byte profile at `0xa000` |
| AF template SHA-256 | `46d7c9aa44aae39b66bdaffc00df9a7c083fccd5acb8822901c8863dcb9208c7` |
| Contax 50mm f/1.4 AF image SHA-256 | `62a8d1f0490a05a50eb52d1aa6fa0aecac64d2352f4ff4ab179298305117aa70` |
| Camera version / proposed loader version | `0x21` / 2.1.0; no loader START sent |
| Arm size: text / data / bss | 16,172 / 1,280 / 9,648 bytes |
| Stack reservation | 8,192 bytes, included in bss; no runtime high-water measurement |
| Servo and drive symbols | Present; required by AF link checks |
| Diagnostic flash-writer symbols | Absent; enforced by link checks |
| Existing metadata template | Rebuilt and still SHA-256 `d7f85bb53897d6b83f30c528d7790ec37e7164090d882251b917060cc300f293` |

Validation completed:

- `python3 scripts/test-firmware.py --af`: inherited framing/shutdown, servo,
  no-body/slow-body, initialization, position/distance/prediction checks passed.
- The new command module passed 65,927 bounded target cases, no-target sentinel
  rejection, Stop versus motion-fault behavior, sticky failure state, exclusive
  motion admission and shutdown admission.
- AddressSanitizer and UndefinedBehaviorSanitizer passed for the actual command
  and state module. Extreme signed feedback, wire deltas and defocus multipliers
  are covered.
- Seven Mac-generated prime/macro metadata fixtures and seven AF fixtures passed
  the actual C profile decoder, all 256 single-byte corruption checks, transmitted
  focal/aperture/name and frame checksums. AF response 07 reports version `0x21`.
- Both linker memory bounds passed. Python build/preparation/test scripts compiled
  without syntax errors. Documentation whitespace checks passed.

The Arm linker reports inherited bare-metal `_close`, `_lseek`, `_read` and
`_write` stub warnings. Native host builds retain the inherited common-section
alignment warning. These were not hidden or treated as camera qualification.

This validation exercises the actual servo on the upstream simulated mechanism
and the extracted command/state policy. It does not execute this fork's full
`main.c` against hardware or an emulated camera/peripheral system. SPI/ADC waits,
homing reference/end-stop assumptions, motor polarity/load, real protocol timing,
optical calibration and A7C II focus accuracy remain open. The observed simulator
arrival error belongs to that model, not this adapter.

Generated templates, personalized binaries, maps, logs and manifests are local
under `firmware/ea9/build/af` and `artifacts/firmware-milestone`, excluded from Git.
The source manifest hashes are retained in the
[machine-readable record](autofocus-candidate-2026-10-10.json). Reproduction,
design decisions and next implementation work are in the
[AF milestone](../autofocus-milestone.md). The separate Astra REA lane's factory
results are in [the official AF dossier](../reverse-engineering/stock-phase2.md).
