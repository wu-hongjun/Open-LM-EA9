# AF 2.6 firmware size and performance audit — 2026-10-12

The lowest-risk measured improvement is to stop collecting and scanning raw diagnostic captures in the release build. The release already removes flash logging, but volatile capture writes and diagnostic-only foreground branches survive. Gating these blocks with the existing `EA9_NO_LOG` option saves **640 bytes of initialized flash and 620 bytes of static SRAM** at the same `-O2` setting and toolchain. The isolated proposal passed the existing offline behavioral checks with unchanged output. It does not establish optical autofocus or camera exposure equivalence.

## Scope and reproducibility

Audited commit: `d023745022e9375c54282221be8d6fee4df2ad61`. Production source, Makefile, resources, trusted pins, candidates and recovery images were not edited by this audit. No hardware reports, USB checks or uploads occurred.

Experiments are confined to ignored `artifacts/af26-night-optimization/`. Each variant copies `firmware/ea9/src`, host test sources and the current Makefile. Only the dependency path is made absolute to build from this location. The compiler remains Arm GNU 14.2.rel1, Cortex-M0+, Thumb, `-O2`, function/data sections and linker garbage collection. Builds retain `EA9_NO_LOG`, the factory controller, camera version `0x26`, application origin `0x5000`, and profile origin `0x9f00`.

The unmodified copy reproduced the trusted template exactly:

`276a134db2db04e4ea41e6bfb622e0b4f3c5421a6e3bfb6e40428cfce07fe265`

This matches [the public build manifest](../evidence/af-audited-build-manifest-2026-10-11.json) and the app's frozen AF 2.6 trust pin.

## Measured layout

Flash margin is `0x9f00 - (_etext + SIZEOF(.relocate))`; it excludes the profile row. Static SRAM is `_ebss - 0x20000000`, including initialized data and BSS. It excludes the separately reserved 8 KiB stack. Binary files remain 20,480 bytes because the profile row stays at the same address and unused flash is gap-filled.

| Isolated variant | Initialized flash end | Flash margin | Static SRAM | Stack top |
| --- | --- | ---: | ---: | --- |
| Original AF 2.6 | `0x9f00` | 0 B | 2,812 B | `0x20002b00` |
| Raw captures gated | `0x9e64` | 156 B | 2,192 B | `0x20002890` |
| Foreground diagnostic block gated | `0x9d1c` | 484 B | 2,812 B | `0x20002b00` |
| Both changes | `0x9c80` | **640 B** | **2,192 B** | `0x20002890` |
| Both changes plus release RX poison disabled | `0x9c6c` | 660 B | 2,192 B | `0x20002890` |

The combined proposal's template SHA-256 is `9270a43f5ab1f43a26795dfb921e834f2c53bd085a56cc62d62ae1c7b049b27f`. This is an experimental image, not a prepared or trusted release.

## Recommended changes

1. In `emount.c:on_cs_edge`, enclose only the pre-handshake raw frame capture and the normal-traffic raw frame capture blocks in `#ifndef EA9_NO_LOG`. Keep frame admission, sequence tracking, request snapshots, command parsing, negotiation and all safety checks active. The two raw arrays total 612 bytes; the measured layout reduction is 620 bytes after dead sections and alignment are considered. Foreground trail functions are already no-ops in this configuration and provide no consumer for these arrays.
2. In `main`, enclose the diagnostic-only work between `em_poll()` and the homing/command-service block in `#ifndef EA9_NO_LOG`. This covers failed-handshake capture flushes, flash milestones, delayed capture flushes and quiet-period logging. These conditions perform no motion policy in this revision. Keep `em_poll()`, homing, feedback publication, query service and `focus_service()` outside the guard.
3. Place the associated `hs_marked`, `caps_flushed`, `caps_written` and `quiet` locals, plus `g_qidlog_written`/`quiet_idlog_page`, under the same guard. This avoids new unused-variable/function warnings. Experimental C compilation passes `-Werror`. Existing nosys link warnings are unchanged.

The exact shared-workspace patches are `artifacts/af26-night-optimization/proposed-emount.patch` and `proposed-main.patch`. The complete modified source is in the `combined/` experiment. These files are intentionally ignored; the boundaries above describe the changes for a fresh checkout.

