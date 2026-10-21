# AF 4.0 upload — October 20, 2026

**AF 4.0 passed strict USB byte verification after physical reconnect. Camera
acceptance subsequently failed; further 4.0 trials are held.** The owner reports a
hard crash after two photos requiring a power cycle. Actual focus mode, saved-file
status and recovery details are unknown; read-only logs await safe cap confirmation.
[Camera failure record](upstream-40-camera-failure-2026-10-21.md).


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

## Physical reconnect and strict verification

The owner explicitly confirmed physical USB-cap reconnect with both apps closed
and the adapter off-camera. Preflight rechecked signed CLI/image/manifest pins,
the unchanged uploaded journal, absence of competing processes and one qualified
adapter on a new, unblocked connection. Inventory sent no reports.

`dist/ea9ctl verify --idle` ran once, exiting 0 at **2026-10-21T02:36:18.725905+00:00 UTC**
(**2026-10-20T22:36:18.725905-04:00 America/New_York**). Two matching 131,072-byte flash
passes and two auxiliary passes completed, totaling 4,359 CHECK/READ exchanges.
No firmware writes or retries were sent. Independent filesystem checks confirmed:

- Every backup file size/digest, known boot code, MCU/geometry, new connection
  and same qualified unit, with reported firmware/version metadata 4.0.0.
- All 20,480 application bytes `[0x5000,0xa000)` exactly match the pinned image,
  including all 1,024 blank diagnostic bytes; this is full-image verification.
- Expected metadata `[0x4000,0x403a)` and unchanged boot, gap `[0x4040,0x5000)`,
  upper flash `[0xa000,0x20000)`, user row, calibration and device-ID windows.
  Only loader scratch `[0x403a,0x4040)` is excluded; NVM status is checked for
  geometry rather than volatile-status byte identity.
- Native publication of the verified journal, original 50mm f/1.4 setting and
  firmware observation. Old blocked-connection membership, stock qualification
  and library bytes are preserved. The successful read marker clears through
  the native engine; no canonical state or safety marker was manually edited.

Readback full-flash SHA256:
`46c4d45590e03f9deb6bc325aaec531cef6511ee4a443a2b91e157cfcc815248`.
The complete pristine application remains identical to the reviewed 4.0 release.
All 146 historical artifacts, older registry entries and original stock 1.8 recovery
remain exact. Raw backups, keys, unit identifiers and real frames stay private.

## One initial camera cycle, then read-only logs

The owner is guided through one loaded-lens cycle after strict verification:
with the A7C II OFF and USB cable disconnected, mount the adapter, C/Y-to-M converter
and 50mm f/1.4, physical infinity/f/1.4. Switch on once without shutter/AF-ON input;
check normal live preview/motor behavior. Then confirm **MF separately from A
exposure mode** and Pre-AF Off in powered-on menus, with EV 0/Auto ISO where available.
After movement stops, wait 10 quiet seconds. Take at most one photo only when MF
and normal preview/aperture/motor behavior are confirmed; otherwise skip it.
Shut down once and leave it off; no restart or AF-S attempt is requested yet.

For freeze, grinding, repeated stop impacts or abnormal drive for about 2 seconds,
stop, switch off, remove the battery if unresponsive or motion continues, and do
not retry. After camera power-off/unpower and stopped motor, return the adapter
to its USB cap and explicitly confirm physical reconnect with both apps closed.
Only then retrieve one guarded read-only backup and decode/audit saved files.
Actual settings, preview, motor, saved-file exposure and shutdown remain unknown
until reported. A later logged read is diagnostic evidence, not pristine full-image
verification. This remains unqualified for sustained capture/AF and factory parity.

## Subsequent October 21 report

The owner reports a hard crash after two photos and needing a power cycle. Two
saved files, actual MF/AF/Pre-AF, exposure/preview, motor and recovery method remain
unverified. The requested single MF cycle is not recorded as confirmed. No new
camera attempt or flash is requested. App 0.23.1/build 32 holds 4.0 and disables its
ordinary installation; exact firmware/native command pins and recovery remain.
Post-camera logs await explicit safe USB-cap reconnect with both apps closed.
This record retains the successful strict USB readback separately from the failed
camera milestone; no physical fault mechanism is inferred from the report alone.
