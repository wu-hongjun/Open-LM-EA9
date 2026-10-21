# Offline crash hardware audit

`boot_retention.py` instruments the pinned original bootloader using the existing lane24 finite Unicorn model. Run from repository root:

```
tools/rea-analysis/venv/bin/python firmware/upstream-hardening/followup/53-crash-hardware-audit/boot_retention.py
```

The runner reads retained private boot evidence and lane24's pinned C3.5 application fixture only. It executes original boot instructions up to application reset, with synthetic calibration/PA23/clock-readiness inputs, and observes SRAM writes. It does not inspect USB devices, initialize the application, perform hardware NVM commands, or model elapsed time, exception delivery, DMA, electrical state, or physical retention. The WDT cause register is a supplied inert fixture. The report is `boot-retention.json`.

The complete design/hardware review is in `docs/audits/astra-53-crash-hardware-2026-10-21.md`. New AF4.1 compiled verification is a separate step; this legacy-fixture boot test does not certify a new app's linker layout or reset handler.
