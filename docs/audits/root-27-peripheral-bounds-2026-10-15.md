# Root follow-up 27 — compiled peripheral polling and fail-stop GPIO

This is a root-run extension, **not another completed Astra lane**. It executes
the exact published upstream C 3.5 image under Unicorn with supplied MMIO. No
hardware was enumerated, opened or controlled; no image, manifest, recovery or
canonical state changed. The [runner and result](../../firmware/upstream-hardening/followup/27-peripheral-bounds/)
bind the published image, full build manifest, all 46 source hashes and reviewed
symbol addresses. Instruction bytes are loaded from the public image.

## Tested contract

Eight stuck-peripheral scenarios reach the correct production `st_fail` reason:
DFLL readiness; encoder SPI DRE, RXC and software-reset completion; TCC compare
synchronization; UART DRE and TXC; ADC result readiness. Each uses the actual
compiled **4,194,304-iteration** wait budget, without shortening its counter or
delivering SysTick interrupts. A separate 40,000,000-instruction emulator ceiling
detects an unexpectedly nonterminating execution; it is not a physical timeout.

Execution continues through the actual `st_fail` interrupt mask and emergency
GPIO stores. Before entering `st_note`, all four motor PMUXEN bits are clear,
DIRCLR receives `0x000c0300`, OUTSET receives `0x00080000`, PRIMASK is one, and
the diagnostic fault note has the original reason. The runner stops there,
before RAM logging or flash flushing. This proves the compiled ordering before
the logging boundary under the stated model, without relying on a responsive
TCC synchronization register to release GPIO.

Three supplied-ready cases return normally: encoder SPI, clock initialization
and one-byte UART transmit. UART and ADC readiness changes explicitly model
selected status behavior; ordinary memory is not assumed to implement all
write-one-to-clear registers. Void-function return-register contents are not
treated as API results. The UART positive returns one.

The failing control replaces only the first SPI DRE budget decrement with a
Thumb NOP in emulator memory. Under the same stuck status, it exhausts the
instruction ceiling without reaching `st_fail` or a return. The public image and
source files remain untouched. This demonstrates that the fixture distinguishes
the actual countdown guard from an unbounded spin.

## Reproduce

First materialize the [pinned 3.5 build](../../firmware/upstream-hardening/next35/README.md),
then use a fresh private output file:

```sh
tools/rea-analysis/venv/bin/python firmware/upstream-hardening/followup/27-peripheral-bounds/run.py --build artifacts/private/absolute35a --output artifacts/private/peripheral-35-recheck.json
```

All eleven positive executions and the one guard-removed control pass their
stated expectations. This suite is specific to the pinned 3.5 layout; a changed
compiled candidate needs separately reviewed addresses and evidence.

## Limits

Memory-backed MMIO supplies readiness and is not the SAM D21 peripheral state
machine. No asynchronous interrupt delivery, voltage, clock calibration, bridge
electrical behavior or physical motor/coast timing is modeled. The iteration
budget is finite work, not a measured response deadline. GPIO register writes do
not prove electrical release. The suite does not execute the NVM flush or WFI;
the separate compiled writer/storage tests retain those narrower contracts.
Unicorn execution also does not by itself prove ARMv6-M instruction legality.

No new production defect or firmware change is inferred. Actual capture,
exposure, shutdown and AF-S qualification still require owner-coordinated camera
evidence after resolving the pending 3.2 reconnect/strict-verification gate.
