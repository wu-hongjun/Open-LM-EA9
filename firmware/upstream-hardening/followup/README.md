# Post-3.3 workbench

This work preserves published 3.3 and all earlier artifacts. It is **not another
firmware candidate**. Future executable changes require a new version and full
release/host/physical acceptance gates. Root completed lanes 12/13 source tests
after their Astra turns were interrupted; Astra 14 completed the stack audit and
root reran its analyzer/negative guards. Do not count the interrupted turns as
additional completed Astra audits.

- [12: query lifetime and work budget](../../../docs/audits/astra-12-query-2026-10-15.md).
- [13: reachable numeric failures and partial proposal](../../../docs/audits/astra-13-numeric-2026-10-15.md).
- [14: exact 3.3 whole-chain stack bounds](../../../docs/audits/astra-14-stack-2026-10-15.md).

The 12-query and 13-numeric applicators refuse non-private scratch paths.
`measure.py` composes 13 then 12 against pinned 3.3 sources and compiles the actual
ARM units with the recorded release flags. It deliberately produces no binary
image. The current combined analysis link ends at `0x9e84`, **644 bytes beyond**
the diagnostic boundary and 900 bytes short of the required 256-byte margin.
The linker exits successfully because its text layout alone does not enforce
that initialized-data load bytes avoid the diagnostic region; root's release
builder correctly checks code plus initialized data. A successful link is
therefore not release acceptance.

```sh
python3 firmware/upstream-hardening/followup/measure.py --output artifacts/private/followup-size-recheck
```

[Measurement](measurement.json) and [preservation inventory](preserved.json)
record actual results. The future overlays have bounded source tests but lack
complete arithmetic closure, full composed regression/host packaging, a fitting
release image and physical qualification. Leave 3.3 frozen and do not select this
workbench for upload. Remaining work is evidence-driven, bounded arithmetic and
footprint simplification, not removing established guards or shortening logs to
hide the size failure. The stack result applies to frozen 3.3 only; changed code
needs new compiled-call-chain analysis.


## Resolved next-candidate disposition

The text above records the rejected partial-widening measurement. Subsequent
Astra [15 range](../../../docs/audits/astra-15-coordinate-2026-10-15.md),
[16 query flow](../../../docs/audits/astra-16-query-flow-2026-10-15.md),
[17 composition](../../../docs/audits/astra-17-composition-2026-10-15.md) and
[18 exact stack](../../../docs/audits/astra-18-stack34-2026-10-15.md) audits
support a different, fitting composition in [../next](../next/README.md).
The separately frozen [3.4 image](../../candidates/3.4.0/README.md) has complete
offline release/host checks and 276 bytes before logs. The partial 13 overlay
is not used; reviewed coordinate admission bounds the unchanged control math.
Physical acceptance remains open, and no original workbench or released image
has been overwritten.

## Target and time follow-ups

Distinct Astra lanes [19 target](../../../docs/audits/astra-19-absolute-target-2026-10-15.md),
[20 time](../../../docs/audits/astra-20-time-contract-2026-10-15.md),
[21 workload](../../../docs/audits/astra-21-workload-2026-10-15.md),
[22 compiled stack](../../../docs/audits/astra-22-stack35-2026-10-15.md) and
[23 final composition](../../../docs/audits/astra-23-composition35-2026-10-15.md)
support the separately versioned [3.5 composition](../next35/README.md).
Root integrated the verified target/time changes and a measured release-only
counter omission. Exact final regressions, independent stack/composition review,
repeat builds and host checks pass. Hardware timing and camera acceptance remain
open. The public captures contain no query records in the inspected traffic and
do not establish a real query deadline; synthetic capacity tests do not justify
an arbitrary buffer or scheduling change. Original overlays and releases stay frozen.

## Startup and observability follow-ups

The [3.6 workbench](../next36/README.md) accepts a scoped EIC startup handoff;
the earlier full-PRIMASK proposal is rejected after independent late-UART-byte
tests. Astra24 supplies conditional original boot-entry facts, Astra25 supplies
the host diagnostic-cohort fix, root26 completes the interrupted startup lead,
root27 checks compiled 3.5 peripheral polling, Astra28 reviews exact final 3.6
source, and Astra29 validates compiled ordering and stack. Their reports and
failing controls are indexed in the
[campaign](../../../docs/audits/astra-hardening-campaign-2026-10-15.md).
No interrupted or root-only scope is counted as another completed Astra lane.
Published images/recovery stay frozen; physical camera qualification is pending.
