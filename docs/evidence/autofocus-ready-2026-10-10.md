# AF candidate readiness — 2026-10-10

The Contax Zeiss 50mm f/1.4 candidate is packaged and admitted to the native
upload/reconnect-verification/restoration workflow. **No AF upload or camera test
was performed.** The final OS inventory found zero USB-cap adapters and sent no
HID reports. The previously verified installation remains metadata-only 2.0.0.

## Candidate and provenance

| Item | Value |
| --- | --- |
| App | 0.4.0, build 7; SwiftUI/AppKit/IOHID |
| Firmware | C, inherited upstream AF controller plus lifecycle/I/O guards |
| Loader / camera version | 2.1.0 / 2.1 |
| Application/profile addresses | `0x5000` / `0xa000` |
| Personalized length | 20,736 bytes; 325 upload reports planned |
| Profile | Contax Zeiss 50mm f/1.4; 50 mm; reported AV 4352 |
| AF template SHA-256 | `6e48fcdd48df13ec529badd4626ee99120e005e4cd011ad664c683720b006552` |
| AF image SHA-256 | `dc21166cdd87727188d20738581eb911b387714660d5de263fa7dac8b3b2a131` |
| Metadata template SHA-256 | Unchanged: `d7f85bb53897d6b83f30c528d7790ec37e7164090d882251b917060cc300f293` |

The candidate and adjacent manifest are under
`artifacts/firmware-milestone/af-ready-2026-10-10/`. The release CLI's `prepare-af`
output matched the independently prepared Python fixture byte for byte and
passed the actual C profile decoder/camera-packet checks. Its adjacent manifest
and [machine-readable evidence](autofocus-ready-2026-10-10.json) include hashes,
source provenance and qualification flags. Diagnostic flash writers are excluded
at link time. The build has 17,880 bytes of text, 1,280 bytes of initialized data
and 9,656 bytes of BSS including the 8 KiB stack reservation; application code
fits before the fixed profile row. Linker no-syscall warnings concern discarded
library stubs; host register shims also produce a section-alignment warning.
Neither warning was a test failure.

## Safety work and audit

The continuing user-authorized Astra audit found and root fixed these paths:

- A timed-out moving/noisy homing stage could have declared infinity. Both drive
  and settle now require stationary observations, not just deadline expiry.
- SPI/ADC faults could block a motor stop. Register waits use a 2 ms deadline plus
  100,000-poll fallback; faults latch and GPIO release has no PWM dependency.
- UART transmission, RX interrupts and delays reached during motion could block
  return to the controller. AF-only guards bound these paths; motion/ADC bursts
  have a 1,000,000-iteration fallback and RX ISR has a 512-byte budget.
- Shutdown could release then briefly reconnect stale PWM during servo cleanup.
  A motor inhibition latch prevents reattachment until reset.
- An encoder fault on the post-servo final report could return successful
  completion. The final admission check now rejects that result.
- UART IRQ fault release could race with foreground remux. Saving/restoring
  PRIMASK around the fault check and remux closes that boundary; the volatile
  fault mask's OR also preserves IRQ state.
- Unknown/pending firmware could display metadata-only behavior. The UI now
  explicitly distinguishes verified AF, verified metadata-only and unverified
  states, and allows same-lens AF→metadata fallback.

The source re-review found no remaining P1 implementation blocker in these
changes. This is code review and host evidence, not a safety certification or
physical qualification. Startup clock/UART/EIC liveness waits remain with motor
outputs released. Stable sensor data does not prove a true mechanical endpoint,
and no independently qualified watchdog was added. Original factory arithmetic
from REA remains documented separately; this candidate retains upstream tuning.

## Verification

All checks passed:

- 28 Swift tests, with both firmware variants exercised for exact writes,
  cancellation/lost ACK, reconnect/protected-range/factory verification, journal
  reload and rehashed code tampering. New checks cover AF fingerprint/version
  disagreement, firmware history, AF backup admission, rejection as an original
  stock source, and a complete simulated AF→metadata fallback.
- Inherited E-mount, servo, no-body, slow-body, startup rescue, distance/map and
  prediction tests; 65,927 AF target-bound cases and sticky-state cases.
- Four deadline/frozen-time/wrap tests for the real wait guard.
- Eight cases using actual `main.c` homing/focus/shutdown paths: normal home,
  pre-drive ADC fault, encoder fault while homing, shutdown while homing, drive
  timeout while still moving, ADC fault during focus, fault only on a successful
  move's final report, and settle timeout while still moving. These also passed
  AddressSanitizer and UndefinedBehaviorSanitizer.
- Eleven cases compiling actual encoder/ADC/PWM/UART drivers against register
  memory with the official DFP types: stuck encoder transfer/reset, stalled ADC,
  frozen-time ADC burst, stuck UART TX/RX, stuck PWM synchronization, no-wait
  release/shutdown inhibition, pending IRQ during attachment, pre-masked IRQ state
  preservation, and frozen-time encoder transfer. Faulted drivers cannot remux or
  poll PWM on subsequent motor commands.
- Two actual delay implementations with frozen SysTick, proving return and release.
- Seven prime/macro profile fixtures for each firmware variant, corruption checks
  and transmitted focal/aperture/name/checksum checks. Zoom qualification is pending.
- Release app/CLI packaging, strict local signature verification, and native UI
  inspection: disconnected state, unverified behavior, AF/metadata actions and
  disabled hardware operations without a qualified connection.

Logs: [firmware build](af-ready-firmware-build-2026-10-10.txt),
[firmware tests](af-ready-firmware-tests-2026-10-10.txt),
[Swift tests](af-ready-swift-tests-2026-10-10.txt),
[Mac packaging](af-ready-macos-build-2026-10-10.txt).

## Restoration evidence and next physical step

The preserved original same-unit backup was rechecked offline: all manifest
files matched, flash SHA-256 remains
`1aa89de1e58ab993fc28a201fc1c651ce1c333df0dc6f16b548294030bf5cd01`, and its
20,172-byte application matches recovered official 1.8.0. The private source path
is recorded separately. Stock application upload/readback was verified earlier;
AF-to-stock restoration and power-loss recovery have not been tested on hardware.

[Follow the AF-S runbook](../af-s-test.md) after connecting the actual adapter
through its update cap. It covers installation, physical reconnect, byte
verification, startup/shutdown, the first AF-S acquisition, retained photographs,
metadata-only fallback and factory restoration. Missing observations remain
explicitly unverified in [the result template](af-s-camera-result-template.md).
