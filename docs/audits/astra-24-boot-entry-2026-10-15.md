# Follow-up 24 — original boot entry contract into frozen C 3.5

The original PA23-low reset path preserves **CONTROL, PRIMASK and interrupt
priorities**, loads the application MSP and selects its vector table. With
explicit privileged thread-mode reset preconditions (`CONTROL=0`, `PRIMASK=0`,
no active exception), application frames use MSP. The boot code does **not**
normalize arbitrary inherited state. One important correction to a literal
“reset-like NVIC” assumption is established: **NVMCTRL IRQ5 is enabled before
handoff**, while its peripheral interrupt enables remain at their reset-zero
value in the modeled ordinary reset path. Boot SysTick is already running,
with its interrupt disabled.

This closes a bounded original-instruction software path, not physical boot
execution. No production-path failure under the stated ordinary-reset contract
was demonstrated; no startup rewrite, firmware patch, build or release change
is proposed. Frozen C 3.5 remains SHA-256
`04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632`.
The [lane 22 stack bound](astra-22-stack35-2026-10-15.md) remains conditional;
this audit supplies more precise conditions without changing its published
inputs or its 1,560-byte conservative envelope.

## Evidence and execution model

The [runner](../../firmware/upstream-hardening/followup/24-boot-entry/run.py),
[policy](../../firmware/upstream-hardening/followup/24-boot-entry/policy.json)
and [result](../../firmware/upstream-hardening/followup/24-boot-entry/result.json)
are source-bound. The original first 16 KiB have SHA-256
`8b6cb0bca7572748ddc1ba85bcb58ef261b8799898603e9b86a0ba4cb038c895`.
The retained original dump is read privately; only that boot region is loaded.
Unit calibration is replaced by synthetic zero/all-one fixtures. No private
binary, metadata, identifier or key is exported.

The runner pins the existing `artifacts/private/absolute35a` image, ELF, raw
image and manifest, verifies all **46** manifest source hashes, independently
compares ELF load bytes with raw/image bytes, and checks the actual ELF symbols
for every called application entry. The original boot inventory and local
vendor NVM register/IRQ definitions are also hash-bound. No build or external
service is needed.

Unicorn executes every original function call from boot reset `0x012c`, through
constructors, main `0x269c`, initialization `0x0114`/`0x0308`, strap selection
and launch, then the actual C 3.5 reset handler `0x5150` and constructors. It
stops at application main `0x82b4`, before executing main. There are **no
function-return stubs** in this composed trace. The reset-like case executes
23,707 instructions at 873 distinct instruction addresses. These are fixture
execution counts, not cycles, coverage percentages or stack measurements.

The hardware model is deliberately finite:

- MMIO is zero-initialized inert memory, with oscillator/DFLL readiness supplied
  at `0x4000080c`, synchronization status zero, PA23 supplied at PORT IN, and
  synthetic calibration at `0x00806024`. GPIO write aliases are not a complete
  PORT model; DIR remains input for the selected strap fixture. This matches
  the intended PA23 input decision but proves no pin/electrical behavior.
- NVIC enable/disable and pending set/clear aliases have explicit W1S/W1C
  behavior. Priority bytes are modeled memory. No interrupt scheduler,
  exception entry/return, active-exception nesting, DMA, NVM command execution,
  clock progression or elapsed time is implemented.
- `CONTROL`, PRIMASK, MSP and PSP use Unicorn's special registers. Privileged
  thread mode and absent active exceptions are preconditions, not observations
  of a processor reset. Initial PSP `0x20006000` is a synthetic sentinel; the
  normal path does not select it.
- A strap-high case stops at `0x3380` before the later USB runtime branch.
  Earlier inert USB initialization instructions do execute on both paths.
  A missing-readiness case stops by an explicit instruction visit budget;
  it establishes that the selected poll blocks handoff in this model, not a
  physical timeout or recovery guarantee.

As in the prior REA work, this Unicorn Cortex-M0 configuration can accept some
unsupported instructions. Execution alone does not certify ARMv6-M legality.

## Resolved path contracts

