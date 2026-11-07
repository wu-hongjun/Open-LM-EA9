# Hardware targets

`lm-ea9/` is the first implemented target. Its source and build rules reproduce
working 4.5.0 exactly; its original recovery files remain in `../recovery/`.
Shared protocol/metadata code lives in `../core/`.

A target contains `target.json`, `src/`, and its own makefiles. Target descriptors
select memory limits, dependencies and build rules. Core and target files are
flattened into an isolated build directory; duplicate names are rejected.

To start a hardware port, copy `lm-ea9/` into a new lowercase target ID, update
the descriptor and replace the board, startup, clock, power, bus, encoder, motor,
servo and linker implementation for that hardware. The current build driver
expects an ARM GNU toolchain, ELF `_etext`, `_srelocate`, `_erelocate`, `_estack`
symbols and a contiguous padded application image. A different architecture or
loader needs its own build/image support. Existing makefiles contain SAMD21 flags.

The macOS USB implementation and upload qualification are LM-EA9 specific.
A firmware target does not automatically create another USB transport or qualify
an image. See [customization](../../docs/customization.md).
