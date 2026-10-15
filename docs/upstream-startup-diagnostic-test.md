# Upstream 3.2 installation and one-cycle diagnostic procedure

**October 15: upload complete; physical reconnect and strict byte verification
pending.** See [the current installation record](evidence/upstream-32-upload-2026-10-15.md).
The earlier offline preparation used no USB. The last verified image remains
3.1 until 3.2 verification succeeds; its camera result failed. Do not repeat 3.1.
See the [3.2 candidate](../firmware/candidates/3.2.0/README.md) and
[design/evidence](evidence/upstream-32-startup-diagnostic-2026-10-15.md).

## Installation and required reconnect verification

After an explicit upload request and confirmation that the adapter is on its
USB cap with TECHART Update closed, use app 0.15/build 19's separate **USB tools
→ Install Startup Diagnostic 3.2.0** action with the original 50mm f/1.4 profile.
The explicit native CLI equivalent is:

```sh
dist/ea9ctl apply-startup contax-zeiss-50-f1-4 --idle
# Owner physically unplugs and reconnects the USB cap; keep off the camera.
dist/ea9ctl verify --idle
```

Upload retains the same-unit qualification, exclusive access, fresh two-pass
backup, durable journal, exact acknowledgements and physical reconnect guard.
No CHECK/READ/end marker/retry follows START on the armed connection. Require
owner-confirmed physical reconnect before strict verification. The **complete
20,480-byte image, including every blank diagnostic page**, must match; protected
flash, known loader metadata and auxiliary data must pass the existing checks.
The six established loader scratch bytes are the sole metadata exclusion.
Repeat an offline evidence audit before any camera use. Diagnostics do not
relax that installation verification.

## One initial camera cycle, after verification

Keep the camera off while mounting the adapter, C/Y-to-M converter and Contax
Zeiss 50mm f/1.4; disconnect the camera's USB cable. Set the physical lens ring
to infinity and iris to f/1.4. Use still-photo A mode, EV 0, Auto ISO, **MF selected
separately in Focus → AF/MF → Focus Mode**, and Pre-AF Off where available.
Record actual settings; leave missing settings unverified.

1. Switch on without shutter/AF-ON input. Note preview updating/brightness,
   displayed aperture (expected f/1.4), motor behavior and whether it stops.
2. If quiet and responsive, wait ten seconds after any movement stops. This
   gives the bounded incomplete-handshake paths an opportunity to retain a log.
   If the aperture remains `--`, skip the photograph and AF; switch off once.
3. If preview/aperture/motor behavior are normal and MF is confirmed, take one
   photograph, then switch off once. Otherwise skip it. Leave the camera off.

Stop on freeze, shutdown nonresponse, grinding, repeated stop impacts or abnormal
continuous drive for about two seconds: switch off, remove the battery if
unresponsive or motion continues, and do not retry. No extra attempt is required
to recover missing settings. **Do not try AF-S or restart before retrieving and
reviewing this cycle's log.** Upstream homing/parking still can move the mount;
motor silence alone is not an AF acceptance result.

## Read-only log retrieval

With the camera off/unpowered and motor stopped, move the adapter back to its
USB cap and physically reconnect it to the Mac, updater closed. After confirming
that physical state, save a new native two-pass backup. This is a read operation,
not another upload or log reset:

```sh
dist/ea9ctl backup /new/after-startup.ea9backup --idle
python3 scripts/decode-startup-diagnostics.py /new/after-startup.ea9backup --output /new/startup-result.json
```

Use new writable paths. The native backup checks the same qualified loader and
retains full flash/auxiliary evidence. The offline decoder checks the flash
manifest, version and immutable `[0x5000,0x9c00)` prefix against the pinned 3.2
candidate, then validates each log page's header/slot/CRC. Invalid/torn pages,
full storage, missing records and dropped events remain explicit. It never
opens a USB device. Raw backups and real camera exchange records remain private;
publish sanitized conclusions and hashes only.

Camera use can change `[0x9c00,0xa000)` as designed. Post-camera log retrieval is
**not** a repeat of installation verification. Use `backup` and the decoder;
ordinary `inspect` deliberately retains full-image matching and will reject a
modified diagnostic image rather than pretending its bytes are pristine. The
last exact installation record stays historical. A subsequent upload first
saves a fresh backup including the logs. No runtime erase, log-clear command or
automatic restoration is provided.

## Evidence needed before the next candidate

Match the owner observations with the last recorded stage, RX/TX IDs/sequences,
UART status, first-window-preservation event, handshake flag and any guard fault.
The handshake flag is the firmware's state, not proof that the camera accepted
the lens. Millisecond ticks do not measure electrical reply timing. A blank log
does not prove the application failed to start; early power loss or an unguarded
CPU/bus failure can prevent persistence. Compare the entire pre/post-camera flash
and factory auxiliary data separately to establish that writes stayed within
the declared diagnostic area. Do not infer a physical fix from software tests
or adjust aperture fields/AF gains without evidence from this cycle.
