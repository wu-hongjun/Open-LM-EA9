# AF 4.0 upload — October 20, 2026

**Upload completed; physical USB-cap reconnect and strict byte/protected-data
verification are pending. Keep the adapter off the camera.** No readback reports
were sent after upload. Camera testing and log retrieval require later owner steps.

[Sanitized receipt](upstream-40-upload-2026-10-20.json) ·
[Candidate and pins](../../firmware/candidates/4.0.0/README.md) ·
[Offline qualification evidence](upstream-40-reference-2026-10-20.md) ·
[Separate one-cycle procedure](../upstream-reference-test.md).

## Preflight and upload

The owner explicitly authorized AF 4.0 upload for the original Contax Zeiss 50mm
f/1.4, physical reconnect verification, one A7C II cycle, log retrieval,
documentation and commit/push, and confirmed the USB cap with both apps closed.
Starting commit `77b3104ce18618ca0856e456b0a2df7d43844447` was pushed and the tree clean. The signed
app 0.23.0/build 31 CLI, full image/manifest and bundled resource pins match the
committed offline receipt. No updater, prototype app or competing CLI was running.
Descriptor-only inventory found one qualified, unblocked adapter and sent no reports.
The prior 3.9 journal was strictly verified. Native prepare-only output with a private
copy of the saved lens library matched all 20,480 pinned bytes.

`dist/ea9ctl apply-reference-upstream contax-zeiss-50-f1-4 --idle` ran once through
canonical native safeguards and exited 0 at **2026-10-21T02:23:08.684002+00:00 UTC**
(**2026-10-20T22:23:08.684002-04:00 America/New_York**). The uploader saved its fresh
complete two-pass backup before START, retained exclusive access/same-unit stock
qualification, verified the final idle address-scratch read and synchronized the
durable transaction journal before writing. No guard or source was changed.

The pre-upload backup reports 3.9.0, with two matching 131,072-byte flash passes and
two auxiliary passes: 4,359 CHECK/READ exchanges. Independent filesystem verification
checks every file size/digest, known boot hash, MCU identity/geometry, same-unit
binding and immutable 3.9 prefix. Its full-flash SHA256 is
`3a98241ee1d6b031fed4656ca1b5bb12d7b62730c849027c5eaf29a22e911791`. Full flash and protected auxiliary windows
match the retained post-camera 3.9 backup, preserving the existing failure evidence.

Image SHA256: `06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae`.
Manifest SHA256: `8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`.
The fixed original 50mm profile retains nominal f/1.4, ID 234 and Unknown actual iris.
This installs the existing reviewed candidate; runtime profile layout, controller,
capture/shutdown ownership, original stock recovery and all prior images are unchanged.

The successful pinned engine implies one acknowledged START and 320 acknowledged
64-byte pages. These are engine-derived counts, not an independent wire capture.
No retry, CHECK/READ, end marker or extra padding followed START on the armed
connection. No report was sent after the native uploader returned. The expected
new journal image, metadata, uploaded timestamp and armed-connection marker pass
filesystem-only checks. Prior marker membership is preserved; applied-lens,
firmware-observation, stock-qualification and library records remain unchanged
pending verification. No canonical journal or safety marker was manually edited.

## Remaining steps

A physical unplug/reconnect and explicit owner confirmation are required before
post-upload reports. Native strict verification must check all 20,480 application
bytes, including the blank 1K diagnostic tail, plus known metadata and protected
flash/user-row/calibration/device-ID data. The six established loader scratch
bytes remain the only flash exclusion. A version read or code-prefix comparison
alone is insufficient. An independent saved-file audit follows native verification.

Only then guide one loaded-lens cycle: start without shutter input, check normal
live preview/motor behavior, confirm **MF separately from A exposure mode** and
Pre-AF Off, wait 10 quiet seconds, take at most one photo if all prerequisites hold,
and shut down once. If MF cannot be confirmed, skip the photo. Freeze or abnormal
drive means stop, switch off, remove the battery if unresponsive, and do not retry.
The camera menu can be set after the single startup; no setup restart is requested.
After camera power-off/unpower and stopped motor, the owner must explicitly confirm
USB-cap reconnect with both apps closed before guarded read-only backup/log retrieval.
Leave unobserved settings/outcomes unknown. AF-S is a later gate after review.

All 146 historical release/recovery/pin artifacts and older registry entries remain
exact. The current 4.0 image/manifest/resource/CLI pins match. Raw backups, keys,
unit identifiers and real frames remain private. 3.9 and earlier failed camera images
remain held. This upload is not strict readback verification, a physical homing/
shutter remedy, camera acceptance or factory parity.