| Original site | Established instruction behavior |
| --- | --- |
| `0x012c` reset, through `0x01b6` | Initializes boot data/BSS, writes VTOR=0, executes constructors, calls main; no CONTROL/PSP normalization |
| NVM init `0x0db8`, stores `0x0dec`, `0x0dfa`, `0x0dfc` | Disables IRQ5, executes DSB/ISB, clears pending IRQ5, enables IRQ5; other enable/pending bits survive |
| SysTick init `0x11c4`, `0x11c8` | Writes LOAD=`0xffffff`, CTRL=5: ENABLE and CLKSOURCE set, TICKINT clear; does not clear all system pending state |
| Strap critical section `0x0384`–`0x039c`, called by main | Saves PRIMASK to its local stack, masks interrupts, samples strap, restores the saved PRIMASK before branching |
| Launch `0x2518`, `0x251e`, `0x2524` | Loads MSP from application vector, writes VTOR=`0x5000`, calls application reset; preserves CONTROL/PSP selection and PRIMASK |
| C 3.5 reset `0x5150` through main entry | Uses 16 bytes of stack, initializes application data/BSS, writes VTOR again at `0x5192`, executes constructors; preserves inherited core mask/stack selection, NVIC enables/pending and priorities |

The MSP/VTOR assignment was already established in the
[stock boot reconstruction](../reverse-engineering/stock-boot-reconstruction.md),
evidence `ev_af84eb17e704f414c6a70060f43666c376cc40e1828175a44552db137154b0c6`.
It is reused here as a checkpoint within the longer original path, not claimed
as a new discovery or physical validation.

At application entry, the ordinary reset fixture yields:

| State | Value |
| --- | --- |
| CONTROL / PRIMASK / IPSR | 0 / 0 / 0 |
| Active thread stack / MSP | `0x20002c00` / `0x20002c00` |
| VTOR | `0x5000` |
| NVIC enables / pending | `0x20` / 0 |
| All modeled priorities | Reset value zero |
| SysTick CTRL / LOAD | 5 / `0xffffff` |
| NVM peripheral INTEN | 0 |

Main entry retains the application's 16-byte reset frame, so MSP is
`0x20002bf0`. The boot frames below the old MSP are not charged as live
application frames after MSP replacement. This conclusion requires CONTROL's
MSP selection and the nonreturning application reset path.

The launch transition is **not interrupt-masked**: at `0x251c`, MSP is already
the application value while VTOR is still zero; at `0x2520`, both have changed.
There is no DSB/ISB in this launch sequence. The earlier NVM-init barriers are
not handoff barriers. The finite no-exception trace does not establish atomic
handoff, delivery ordering or architectural synchronization under exceptions.

## NVM IRQ5 and active/pending qualification

The local pinned SAMD21 definition names IRQ5 NVMCTRL. Its INTENCLR and INTENSET
reset values are both zero. The complete composed low-strap trace makes no
write to either peripheral interrupt-enable alias. With a real reset that
establishes those peripheral defaults and no outside pend source, enabling
NVIC IRQ5 alone does not demonstrate a pending NVM interrupt. The original
code explicitly clears pending IRQ5 before enabling it. USB IRQ7 is not enabled
on the low-strap path; the later enable is on the USB runtime branch.

C 3.5's IRQ5 vector points to `Dummy_Handler` at `0x514c`; its current startup
and relevant initializers preserve that NVIC enable. An unexpected delivered
IRQ5 would therefore enter the default loop. This is a conditional consequence,
**not a demonstrated reachable cold-start defect**: this work does not supply
a production-path cause that sets the NVM peripheral enable or a pending IRQ5
after its clear under the ordinary reset contract. Arbitrary inherited IRQ
state or an injected pending bit must not be mislabeled such a cause.

Similarly, the absence of an active exception in the trace follows the model's
thread-mode/no-delivery preconditions. A normal processor reset plus quiescent
interrupt sources supports that interpretation, but neither Unicorn's mapped
NVIC words nor a software branch proves actual active state. NMI, HardFault,
late pending arrivals, debugger interventions, warm jumps, failed stacking and
memory corruption remain outside this experiment. Pending SysTick/PendSV bits
are not globally cleared by this software path; synthetic nonzero system
pending bits survive.

## Current application initialization comparison

After the composed reset trace, the runner additionally calls the actual linked
`delay_init`, `em_uart_init`, and `em_eic_init` routines in isolation, in the
source's initialization order. Their callees execute normally. Only EIC and
SERCOM1 SWRST completion reads receive explicit self-clear fixtures. This is
**not execution of the intervening foreground main, diagnostic NVM work, sensor
initialization or complete peripheral startup**.

Two priority fixtures (zero and `0xc0`) both confirm:

- `delay_init` writes LOAD=47,999, VAL=0 and CTRL=7, explicitly enabling SysTick
  interrupts. It does not set SysTick priority.
- `em_uart_init` enables SERCOM1 IRQ10 and does not set its priority.
- `em_eic_init` sets EIC IRQ4 priority to `0x40` (logical priority 1), then
  enables IRQ4. Other priority bytes are preserved.
