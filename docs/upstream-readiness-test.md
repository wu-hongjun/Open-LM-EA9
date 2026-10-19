# AF 3.8 future owner-coordinated camera check

**3.8 upload and strict verification passed after physical reconnect, including
an independent full-image/protected-data audit. One camera cycle and log
retrieval are pending; no camera result is known.**
[Live installation record](evidence/upstream-38-upload-2026-10-19.md).
The owner separately authorized the upload and one post-verification cycle.
The earlier 3.7 hold remains after capture freezes requiring battery removal.
The gates below do not establish that 3.8 fixes the physical failure.

[Candidate and pins](../firmware/candidates/3.8.0/README.md) ·
[Offline evidence](evidence/upstream-38-readiness-2026-10-19.md).

1. On separate owner authorization, close the official updater and Open LM-EA9
   app, confirm the adapter is on its USB cap, and preserve a fresh two-pass
   full backup plus the existing 3.7 diagnostic cohorts. Do not discard a
   pending journal or bypass a reconnect/safety guard.
2. Upload only the pinned original Contax Zeiss 50mm f/1.4 3.8 candidate through
   the existing guarded path. After successful upload, send no further reports
   on that armed connection. Require the owner's explicit physical unplug/
   reconnect confirmation.
3. Strictly verify the complete application, metadata, erased diagnostic tail
   and unchanged protected/factory data against the pre-upload backup; perform
   the separate offline readback audit. A matching version alone is not enough.
   Stop on any mismatch. No camera use until verification passes.
4. Coordinate one loaded-lens lifecycle cycle with the A7C II off and camera
   USB disconnected before mounting. Set the physical 50mm focus ring to
   infinity and iris to f/1.4. Select still-photo A, EV 0, Auto ISO, **MF** and
   Pre-AF Off where available. Record the actual settings; A exposure mode
   alone is not MF. If MF cannot be confirmed, skip the photo.
5. Switch on without shutter/AF-ON input. Note live preview, brightness,
   aperture and motor behavior. Wait ten seconds after any movement stops.
   Only if preview/motor behavior is normal and MF is confirmed, take one
   photo. Switch off once and leave it off. AF-S is a separate later decision
   after reviewing this cycle's logs; no repeated restarts or captures.
6. Stop for frozen preview, grinding, repeated stop impacts or abnormal
   continuous driving for about two seconds. Switch off; remove the battery
   if unresponsive or motion continues. Do not retry. Normal shutdown alone
   does not establish capture compatibility.
7. Once the camera is off/unpowered and the motor stopped, return the adapter
   to the USB cap. Require explicit physical reconnect and closed-app/updater
   confirmation before read-only log retrieval. Preserve the first post-test
   two-pass backup, then decode it offline using the registry-bound 3.8 decoder.
   Do not flash another image before preserving those logs.

Record MF/AF-S/AF-C and Pre-AF as observed or unknown; preview/aperture/exposure;
movement/stopping/idle; half-press versus full-press if relevant; actual saved
files; shutdown and battery removal; and the evidence cohort for each attempt.
Do not attribute older terminal pages to a new cycle. Raw dumps, operands,
identifiers and camera files stay private.

3.8 distinguishes drive stillness failure (17), settle stillness failure (18)
and shared poll-budget exhaustion (19). A label identifies a software branch,
not a measured mechanical cause or end stop. A retained first fault can mask a
later inhibit; a late fatal footer may differ from the earlier persisted summary.
Missing footer records can mean no room or an interrupted append and cannot
locate the camera freeze. Camera acceptance requires observed successful
capture/shutdown, not merely host tests or a locally returned UART send.
