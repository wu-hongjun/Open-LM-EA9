# AF 2.5 candidate: aperture consistency and bounded completion

## Independent aperture audit amendment

**Hardware installation is on hold for this frozen candidate.** The
[independent design audit](../audits/aperture-protocol-design-2026-10-11.md)
found that pinned `msg_0x34.md` labels its semantics UNKNOWN. REA proves the
request-word copy at reply offset 7; it does not establish an aperture meaning.
The separately documented duplicated value 850 is at other offsets. The earlier
claim that a conflicting aperture request in `0x34` proved inconsistent
aperture reporting was too strong: our synthetic operand was interpreted as
aperture without protocol evidence. Test output labels such as `AV` reflect
that hypothesis and do not prove it. These offline test results and binaries
remain preserved; the hardware recommendation and semantic interpretation are
superseded by this amendment.

Known aperture fields (`0x05`, `0x1b`, negotiated `0x28`) must be handled
separately from unknown fields. A later candidate should preserve the bounded
stock `0x34` echo baseline unless a specific experiment is supported by evidence.
The AF completion regressions remain valid offline controller evidence.

October 11, 2026, America/New_York. Delivered a separately versioned 50mm f/1.4
candidate and app 0.8.0/build 11. **Offline validation passed; no adapter upload
or camera qualification occurred.** The owner's failed 2.4 AF attempt and stock
exposure reports remain accepted evidence. No photograph was required to
continue, and no automatic one-stop exposure correction was introduced.

## Aperture and exposure path, with corrected interpretation

The receive layout and independent factory instruction/model comparison show
that dispatcher `0x58a4` copies a parsed request word at SRAM `0x69a` (request
snapshot `0x694` plus six header bytes) into the `0x34` reply at offset 7.
Factory `0x1b` also echoes that word. Upstream RX fixups follow this behavior.
This establishes data dependency, not persistent sensed state and not a shared
meaning for these two message IDs. The pinned documentation establishes aperture
for `0x1b`, but labels the purpose of `0x34` UNKNOWN.

The 2.5 `lens_aperture.[ch]` module owns a declared value and publishes the known
current fields in `0x05`, both `0x1b` copies and negotiated `0x28`. The known iris
countdown is zero and the iris-rest bit is set without clearing other status
bits. The profile sets equal declared range endpoints. Lens specification and
unknown physical iris remain distinct from declared camera metadata; retained
stock optical rows are not calibrated for this lens. Production `em_init()`
does not install the SEL5518Z row constants still present in the header.

The module **also overwrites `0x34` based on an unproven aperture hypothesis**.
A synthetic pair of requests with operand `0x1600` makes frozen 2.4 return
`0x1100` in `0x1b` and echo `0x1600` in `0x34`; 2.5 returns `0x1100` in both.
Only the first message's operand has established f/8 semantics. These test
results demonstrate implementation behavior, not an aperture contradiction or
an exposure repair. A synthetic payload-free query is also exercised; it is
not proof of a real camera request's grammar. Three original-instruction cases
confirm only the `0x34` echo dependency for the chosen words `0x1100`, `0x1200`
and `0x1600`. The meaning of the separate duplicated 850 field is unresolved.
The audit therefore recommends preserving bounded opaque stock behavior in a
successor candidate, or isolating a separately justified experiment.

`0x08` negotiation is applied from the consumed request snapshot rather than
publishing the receive ISR's latest capability to an older pending reply.
The optional EXIF aperture is omitted after a session opener until negotiated
again. No unknown wire sentinel, invented capability bits or blanket exposure
bias is used. The app labels actual physical aperture Unknown. Profile tests
exercise framing/checksums, known aperture fields, optional-copy negotiation
and session reset across seven prime/macro profiles. **None proves correct
metering, aperture display, or focus on the A7C II.**

## AF result and completion policy

The pure factory speed/PID/timer law is unchanged and still matches 7,323
original-instruction comparisons. Changes are in the hardware wrapper, session
fault policy and event eligibility:

| Termination | Behavior |
| --- | --- |
| Target crossing | Brake; preserve actual measured position; eligible termination event |
| Whole correction within one four-count protocol unit | No drive pulse; terminate at existing resolution; final feedback must still be within that unit |
| Factory-sized deadline with direction-consistent progress | Brake; report partial actual position; allow a later command and emit actuator termination |
| Stall/no progress, unsafe timeout, runaway/wrong-way, sensor/PWM/timebase fault | Release; latch the fault; subsequent driving remains inhibited |
| Camera Stop | Cancel completion and acknowledge Stop; retain any observed hard fault |

