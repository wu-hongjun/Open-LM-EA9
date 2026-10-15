# AF 2.9: camera communication through motion faults

October 12, 2026, America/New_York. **AF 2.9 for Contax Zeiss 50mm f/1.4 is
prepared and tested offline in this implementation pass.** App 0.12.0/build
15 and the signed CLI prepare/install this separate variant. During that offline
pass the adapter was on the [strictly verified stock 1.8 restoration](stock-18-af28-recovery-2026-10-12.md);
the implementation work sent no hardware reports and changed no owner application state.
AF 2.8 remains frozen and held after its reported camera failures.
Subsequently, the separately authorized [AF 2.9 upload](af-29-upload-2026-10-12.md)
succeeded and passed strict two-pass reconnect verification plus a separate
offline audit. Subsequent **camera acceptance failed**: the owner reports focus
achievement followed by capture-time freeze requiring battery removal. Further
2.9 trials are held; see [the failure and finite protocol investigation](af-29-camera-failure-2026-10-12.md).
The owner subsequently reports startup/reset movement but no later focus
movement. Two additional composed admission fixtures cover homing interrupted
after movement by Stop or ADC fault, parsed subsequent Moves and shutdown.
[The follow-up suite](af-29-reboot-admission-2026-10-12.json) passes 40 current
cases with the same 15 frozen controls; production firmware is unchanged and
the physical cause remains unproven. The implementation evidence below retains
its original 38-case scope.

## Demonstrated defects and changes

