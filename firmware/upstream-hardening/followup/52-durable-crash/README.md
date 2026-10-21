# Durable crash diagnostics

Source-pinned overlay for a private AF 4.0 source copy. Run `apply.py COPY/src`.
The root build owns the AF 4.1 version change, compilation and release manifest.
Published 4.0 artifacts are immutable.

`retained.inc` adds one 56-byte retained checkpoint at fixed SRAM `0x20003fc0`,
outside application BSS/stack and the modeled original bootloader footprint.
Its summary is the last completed foreground checkpoint, not the final fault
state. Magic/schema and CRC guard recovery; exact WDT or system reset causes
alone permit interpreting retained bytes. Power removal may destroy them.

`watchdog.inc` configures a separate OSCULP32K clock, divide 32, 4096-cycle WDT.
The nominal period is four seconds, not a measured deadline. Preparation is
before protocol activation; asynchronous arming is after initialization and
reference reads. Health service occurs only in the foreground main loop and
after completed servo sensor/control/protocol iterations, at most once per
250 ms of advancing SysTick time. It never writes flash. CRC runs with IRQs
restored; only the 48-byte summary copy and publication invalidation are masked.

At boot the GPIO-only emergency motor release precedes all scanning/writing.
One CRC-protected type-5 page records reset cause and optional recovered summary.
Any current WDT/system cause, previous valid type-5 crash record, or inability to
append the normal baseline halts before normal board/motor/protocol setup.
A nonerased page with invalid CRC also halts as a storage-integrity failure.
A prior crash latch persists across battery removal until the tail is erased
through the separately authorized installation/recovery workflow. No erase is
implemented here. The baseline is startup evidence only. The standalone boot
page and subsequent ordinary trace have separate append cohorts.

HardFault requests a system reset with a naked assembly handler. It never reads
the exception frame or attempts flash programming. Its record therefore means
system reset, not proven HardFault and not a captured fault PC.

Offline target-C/register-stub tests:

```sh
python3 firmware/upstream-hardening/followup/52-durable-crash/test_watchdog.py \
  --output artifacts/private/astra52-watchdog-new
```

Lane 54 independently exercises the actual retained/append C with corruption,
torn writes and mutation controls. These tests do not emulate WDT silicon,
camera timing, flash power-fail behavior or electrical motor release.

See [audit](../../../../docs/audits/astra-52-durable-crash-2026-10-21.md).
