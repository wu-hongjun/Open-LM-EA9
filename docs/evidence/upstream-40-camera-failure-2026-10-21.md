# AF 4.0 — hard crash after two reported photos

**Camera acceptance failed; further 4.0 trials are held.** On the October 21 client
date the owner reported: “this time, hard crash and i had to power cycle after two
photos.” No further camera attempt is requested. This is stronger than the prior
3.9 report of blocked further capture with normal shutdown, but the mechanism is
not yet known.

[Sanitized receipt](upstream-40-camera-failure-2026-10-21.json) ·
[Strict installation record](upstream-40-upload-2026-10-20.md) ·
[Offline evidence](upstream-40-reference-2026-10-20.md) ·
[Preservation ledger](upstream-40-camera-preserved-2026-10-21.json).

## What is established

AF 4.0 was installed for the original Contax Zeiss 50mm f/1.4 and strictly verified
after an owner-confirmed physical reconnect: complete 20,480-byte image, pristine
1K diagnostic tail, expected metadata and protected flash/auxiliary windows.
The prior readback full-flash SHA256 is
`46c4d45590e03f9deb6bc325aaec531cef6511ee4a443a2b91e157cfcc815248`.
This remains a historical installation fact, distinct from failed camera acceptance.

The latest report establishes two reported photos, a hard camera crash and a
required power cycle. Whether two files saved, the actual focus/Pre-AF modes,
preview/aperture/exposure, motor behavior, exact crash trigger, power-switch versus
battery recovery, and shutdown behavior are unverified. One MF photo was requested;
the reported attempt is not relabeled a confirmed controlled MF cycle. No missing
value is inferred from the instructions or earlier trials.

## Read-only evidence gate

Post-camera logs have not been retrieved. The owner was asked to stop further
attempts and confirm that the camera is off/unpowered, the motor stopped, and the
adapter physically reconnected through its USB cap with TECHART Update and Open
LM-EA9 closed. No enumeration, open or report is sent while that confirmation is
pending. No firmware or stock restoration is performed.

Once confirmed, use the pinned signed native reader and canonical safeguards for
one guarded two-pass backup. Compare it with the pristine installed readback:
only diagnostic pages may differ; boot, application code outside diagnostics,
metadata and protected data must remain exact. Decode only with the 4.0 registry,
full image/manifest pins and writer/cohort consistency checks. Keep raw dumps,
keys, unit identifiers and real traffic private. A logged backup is not pristine
full-image installation verification.

Missing flash records after a hard power cycle can result from RAM loss or an
incomplete terminal flush. They do not establish no homing/servo/capture activity
or identify the crash location. Local TX return does not establish body acceptance.
The two reported photos do not prove successful optical AF, a qualified reference,
a resolved completion path or sustained capture. No new firmware fix follows from
this report alone; the new backup should discriminate those paths first.

## App hold and preservation

App 0.23.1/build 32 marks installed 4.0 held and disables ordinary installation of 4.0 from any
installed version. Read-only tools and recovery remain available; historical native
prepare/apply commands keep their exact research/recovery image pins. The original
4.0 image, manifest, patch, bundled resource, trusted digest and all earlier releases
remain unchanged. The prior signed app 0.23.0/build 31, CLI and bundles are preserved
privately. No canonical Application Support record is manually edited.

The ledger verifies 151 release/recovery/pin artifacts and every existing diagnostic
registry entry, including 4.0. Stock 1.8 recovery is unchanged. Software-only regression
and compiled audits remain valid within their documented supplied-I/O assumptions;
this camera failure means physical homing, reliable capture/shutdown, optical AF
and factory parity remain unqualified. Log retrieval and analysis are pending the
owner's safe USB-cap confirmation.

The previous app fails five intended hold/workflow assertions. After the narrow
UI hold change all 53 named Swift tests pass. Packaging and ad-hoc signatures
verify without launch; the native reader remains byte-identical to its prior pin.
No firmware/controller/source guard changed as part of this hold.
