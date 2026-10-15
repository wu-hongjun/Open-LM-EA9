# Astra lane 05 — UART/EIC ownership and transmit admission

Offline audit against frozen upstream C 3.2, image SHA-256
`e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
The overlay applies after root frame admission and explicit UART completion,
then lanes 02, 01 and 03. Root owns integration and release decisions.

## Accepted fixes

1. **Atomic software transmit admission.** The former check-to-CS gap allowed
   receive/control ownership to change before lens CS assertion. `em_transmit`
   now validates length before reading, takes a coherent private snapshot, then
   briefly masks interrupts while checking CS generation, actual body CS,
   actual CS EXTINT pending flag, active status validity, and the sticky shutdown
   latch. The dedicated shutdown snapshot is the only shutdown exception.
   Admission and lens CS assertion share the critical section. UART and checksum
   work execute with the caller's normal interrupt state restored.
2. **Immutable bytes on the wire.** EIC dispatch of incoming aperture metadata
   can edit shared `ea9_data` while foreground is transmitting it. The snapshot
   is copied with interrupts enabled, bracketed by `em_cs_edges` reads and
   compiler memory barriers. A changed generation returns failure immediately;
   a second generation check occurs at final admission. No retry loop is added.
   An admitted local packet stays immutable through UART completion. Length's
   high byte is explicitly stamped, including supported 256-byte raw echoes.
3. **Serialized receive reset.** SERCOM priority zero could append halfway
   through the lower-priority EIC's poison/reset loop, then have its new length
   overwritten with zero. `em_uart_rx_reset` now preserves/restores PRIMASK
   around its bounded 64-byte reset. A pending UART interrupt runs afterwards.
4. **Bounded receive error path.** At most four DATA reads occur per UART ISR
   entry. If RXC remains asserted, the window becomes invalid and RXC interrupts
   are disabled until physical reset. This prevents an infinite drain loop and
   immediate priority-zero tail chaining of the same stuck source. Software
   buffer overflow and UART ERROR also invalidate the complete window; an
   ordinary new window clears those nonfatal conditions. A drain fault remains
   sticky. Invalid windows report length zero and cannot enter frame admission.
5. **Explicit completion retained.** Root's `em_uart_send` result remains the
   authority for transmit counters and publications: disabled returns zero;
   successful completion is after TXC. Lane 05 releases CS and returns failure
   without publishing a successful transmission when that result is zero.

`em_eic_receive_pending()` is the only new hardware API. It reads the actual
CS EXTINT bit, independently of the VD flag and NVIC delivery. The legacy staged
host shim defaults that predicate to zero. Targeted tests inject its states.

## Verification

Reproduce without device access:

```sh
python3 firmware/upstream-hardening/lanes/05-transport/run.py \
  --output artifacts/private/astra-05-transport-review
```

Recorded run: `artifacts/private/astra-05-transport-v3/result.json`.
It verifies frozen source hashes, composes the staging tree, extracts the exact
production function bodies, and compiles native probes with ASan/UBSan for TX
and receive paths. A register model replaces DATA reads and injects a UART
interrupt halfway through reset; no driver algorithm is reimplemented.

- **17 frozen failing controls**, including TX during high body CS, pending
  CS edge, invalid status, shutdown, failure publication, interrupt-cut admission,
  template mutation during send, 256-byte high-length encoding, reset interleave,
  stuck RXC timeout, UART ERROR, and receive-buffer overflow. The dedicated
  shutdown acknowledgement is a passing frozen control.
- **22 hardened passing cases:** 14 TX/admission/snapshot cases, four actual RX
  driver cases, and four actual UART send cases (disabled, complete, DRE timeout,
  TXC timeout). The timeout probe substitutes an eight-iteration wait budget and
  a test fault trap; production retains its existing fail-stop wait mechanism.
- **65,536 EIC flag combinations** verify the actual predicate ignores unrelated
  flags and recognizes CS pending.
- Whole `emount.c`, `em_uart.c` and `em_eic.c` compile for Cortex-M0+ against the
  actual SAMD21/CMSIS headers with `-O2 -Wall -Wextra -Werror`. Disassembly and
  GCC stack-usage files are retained with the private run.

Native probes are exact-function tests, not full MCU emulation: W1C flag
clearing and NVIC delivery are represented by explicit model state. Whole-unit
ARM compilation checks the real register/API spelling. Root's composed host
regression suite and full image/stack gates remain required.

## Timing and memory findings

The first candidate used `memcpy` under a global mask. Inspection of the bundled
`libc_nano.a` showed a six-instruction byte loop; 256 bytes would take roughly
2,500–3,000 core cycles before stalls, around 50–60 microseconds at 48 MHz. That
exceeds the 13.3-microsecond wire-byte interval and was **rejected before final
integration**. The accepted copy and checksum are interruptible. The final TX
mask has no loop: it performs bounded generation/ownership tests, two MMIO
observations and one CS write. There is no PRIMASK interval spanning UART waits.

The receive-reset mask contains exactly 64 poison stores in a four-instruction
loop, then the length/fault updates. Disassembly supports a nominal roughly
450-cycle estimate (about 9.4 microseconds before memory/bus stalls), not a
measured worst-case timing guarantee. This replaces an already-existing poison
loop; its newly masked duration needs hardware timing validation.

GCC reports a **296-byte `em_transmit` stack frame**, including the 256-byte
snapshot. This is an individual frame measurement; nested foreground, interrupt,
exception-stack and library frames must be included in root's stack budget.

## Explicit limitations and deferred findings

- Masking CPU interrupts cannot atomically freeze an external pin. A physical
  edge arriving after the last hardware observation and before CS assertion,
  or a pulse not yet visible through the input/filter, remains possible. A new
  edge after an admitted transmission begins cannot retract already-shifted
  bytes. This is software admission serialization, not an electrical bus lock.
- The coherent-copy proof relies on the audited writer set: packet setters run
  in foreground, except incoming aperture handling in the CS EIC callback;
  that callback increments `em_cs_edges` before mutation. VD changes timing and
  owner state but not packet bytes. SERCOM and servo/tick interrupts do not write
  these templates. Future interrupt writers must join the generation protocol.
  The comparison assumes fewer than 2^32 CS dispatches during a bounded copy;
  prolonged interrupt starvation can prevent foreground progress generally.
- A byte already serviced before the rising-edge reset starts may still be
  discarded by that reset. The fix proves append/reset serialization, not
  reconstruction of edges and UART data that arrive in an ambiguous order.
  Likewise, multiple edges merged into the single hardware EIC latch cannot be
  reconstructed offline. Priorities are unchanged.
- A continuously asserted RXC is treated as a fatal receive fault after four
  reads. This sacrifices automatic recovery until reset. The policy prevents
  an unbounded ISR and stale-frame acceptance; it does not independently invoke
  the motor inhibit or a physical power-cycle. Normal UART ERROR/overflow rejects
  one window and may recover at the next rising edge.
- Error-invalid windows expose length zero; the existing raw UART error/status
  telemetry remains, but this lane does not add a new host diagnostic schema.
- No factory parity, physical camera stability, calibrated timing, or safe
  mechanical behavior is established by these tests. No adapter enumeration,
  opening, HID report, flash, updater, motor action, Application Support write,
  or released-firmware mutation occurred.
