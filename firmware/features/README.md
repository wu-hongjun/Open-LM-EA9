# Optional firmware features

The canonical working source and target build remain unchanged. The opt-in
4.8 builder assembles profile_bank with the LM-EA9 profile-bank port in an
isolated directory; default firmware still reproduces 4.5 exactly.

profile_bank.c/h contains a byte-format codec and a portable journal with an
injected read/program/erase interface. profile_runtime.c binds committed optical
metadata to the E-mount responder at startup. SAMD21 register operations and
physical addresses live under targets/lm-ea9/profile-bank, not in the journal.
Porting requires a qualified storage layout, hardware implementation, linker and
transport; copying this target's addresses is not a safe generic default.

The firmware remains unflashed for this work. The host now provides explicitly
acknowledged experimental installation/selection, with normal switching gated
by verified transport evidence. See docs/bank-migration-2026-11-07.md from the
repository root for the current integration and remaining hardware gates.