- The combined NVIC enable mask becomes `0x430`: inherited NVM IRQ5 plus
  SERCOM1 IRQ10 and EIC IRQ4.

Thus the ordinary-reset/no-interference preconditions, combined with the
original path's preservation, support the prior default-priority reasoning for
SERCOM1/SysTick. The app does not enforce that reasoning for arbitrary callers.
This refines the normal-path assumptions underlying audits 14/22; it does not
replace their conservative all-vector envelope or physical acceptance gates.

## Sensitivity and negative controls

Six complete boot-to-main configurations pass: reset-like; all-one synthetic
calibration; incoming PRIMASK=1; incoming CONTROL.SPSEL=1; unrelated NVIC
state/priorities/system-pending bits; and combined non-reset state. Two branch
controls cover strap-high and absent oscillator readiness. The two initializer
fixtures are separate tests and must not be counted as full reset-to-operating
application executions.

Nine negative controls reject overstatements or deliberately broken behavior:

1. Remove original MSP assignment: application-stack contract fails.
2. Remove original launch VTOR store: the **entry** contract fails even though
   the later application reset would write VTOR itself.
3. Remove PRIMASK restore: the originally zero mask remains set.
4. Remove NVM NVIC enable: inherited IRQ5 contract fails.
5. Remove pending-IRQ5 clear with a synthetic initial pending bit: clear
   contract fails.
6. Change boot SysTick to enable TICKINT: interrupt-disabled contract fails.
7. Assume incoming PRIMASK=1 becomes zero: disproved.
8. Assume incoming PSP selection becomes MSP selection: disproved; MSP is
   loaded but application thread frames continue on synthetic PSP.
9. Assume unrelated incoming pending IRQ bits are cleared: disproved.

The first six mutate only an emulator's private in-memory instruction copy.
The last three reject unjustified normalization claims. They are not firmware
fixes, physical fault injection or evidence that arbitrary non-reset states
occur during the ordinary factory cold start. Inputs are rechecked after all
mutations; original boot files and C 3.5 artifacts remain unchanged.

```sh
tools/rea-analysis/venv/bin/python \
  firmware/upstream-hardening/followup/24-boot-entry/run.py \
  --output artifacts/private/astra-24-entry-recheck.json
```

No network, enumeration, USB/HID device open or report, updater, flash, motor,
app launch, canonical Application Support write, commit or published-artifact
modification occurred. Physical entry, asynchronous exception transition,
stack high-water and camera behavior remain separate acceptance gates.

## Separate requested consumer check: legacy RX snapshot

Root requested an independent review of a possible footprint-only guard around
`em_rx_bytes_at_open = em_rx_bytes` after another proposed change missed the
required code-margin floor. This is separate from the boot-entry findings.
The [consumer runner](../../firmware/upstream-hardening/followup/24-boot-entry/review_snapshot.py)
and [result](../../firmware/upstream-hardening/followup/24-boot-entry/snapshot-review.json)
verify all 46 frozen source hashes and preprocess every one of the **22** ARM
translation units with the exact release flags/per-unit optimization flags.
They additionally preprocess all 22 with only `EA9_NO_LOG` removed.

In the release, the identifier occurs only in declarations, its definition,
and the single assignment in `emount.c:1529`; there is no read or address-taking
consumer. Across the raw C/header sources its sole read is the legacy main
logging-page subtraction at `main.c:1716`, excluded by `EA9_NO_LOG`. The live
`em_rx_bytes` counter is a separate volatile RAM object.

A private proposal wrapping only that assignment in `#ifndef EA9_NO_LOG`
produces release `emount.c` preprocessed text identical except for removing that
statement. The logging-enabled comparison is byte-identical. Every other
statement, including live RX counter, trace and wire work, is retained. This
supports the narrowly scoped release omission on consumer evidence; it is not
a linked code-size measurement or a substitute for root's full candidate
validation. No shared source was edited.

| Frozen source | SHA-256 |
| --- | --- |
| `src/emount.c` | `9127671f5f27fb20c9732972881e74af932f149df9f2108254207cb6618f0feb` |
| `src/main.c` | `982c1beb7dca621fd2c403e1f7bc670f2859003c960265bad936c6f348c9b3b3` |
| `src/em_uart.c` | `2bf37e208fbeae06da09288633dec559ca444e52e84e1f6ec440f753f68ae3ee` |

```sh
python3 firmware/upstream-hardening/followup/24-boot-entry/review_snapshot.py \
  --output artifacts/private/astra-24-snapshot-review-recheck.json
```