The resolution policy applies to the whole tiny leg, not a widened arrival
band for ordinary moves. It is an explicit bounded-wrapper deviation from the
factory crossing law. It avoids raising gains/duty to break simulated stiction.
Healthy deadline completion does not claim exact arrival or optical focus lock.
Scan run-up termination does not start a sweep from an unreached start point.

Stop is still polled after the retarget budget is exhausted. A new additional
target exhausts the hard budget, but Stop cannot be stranded by an unpolled
receiver. Final feedback/fault checks remain authoritative; Stop acknowledgement
cannot erase an observed runaway or wrong-direction fault. Invalid feedback is rejected before target arithmetic, prediction and telemetry.
The existing I/O guard already released motion ownership; the additional
regression confirms that a later Stop remains acknowledged with that fault latched.

The inherited mechanical simulation reproduces both 2.4 counterexamples, then
checks the new policy and an actual following motion:

| Request | 2.5 first termination | Following motion |
| --- | --- | --- |
| Four counts from zero | Resolution termination at zero; peak drive zero; no session fault | 40-count target crosses, ending at 42 |
| 5,952 counts from zero | Healthy deadline at 5,762; no session fault | Reversal toward 4,000 crosses, ending at 3,997 |

Neither sequence contacts a simulated stop. Mechanical coefficients and elapsed
simulation times come from upstream's unit, not this owner's hardware. Camera
optics/metering are not modeled. Physical timing, homing/origin, loaded braking,
AF-S accuracy, hunting, AF-C/video and factory parity remain unqualified.

## Validation and preservation

- Cross-build: 20,480 bytes, profile at `0x9f00`, write end `0xa000`; no diagnostic
  flash writers or legacy servo linked. No expansion into retained upper flash.
  Initialized code/data ends at `0x9edc`, leaving only 36 bytes before the fixed
  profile row. Further features need size reduction within this boundary.
  Static RAM ends at `0x20000afc`, with a reserved 8 KiB stack ending at
  `0x20002b00` inside 16 KiB SRAM; actual stack high-water is unmeasured.
- Swift: 50 tests across lens, DeviceKit and app-workflow suites. 2.5 admission,
  wrong-image rejection, firmware-preserving profile changes and recovery rules
  pass; a future 2.6 version remains rejected.
- Host suite: packet/init/profile checks, 27 scripted factory-wrapper scenarios,
  both motion backends' lifecycle/hardening checks, Stop/fault and MMIO wait/
  startup checks. Includes 21 hardening scenarios per backend.
- Factory oracle: 7,323 comparisons, with the altered-gain negative control
  detected. Original final drivers/transmitter are stubbed; emulator behavior
  does not prove physical timing or architecture legality.
- New regression: eight mechanical targets, following moves for both former
  failures, original query instructions and a frozen 2.4 negative control.
- Mac bundle: app/CLI built and locally signed. Native/Python prepared bytes
  match exactly; all frozen templates and stock recovery remain unchanged.

Evidence: [build inputs](af-refined-build-manifest-2026-10-11.json),
[motion/query regressions](af-25-regressions-2026-10-11.json),
[factory oracle](af-25-factory-oracle-2026-10-11.json),
[release validation](af-25-validation-2026-10-11.json), and
[candidate manifest](../../firmware/candidates/2.5.0/contax-zeiss-50-f1-4.manifest.json).
The frozen 2.4 test inputs and checksummed manifest are retained under
`firmware/candidates/2.4.0/counterexample-src`. The historical reproducer now
uses those inputs; it does not silently run the repaired controller as 2.4.
That byte-exact snapshot preserves inherited trailing whitespace in the packet
table. The whitespace check passes for the new implementation/documentation
when the frozen snapshot is excluded; its exact bytes are checked separately.
Raw unit backups, serials, calibration and recovery keys remain private.

The original planned hardware step was separately coordinated USB-cap upload and strict
reconnect readback, followed by aperture/display/exposure and lifecycle checks,
then one AF-S comparison. The audit amendment above now holds that step for 2.5.
The existing photograph is unavailable and is not a
gate. Recovered protocol/model evidence remains a starting point, not a claim
that this complete firmware equals stock.
