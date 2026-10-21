# Offline crash persistence acceptance

This lane tests actual candidate trace C and decoder code using synthetic bytes.
It cannot establish physical watchdog timing, flash atomicity, or camera health.
Only a CRC-valid, version-bound retained checkpoint is eligible after a qualified
warm reset. A cold reset, bad checkpoint, or interrupted checkpoint update must
not manufacture a recovered snapshot. Battery removal before watchdog reset and
boot-time append may lose all volatile evidence. Even a durable baseline proves
only that boot reached that append, not that capture or shutdown was healthy.

The 1 KiB tail remains sixteen append-only 64-byte pages. A page write interrupted
at any byte must not decode as the intended complete record unless its final bytes
already equal erased flash. This byte-prefix test is a fault-injection schedule,
not a claim that hardware programs bytes serially. Independently corrupt every
bit of the page to check the envelope checksum. A write failure consumes the
attempt and blocks later writes in that boot. Reboot resumes strictly beyond the
highest valid occupied slot; any occupied bad-CRC page instead latches fail-stop
as storage damage. It never reuses holes.

Retained RAM must invalidate its commit marker before modification and publish
it last. Schema identity and checksum both bind the retained bytes. Cold reset
bits must override warm bits. A valid old checkpoint after an ineligible reset
must be discarded, and a consumed checkpoint must not replay after another reset.
Source-level interruption injection is required because complete-call tests alone
cannot detect a prematurely published commit marker.

A boot-only crash record is independent of legacy summary/motion/event cohorts.
Do not let it assemble a snapshot, satisfy a shutdown footer, claim a complete
session, or lend its old timestamp to the new boot. Captured summary fields are
checkpoint observations and can predate the lockup. A record's reset cause is an
observed register bitmask, not a diagnosed root cause. Unsupported firmware/schema
versions and semantically impossible reset/recovery combinations fail closed.

All raw fixture output goes under a fresh `artifacts/private/astra54-*` directory.
No hardware or canonical host state is accessed. Frozen 4.0 inputs and published
artifacts must remain byte-identical.

Run `python3 firmware/upstream-hardening/followup/54-crash-powerloss/run.py --output artifacts/private/astra54-NEW`.
Optional `--candidate PRIVATE_BUILD` verifies and tests an already integrated build.
The default applies lane52 to a private copy of pinned frozen4.0. The ST_HOST boundary
omits the ELF section attribute; the harness injects interruption hooks after actual
checkpoint write boundaries. Six C mutation controls must fail. ARM/linker/reset
integration and decoder semantics require their separate acceptance lanes.
