# AF 3.9 — late homing qualification and blocked further photos

**Camera acceptance failed; further 3.9 trials are held.** The owner reports two
photos followed by refusal to take more, with **normal shutdown**, then return
to the computer. This is not recorded as another camera freeze or battery-required
recovery. Actual focus/Pre-AF, aperture, preview state and saved-file status are
unverified. Retrospective clarification tentatively recalls AF-S but explicitly
states uncertainty; focus mode remains unconfirmed. No extra test was requested.

[Sanitized receipt](upstream-39-camera-failure-2026-10-20.json) ·
[Strict installation record](upstream-39-upload-2026-10-20.md) ·
[Offline work](upstream-39-homing-2026-10-20.md) ·
[Candidate](../../firmware/candidates/3.9.0/README.md).

## Read-only retrieval and preservation

Return to the USB cap was inferred from the answer to the cap-return question
and confirmed by a new qualified LM-EA9 connection. Both apps were absent by
process check; the same signed reader and image/manifest pins matched. The
3.9 verified journal was unchanged and no update remained pending. Descriptor
inventory sent no reports. One guarded native backup performed two matching
131,072-byte flash reads and two auxiliary passes, 4,359 CHECK/READ exchanges,
with no write, erase, restore or retry. Raw backups, keys, identifiers and real
camera frames/operands remain private.

The filesystem audit confirms recognized boot code and MCU/geometry, every file
size/digest, same-unit binding and a new connection. Exactly 893 bytes changed,
all within diagnostic slots 0–13 in `[0x9c00,0xa000)`. Every flash byte outside
that range, user row, calibration and device-ID windows is unchanged. Pending,
applied-lens, firmware-observation, stock-qualification, library and blocked-
connection records remain unchanged; no safety marker was edited manually.
All 49 reconstructed source pins, 141 inventoried historical release/recovery
artifacts, old registry entries and original stock recovery remain exact.

Pristine verified flash SHA-256:
`be84ddc1c99e618280175af8af44b12e632abb5ab311edbb4d49a60dbe6a1798`.
Post-camera flash SHA-256:
`3a98241ee1d6b031fed4656ca1b5bb12d7b62730c849027c5eaf29a22e911791`.
The original strict installation remains verified as recorded. This later
backup intentionally includes logs and is not relabeled full-image verification.

## What the new home snapshot establishes

The registry-bound decoder finds 14 valid pages, zero torn/inconsistent/
unassociated pages and two erased pages. One complete planned cohort retains
all 32 focused events and all three motion chunks, with zero capacity omissions.
It also records 35 older-event evictions and 7,423 filtered routine observations;
this is not the complete bus history or a physical boot counter. The summary
has 930 RX frames, 932 local TX returns, zero reported UART errors, handshake and
UART-disable observations. The same phase 17 drive failure seen in 3.8 persists
after release ADC telemetry removal.

The 3.9 tail is writer-consistent, with no initialized AF-servo snapshot. It
records:

| Existing software observation | Retained value |
| --- | --- |
| Fault | 17, `home-drive-unsettled` |
| Drive qualified / settle entered | No / no |
| Phase start to after-inhibit tick | 300 |
| Shared poll count | 7,099 of 1,000,000 budget |
| Stillness anchor age at cutoff | 20 ticks; qualification requires 40 |
| Anchor displacement from pre-drive coordinate | −2,902 encoder counts |
| Last entered iteration start | Phase tick 299 |
| Last iteration start to after-inhibit tick | 1 |
| Later consumed non-Stop requests | 17, unsaturated |

The stillness anchor is the initial or latest threshold-crossing observation,
not a final raw sample or measured end-stop arrival. At the cutoff its age was
only 20 ticks, below the 40 required by the unchanged policy. The final entered
iteration began at 299 and reached inhibition at 300; this snapshot does not show
a long final returning pump crossing the deadline. It does not exclude earlier
long iterations, slow arrival, stiction, threshold noise or electrical effects.
The displacement is software encoder travel, not calibrated physical movement
or proof of polarity. SysTick intervals can wrap or lose ticks; none of these
numbers is a measured motor/IRQ/peripheral duration.

This narrows the failure from an unspecified home timeout to insufficient
retained stillness before the drive cap. It does **not** justify simply raising
duty/deadline, assuming an end stop or forcing reference readiness. The factory
persisted-origin and conditional-home contracts remain distinct from this
upstream replacement policy; the prior REA findings and limits still apply.
ADC dependency removal is a verified software repair, but did not resolve this
observed drive-phase failure.

After failure the source keeps reference readiness false and inhibition sticky.
Seventeen later non-Stop commands were actually consumed while inhibited, with
no normal servo execution. This supplies the discriminator missing in 3.8 and
explains a path to unresponsive focus. It does not identify 17 shutter attempts,
prove the two files were saved, establish focus acquisition, identify actual
focus mode, or prove why the body refused further capture. Commands can be
coalesced/discarded; Stop is excluded and sessions can share the record.

## Retained capture and shutdown evidence

Four ordinary owners and one raw owner complete successfully in the valid
retained session. All six local TX START/RETURN pairs match, including shutdown;
there is no unmatched retained START/RETURN. Raw completion precedes shutdown
admission by one software tick, with no later ordinary completion retained.
This exchange cannot be mapped to either reported photo or the first blocked
shutter attempt. Local send return is not body acceptance. The retained data
provide no basis to change the REA-supported raw-readiness re-arm policy.

Shutdown acknowledgement and UART disable are followed by VD-timeout and PA23
write breadcrumbs. There is no tail-delay-return footer despite two free slots.
As in earlier studies, missing records cannot distinguish power removal,
interrupted delay or append failure and do not prove a hang. The owner's normal
shutdown is independent evidence; the PA23 breadcrumb is not a voltage measurement.

## Disposition

Keep 3.9 held and the adapter on its USB cap. Two free pages cannot retain another
full planned event/motion snapshot, and no further camera attempt is requested.
No additional firmware was flashed during log retrieval, and stock was not restored. The next offline work
should address reference qualification using the new late-anchor evidence and
the factory calibration/origin findings, while preserving bounded drive and
capture/shutdown ownership. The physical cause and shutter decision remain
unresolved; successful sustained capture, optical AF and factory parity are not
established. Any later production change needs a new candidate version.

App 0.22.1/build 30 records the 3.9 hold and disables ordinary installation from
other versions while retaining backup/recovery and all native command/image pins.
All 53 named host tests pass. The package and signatures verify without launch;
the reader CLI remains byte-identical and the previous signed package is retained
privately. No canonical state was manually changed for the UI update.
