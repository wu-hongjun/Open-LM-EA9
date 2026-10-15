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