The [owner's AF 2.8 reports](af-28-camera-failure-2026-10-12.md) include preview
freeze, poor focus response, darker exposure and a shutdown hang requiring
battery removal. No live fault/traffic trace survived. The following defects are
reproduced software failures, not a proven diagnosis of which one occurred there.

| Frozen 2.8 behavior | AF 2.9 behavior |
| --- | --- |
| Any encoder/ADC/PWM fault blocks even a ready UART transmitter and UART/EIC initialization | Dependency masks let a healthy link initialize/transmit while every motor fault remains latched and drive remains inhibited |
| Motion faults immediately skip micro/millisecond protocol delays and the shutdown VD-low wait | Healthy timing continues through motion faults; clock/timebase/link failures retain bounded exits and the existing 500 ms VD-wait ceiling |
| A failed send is counted as transmitted; final init can arm status, shutdown can be marked acknowledged and event/query tails can be consumed | UART returns success only at TXC; framing, handshake, shutdown and tail consumption advance only after successful transmission |
| A new initialization request retains the previous status-handshake flag | A session opener clears handshake/status-due state; status waits for a successful final 0x0a reply |

`io_guard` now separates all-fault motor guards, timing dependencies
(clock/timebase), and link dependencies (clock/timebase/UART/EIC). Encoder,
ADC and PWM faults remain sticky. There is no fault clearing, automatic motor
retry or rearming. A genuine UART/timing/EIC failure still blocks communication;
this is not a promise to transmit through broken hardware.

`em_uart` owns complete-transmission success. `emount` owns protocol publication:
it releases chip select on every attempted send, but only records completed
frames and consumes transmitted tails. `main` retains its shutdown owner;
motion faults no longer skip its healthy VD/timing sequence. Motor-controller,
reference, observer, aperture, optical-table and completion policies are
unchanged from 2.8. No gain, duty, iris/EV correction or sensor reference is guessed.

The simplified responder still does not reproduce the full factory fourteen-
state scheduler. The new initializer reset is a candidate admission policy;
it is not a claim that stock uses our handshake boolean or that a disabled bus
and inhibited motor can resume without a physical power cycle.

## Original factory evidence

The retained REA model separates initialization/status phases and recovers
shutdown's echo, 50 ms delay, UART disable, VD-low checks, PA23 signal and
100 ms delay. A new [original-instruction replay](../../scripts/test-stock-shutdown-order.py)
executes entry `0x5e00` with explicitly seeded shutdown phase 2 and PA3 low.
[Its retained evidence](af-29-stock-shutdown-oracle-2026-10-12.json) contains:

- 24 valid generated request/sample/sequence cases with the expected raw echo
  and ordered shutdown actions.
- One direct-state bad-checksum observation at the pre-format buffer boundary.
  It bypasses receive validation and is not a legal camera request. The original
  record's interpretation of this boundary is corrected below.

**October 15 correction:** `0x51c8` is the GPIO handoff before formatting,
not the final UART sender. The [terminal-tail audit](../audits/astra-31-factory-shutdown-tail-2026-10-15.md)
executes the original formatter and observes its pointer/count buffer at UART
boundary `0x9180`: length, checksum and terminator are normalized there.
The live replay now distinguishes both observations and rejects equating the
malformed pre-format buffer with UART bytes. All 25 corrected replay cases pass.
The old JSON and validation pins remain unchanged as historical evidence; its
`checksumFinding` and `transmitCut` wording do not describe final UART bytes.
This correction establishes no malformed receiver admission or physical delivery.

In the historical replay, the pre-format GPIO helper, timing/UART services and sleep were explicit cuts;
registers are dummy memory and wake is supplied. This establishes action order
under the seeded phase, not ordinary reachability, physical elapsed time or
the whole camera conversation. It adds fixtures for an already reconstructed
routine; it does not increase the 41-entry semantic-model union or establish
full factory reconstruction. In the custom shutdown path, receive validation
precedes checksum recomputation, so legal shutdown echoes remain exact.

The pure controller still passes 7,323 original-instruction comparisons and its
integral-gain negative control. The original frame-sync/completion replay still
passes 12/18 cases. These retain the PID and measured-position baseline while
communication policy changes independently.

## Validation and prepared products

[The reproducible link runner](../../scripts/test-camera-link.py) passes **38
sanitized current cases** and detects **15 intended failures in exact frozen
2.8 production sources**. It tests actual UART, GPIO release, clock routing,
EIC and delay implementations against DFP-shaped register memory, plus composed
production handshake/reference/shutdown routines with parsed frames. The latter
start unhandshaken/unhomed, load the actual 50mm profile, complete initialization
and exercise healthy, pre-home fault, idle fault, failed init/status/shutdown and
reinitialization scenarios. Frozen host-boundary instrumentation only discards
a selected transmit and counts VD reads; production source/headers stay exact.

The simulator/register transitions do not represent complete reset entry,
concurrent physical IRQ timing, actual sensor readiness, camera preview or optics.
The guarded no-body startup wait and full factory scheduler remain separate
boundaries. A test pass does not reproduce or resolve the owner's hardware hang.

Additional checks passed: 51 Swift tests; the full firmware/profile/driver suite,
including eight requested lens profiles; retained queue/retarget, observer,
controller/mechanical and 32 original opaque `0x34` reply regressions; signed
app/CLI packaging; exact native/Python prepared-image equality. All prior
release binaries and recovery data remain byte-identical. See
[validation](af-29-validation-2026-10-12.json),
[link controls](af-29-link-regressions-2026-10-12.json),
[retained regressions](af-29-retained-regressions-2026-10-12.json),
[build/layout](af-serviced-build-manifest-2026-10-12.json), and
[preserved releases](af-29-preserved-releases-2026-10-12.json).

The [50mm candidate](../../firmware/candidates/2.9.0/README.md) is 20,480 bytes,
loader 2.9.0/camera BCD 0x29, profile at `0x9f00`, ending at `0xa000`. Release
margin is 276 bytes; static RAM is 2,200 bytes with 8,192 reserved stack bytes.
Stack high-water and physical timing are unmeasured. The known fixed f/1.4
declaration and opaque stock `0x34` echo remain; actual iris is Unknown.

## Next qualification gate

Hardware upload is a separate requested step with the normal same-unit backup,
durable journal, physical reconnect and strict verification. Then require one
controlled loaded-lens display/exposure/idle/shutdown check before bounded AF-S.
Stop immediately for frozen preview, shutdown nonresponse or abnormal motion.
The [camera runbook](../af-s-test.md) records actual settings and preserves failures.

Factory parity remains the goal. It needs stable startup/preview/shutdown,
correct saved exposure with manual iris changes, and matched stock/custom AF
lock, acquisition-time, hunting and sharpness comparisons. Real bus/sensor
latency, frame scheduling, ordinary factory homing/persistence, fault telemetry
and the optical declarations remain open. No physical improvement, complete
reverse engineering or factory-equivalent performance is claimed here.
