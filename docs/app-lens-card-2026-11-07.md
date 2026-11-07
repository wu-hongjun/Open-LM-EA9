# Lens card and adapter status

App 0.28.0 (build 39) retains the two-card home and secondary Lens Library.
The Adapter card shows automatic connection status, operation/reconnect state,
firmware and the last verified profile for that unit, with its timestamp.
Read adapter and Verify profile are available on the card. Backups, firmware
installation and recovery remain behind USB tools.

Discovery reads OS descriptors and bounded local history every two seconds;
it does not silently send USB reports. Read explicitly takes a two-pass backup
and inspects it. Cached information is labeled last verified.

The Lens card has an eight-lens dropdown, reference photo, focal length/nominal
aperture, Sony dial range and physical-aperture-unknown indication. Edit opens
the selected lens's local editor. Choosing a lens changes only the local
preparation, preserving installed data and the update journal. Status distinguishes
selected/not applied, on adapter/last verified and uploaded/verification needed.
The app cannot detect which passive lens is physically mounted.

The current cap cannot perform a qualified parameter-only change. Its fallback
button is therefore **Update lens firmware**. Confirmation describes the
concrete lens/startup report, backup, whole-application rewrite, reconnect and
pending 4.7 camera validation. The preferred product design is
[bank plus wear-leveled settings](lens-profile-persistence.md).

The fallback uses a pinned 4.7 template and narrowly canonical personalized
images. Invalid metadata, unqualified adapters, corrupt/stale history, dirty
edits, pending verification, blocked connections and previews cannot start it.
A fresh backup and native source admission remain mandatory. Only complete
reconnect verification publishes a new on-adapter setting.

## Verification

56 named Swift tests pass, including eight-profile image generation, tampering,
image-bound cached history, source admission, upload/reconnect guards, local-only
selection and home-screen verification. Production C protocol/servo suites and
their failing controls pass for the template. Eight profile C fixtures and an
ignored-startup-word negative control pass. Clean builds still reproduce the
published 4.5 and 4.6 digests exactly.

An isolated USB-disabled native preview was visually reviewed. Selecting the
35mm Distagon changed the right photo, numbers and selected state; the left card
retained the verified 58mm Biotar and 4.6.0. All eight menu choices and the main
actions were visible at the default size. No production app state was used.

No HID report, firmware upload, motor action, settings write or bootloader
modification was performed in this app work. Camera qualification and a low-write
settings transport remain separate milestones.

[Sanitized software-verification evidence](evidence/lens-card-2026-11-07.json).
