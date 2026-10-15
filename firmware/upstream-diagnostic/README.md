# Upstream C startup diagnostic 3.2

**Prepared offline for Contax Zeiss 50mm f/1.4; not uploaded or camera-qualified.**
This lane starts from pinned upstream `d52ed06cc449918f938e0695fbf29a0c4141f2b2`.
It keeps the upstream servo, focus mapping, prediction, homing and parking
algorithms. The [reviewable patch](upstream-changes.patch) contains every change
to the archived upstream source; the new diagnostic module lives in `src/`.
The original reference snapshot and older firmware remain untouched.

The [3.2 candidate](../candidates/3.2.0/README.md) addresses a reproduced first-
window receive loss. It also restores stock packet-table lens ID 234 as a
compatibility control, replacing upstream's experimental 50496. That identity
choice is not a proven explanation for the A7C II failure. The fixed nominal
f/1.4 aperture and upstream's capability-controlled optional `0x28` field stay
consistent with 3.1; actual physical aperture remains unknown.

## Receive-window repair

Upstream enables UART before polling the first body chip-select pulse, then
clears the receive buffer after it notices the rising level. RX interrupts can
already have delivered the opener at that point. The new helper preserves a
plausible init-frame prefix, checks checksum/terminator when the whole frame is
available, and still discards unrelated idle noise. The prefix decision/reset
runs in a short IRQ critical section so another byte cannot be appended during
the buffer clear. Partial prefixes still need the ordinary parser at window
close; this does not claim a new complete frame validator.

An authored host shim supplies 0–11 bytes before the observed rise and the rest
at close. The candidate answers all 12 openers. Checksum-pinned frozen 3.1
loses all 11 early-prefix cases and passes the no-early-bytes/noise control.
These are synthetic interleavings, not recovered A7C II traffic.

## Diagnostic boundary

`startup_trace.c` owns a bounded 48-event RAM recorder and explicit little-endian
page encoding. `startup_trace_flash.c` supplies the SAMD21 storage/IRQ boundary.
The decoder is a separate host script with no USB API. Stages cover entry to
main, clocks, tick, encoder, ADC, motor, UART, first CS waits, EIC, bus readiness
and initial reference. RX/TX records retain ID, class, sequence, window length,
first two request bytes and firmware tick. Summary counters continue after the
event buffer fills, with an explicit dropped-event count.

No diagnostic flash programming runs during healthy early startup or an active
connected session. RAM breadcrumbs are persisted only:

- after two seconds with no frame-sync edge while waiting for the first CS;
- once an incomplete handshake is at least two seconds old and has gone quiet
  for 100 ms, with body CS low;
- after the upstream shutdown path disables UART;
- at a guarded terminal peripheral/tick/CS-wait fault, after detaching the motor.

A terminal fault is allowed to persist while the bus is otherwise unusable.
The normal logger does not run in RX/EIC interrupts. Flash writes stall the
device and mask IRQs, so their real latency and any effects on later power-down
are unmeasured. Early power loss, a CPU exception outside the guarded paths or
an electrically wedged bus can leave no diagnostic record. A blank log does not
prove that main never ran. Tick timestamps are not wire timing; pre-tick stages
use zero and masked flash intervals can lose SysTick increments.

## Storage and waits

The linker caps executable/initialized ROM at `0x9c00`. The entire 20 KiB upload
ends at `0xa000`; its reserved `[0x9c00,0xa000)` tail starts FF. The logger can
program at most **sixteen distinct 64-byte pages per installed image**. Each has
version, type, boot discriminator, physical slot and CRC32. It never issues an
erase, retries a failed program within the same boot, overwrites a nonblank/torn
page or wraps storage. After power loss a still-FF page is indistinguishable
from an unused page and can be selected on a later boot; sixteen slots is a
storage bound, not a proof of sixteen lifetime program attempts under power cuts.
All addresses are checked again by the hardware backend. Boot code, loader
metadata, the protected gap, upper retained flash and factory auxiliary rows
are outside its write range. Reflashing is separately coordinated and backs up
the existing logs first; there is no log-clear command.

Empty clock, SPI, ADC, PWM, UART and EIC polling loops have finite iteration
budgets. Millisecond/microsecond delays also have fallback budgets. The two
initial CS waits use an eight-second firmware-tick limit plus an iteration
fallback. A guard failure detaches motor mux pins without waiting on the
potentially stuck PWM peripheral, attempts one bounded log flush and stops.
These are software bounds, not measured wall-clock guarantees during a wedged
AHB/NVM transaction. A valid slow-body host case remains covered.

Nine tests execute the **compiled candidate NVM writer** in Unicorn. They check
first/last page, address/alignment fences, occupied pages and controller-error
rejection. The supplied peripheral model is not an electrical NVM simulation;
voltage, cache coherence, endurance and actual programming latency remain
hardware qualification work. [Primary sources and retrieval limits](../../references/analysis/startup-diagnostic-primary-sources-2026-10-15.json)
record the Microchip guidance and pinned DFP register definitions.

## Reproduce offline

```sh
python3 scripts/build-upstream-diagnostic.py
python3 scripts/test-upstream-diagnostic.py --output /new/host-results
python3 firmware/upstream-diagnostic/tests/test_decoder.py /new/host-results/trace-fixture.bin
tools/rea-analysis/venv/bin/python scripts/test-startup-flash-arm.py --output /new/arm-results.json
scripts/swift-local.sh test
scripts/build-macos-app.sh
```

The reference collection, pinned ARM/DFP/CMSIS dependencies and Unicorn analysis
environment must already be materialized. A rebuild that differs from the
published 3.2 image stops rather than replacing it. The native image is fixed;
edited/other lens profiles are rejected before USB. See the [later installation
and log-retrieval procedure](../../docs/upstream-startup-diagnostic-test.md).

Retain upstream [MIT](../upstream-baseline/LICENSE) and Microchip/CMSIS
[Apache-2.0](../upstream-baseline/Apache-2.0.txt) notices. These notices are already
packaged with the application's firmware resources. No original factory
algorithm completeness or camera compatibility is inferred from these checks.