The callback law in `factory_af.c`, wrapper in `factory_servo.c`, motor/encoder/ADC drivers, clock and delay routines, packet table and aperture module remain byte-for-byte identical as source inputs. No stock unknown field, `0x34` echo, optical row, PWM limit, timeout, completion outcome or fault latch is changed by the proposal. Removing diagnostic work reduces overhead; actual hardware scheduling changes have not been measured, so do not claim identical timing.

Preserve the frozen 2.6 resource and candidate. If integrated, the modified image needs its own release identity, manifest, pin, native/Python preparation comparison and camera-test record.

## Offline equivalence checks

`artifacts/af26-night-optimization/run-equivalence.py` built baseline and combined copies using host Clang `-O1`, AddressSanitizer and UndefinedBehaviorSanitizer. Both variants passed **68 runs**, and the stdout of every corresponding run matched exactly:

- Existing E-mount suite, including diagnostic raw-capture expectations with logging enabled.
- Production opaque `0x34` query/snapshot/transmit test.
- 13 legacy and 11 factory lifecycle scenarios.
- 21 hardening scenarios for each controller backend, including command replacement, Stop/shutdown ownership and invalid feedback.

The motion suites use `EA9_NO_LOG`, so they exercise the capture gate in the same configuration as the ARM release. The inherited protocol suite deliberately retains diagnostic behavior when the macro is absent. Test transcripts and per-run output hashes are in ignored `equivalence.log` and `equivalence.json`. These checks execute production functions used by the motion dispatcher; they do not exhaustively simulate an entire infinite foreground loop or the physical interrupt/peripheral schedule.

A subsequent warning cleanup only gated the unused diagnostic locals/helper. The measured combined binary hash remained identical, so no new firmware behavior was introduced by that cleanup.

## SRAM and stack assessment

The original layout reserves 8,192 bytes of stack from `0x20000b00` to `0x20002b00`, leaving 5,376 bytes beyond the stack in the 16 KiB SRAM bank. The proposed layout retains the same stack reservation; SRAM savings move the stack down rather than reducing its allocation. No heap allocator is linked in the reviewed release symbol map.

An isolated `-fstack-usage` build produced exactly the same combined binary hash. The largest compiler-reported single frames are `focus_exec` 120 B, `focus_run` 104 B, `park_to_infinity` 96 B, `main` 80 B, and `factory_servo_move_to`/`on_cs_edge` 72 B each. All emitted application reports are static. These are individual function frames, **not** a whole-program stack bound; callbacks, nested protocol service and interrupt exception frames must be added. There is no measured stack high-water result. Do not shrink the reserved stack based only on these numbers.

Retain the linker profile-overlap assertion and RAM-region bounds. Add an explicit build-layout report or regression budget for initialized flash margin, live SRAM and stack reservation: the current 2.6 margin of zero gives no room for another linked instruction or data word, although the image itself still fits. This is a maintainability problem, not evidence that the existing image overlaps its profile.

## Additional options and limitations

The receiver's 64-byte diagnostic poison fill can also be gated for `EA9_NO_LOG`. A copied variant saved another 20 flash bytes, giving 660 bytes total margin. The validated frame path only examines received bytes and `g_rx_len` resets at the start of every window, making this a plausible optimization. It was built and measured, but this audit did **not** establish an actual-driver hardware/reset equivalence test for that change; keep it separate from the recommended two-block optimization.

Further histograms, aperture-request counters, ID logs and timestamps remain volatile in release. Some feed test observability and others share data with live control logic: `em_vd_edges` drives velocity history and `em_frame_period_ms` drives prediction, for example. Do not remove diagnostic declarations wholesale or redefine them as ordinary variables. A later pass should classify each field and retain faults and live telemetry explicitly.

Avoid changing optimization level, enabling LTO, removing supply samples or replacing blocking UART with DMA in the same polish round. Those can affect instruction timing, control scheduling and faults much more broadly than gating disconnected logging work. The original initialization/status gaps, bounded I/O waits, controller law and opaque protocol behavior deserve independent acceptance checks if changed.

Finally, source comments still describe the responder as unable to handle focus commands and the application as a small scripted mechanism test; those descriptions are obsolete. `em_uart.c` also calls its RX handler a two-instruction ISR with three orders of magnitude of headroom, while the generated handler includes buffer bookkeeping, diagnostics, an error path and a bounded-loop guard. Update those claims to describe the actual architecture and measured limitations; no ISR cycle budget or camera-qualified timing was established here.
