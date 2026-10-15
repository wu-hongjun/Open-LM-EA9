# Astra 28 — independent startup handoff review

**Disposition:** accept the scoped EIC setup/start proposal for root's exact
compiled and release checks. Reject the earlier whole-PRIMASK proposal. A
single permitted rising EIC interrupt corrupts the frozen startup snapshot;
the scoped proposal removes that producer overlap while retaining UART service.
No hardware timing, camera acceptance, complete startup reliability or release
footprint conclusion follows from this lane.

The input is frozen C 3.5, image SHA-256
`04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632`, manifest SHA-256
`a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de`.
Every manifest source hash was checked before and after execution. The lane
read the authorized-window ledger and campaign and made only offline fixtures,
synthetic evidence and this report. Published candidates, pins, canonical state,
production source and build scripts were not edited by this lane.

## Reproduction and independent controls

Frozen `em_init` enables EIC delivery and then calls `on_cs_edge(0)` directly
from foreground to rescue the first receive window. This direct call is not
an EIC exception. A normal EIC exception may therefore preempt it. The real
rising-edge callback calls `em_uart_rx_reset`, whose production implementation
poisons 64 receive bytes before zeroing its length. If that single callback
runs after four bytes of `em_owner_offer` have been copied, the remaining
snapshot bytes become poison. The resulting eleven-byte request is invalid.
No second frame, same-priority EIC recursion or assumed long interrupt duration
is required for this counterexample.

Root's earlier whole-frame injection was sufficient to illustrate producer
overlap but did not model the peripheral consequences of delaying an entire
wire transaction. The independent fixture replaces that with one pending EIC
bit and one rising callback. It also executes actual source bodies for
`em_eic_init`, `em_eic_start` when present, `EIC_Handler`, `SERCOM1_Handler`,
UART reset/accessors, and the full `em_init`, frame validation and owner path.
MMIO setup, DATA reads, write-one-to-clear flags, pin reads and NVIC effects
are explicit host models. Successful synchronization is modeled as already
ready; it is not measured or cycle-emulated. Interrupt delivery never recursively
enters EIC. Priority-zero UART is serviced before pending priority-one EIC.

[Runner](../../firmware/upstream-hardening/followup/28-startup-handoff-review/run.py),
[fixture](../../firmware/upstream-hardening/followup/28-startup-handoff-review/test.c)
and [synthetic result summary](../../firmware/upstream-hardening/followup/28-startup-handoff-review/result.json)
record **246 executions: 41 cases for each of six source variants**. Every
matrix row has an asserted expected snapshot, UART error count, callback count
and returned PRIMASK state. Builds use Clang ASan/UBSan with immediate failure
on sanitizer errors. Expected defects in negative controls are asserted results,
not passing product behavior.

| Source variant | Single rise during owner copy | Late final UART byte during EIC setup |
| --- | --- | --- |
| Frozen 3.5 | Invalid eleven-byte snapshot | Complete first request admitted |
| Whole-PRIMASK proposal | First request preserved | First request missed |
| Unlock-before-rescue control | Invalid snapshot | Complete request admitted |
| Scoped EIC setup/start | First request preserved | Complete request admitted |
| Start-EIC-before-rescue control | Invalid snapshot | Complete request admitted |
| Omit initial EIC-disable control | Invalid snapshot with inherited EIC enabled | Complete request admitted |

The matrix includes valid, empty, noise and truncated first windows; interrupts
at setup completion, post-validation and mid-copy; pending high/low CS, VD and
combined flags; coalesced CS transitions; one and two delayed UART bytes; a
synthetic three-byte FIFO overflow; and prior PRIMASK equal to one. The prior-mask
case sets the mask after the first bytes have been received, checks that startup
leaves it set, and verifies pending delivery only after the test restores it.

The full private result is `artifacts/private/astra-28-startup-verified/result.json`,
SHA-256 `59ae46059ec256df7e717b4ffd1d70fb3bf11bdab6b86181b622f8e6020a0ae8`.
The public summary retains source, fixture and applied helper hashes and selected
synthetic rows. The tested scoped transformation is root's actual `scoped(work)`
from lane 26, not a separately implemented equivalent.

## Why the global mask was rejected

With ten of eleven valid bytes in software, a final UART completion at the
setup cut is serviced before rescue in frozen source. Under the proposed
PRIMASK lock it waits while rescue rejects the truncated frame. Unlock then
appends the final byte, but no remaining EIC edge reparses the completed buffer.
This is a permitted late-completion model and a source-level behavioral
regression. It is not evidence that the physical camera generates this exact
relationship between CS, RXC and interrupt acceptance.

