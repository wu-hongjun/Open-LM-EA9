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

The package and metadata mailbox remain offline experiments. The current app
does not install them or transmit settings. See docs/profile-bank-2026-11-07.md
from the repository root for design, tests and remaining qualification gates.