The global mask also accumulates three synthetic byte arrivals in the modeled
two-byte FIFO, producing an error that the unmasked path avoids. That test
illustrates dependence on a masked-duration bound; it does not establish that
the real successful setup exceeds the FIFO service budget. The actual EIC setup
contains three `ST_WAIT_WHILE` synchronization loops, each with a 4,194,304
iteration fail-stop budget. This is finite software work before failure, not a
calibrated microsecond bound. A failed wait enters a nonreturning fail-stop path.
Masking these waits would suppress UART and SysTick along with EIC. Preserving
the previous PRIMASK correctly does not resolve these receive-service effects.

## Scoped proposal assessment and limits

The accepted transformation disables only NVIC EIC before publishing callbacks,
performs the existing peripheral setup and flag initialization, and defers NVIC
EIC enable to `em_eic_start` after the synthetic rescue/reset branch. The start
function does not clear pending flags. UART and SysTick remain eligible throughout
setup/rescue, apart from the short existing saved-PRIMASK sections. Local CMSIS
implements EIC disable with the ICER write followed by DSB/ISB. The proposal
does not change inherited PRIMASK or enable any other interrupt.

A pending rising callback after rescue resets the live receive buffer without
changing the owned snapshot. Pending falling and combined CS/VD callbacks are
delivered after rescue. Empty/noise/truncated inputs remain unowned. The fixture
begins with EIC enabled to verify that disabling before setup matters; removing
that disable is a failing control. Enabling EIC before rescue is also a failing
control. The original valid first request and delayed final UART byte both
survive the corrected ordering.

This is a producer-serialization repair, not a complete peripheral scheduler:

- Both-edge EIC has a pending bit, not an edge queue. Multiple transitions can
  coalesce; the handler reads the current pin level. The fixture explicitly
  retains that limitation.
- At gate release, a higher-priority UART completion can be serviced before a
  pending rising EIC callback. That callback resets the buffer and can discard
  the newly delivered byte. The fixture observes this existing ordering issue;
  the change promises preservation of the first owned request, not all bytes
  in a second overlapping receive window.
- A pending falling callback can inspect the same receive buffer after synthetic
  rescue. Ordinary init mailbox admission prevents a second owned request, but
  this review does not prove idempotence of every possible normal-class record
  under duplicated boundary observations.
- Peripheral setup still clears its flags at the existing initialization point.
  Retention applies to edges latched after that clear, not an inherited history.
  The test does not establish the state of a running inherited EIC handler before
  entry, the bootloader's complete interrupt handoff, or real synchronization time.
- No new buffer capacity, bus rate, optical behavior or physical timing policy
  is inferred. Root owns exact final build/stack/size and separately versioned
  candidate acceptance. This lane does not independently certify the proposed
  legacy diagnostic counter omissions.

Reproduce offline with a fresh private output directory:

```sh
python3 firmware/upstream-hardening/followup/28-startup-handoff-review/run.py \
  --source artifacts/private/absolute35a \
  --output artifacts/private/astra-28-replay
```

No adapter enumeration/open, USB/HID report, firmware upload, updater, app launch,
motor operation or canonical-state change was performed.

## Exact final 3.6 source check

After the preceding disposition, root supplied a stable private full candidate,
image SHA-256 `d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`,
manifest SHA-256 `ea2511bbdd7a833095df5b613579d0b69083efe3a44d26078d07efa8d51eccae`.
The runner's new `--candidate` option verifies the actual candidate binary and
every manifest source before and after testing. It copies and instruments the
candidate's final source directly, without reapplying the scoped transformation.
The candidate's final UART/EIC bodies and caller therefore include root's actual
version/counter composition rather than the earlier isolated overlay.

All **41 exact-final-source cases pass**, retaining the first request in each
rising-edge cut, servicing the final UART byte, preserving prior PRIMASK and
delivering pending flags. The same run retains all frozen-source, whole-mask and
three placement/removal controls: **287 asserted ASan/UBSan executions total**.
The source-only acceptance stands for this exact candidate. Actual ARM stack,
compiled NVIC ordering, code margin and release publication remain root's and
the compiled audit lane's separate checks.

[Final synthetic evidence](../../firmware/upstream-hardening/followup/28-startup-handoff-review/final36.json)
includes the exact source hashes and every final-candidate row. The full private
result `artifacts/private/astra-28-final36/result.json` has SHA-256
`83cbdfce60fc549365ac30a25706a8a1406216b76d2a9793615775463f4adf5a`.
Exact executed runner/fixture copies are retained beside both private result
generations; the earlier 246-case evidence remains separately preserved.

```sh
python3 firmware/upstream-hardening/followup/28-startup-handoff-review/run.py \
  --source artifacts/private/absolute35a \
  --candidate artifacts/private/handoff36a \
  --output artifacts/private/astra-28-final36-replay
```
