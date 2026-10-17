# AF 3.7 installation, one cycle and log retrieval

**No 3.7 upload or camera trial occurred during offline preparation.** The owner
requested flashing separately. Previously installed 3.6 remains held after capture freeze
and shutdown nonresponse; a new diagnostic image is not a demonstrated repair.

The separately authorized October 17 upload and strict byte verification have
passed after the owner-confirmed physical reconnect, followed by an independent
full-image/protected-data audit. The first owner camera cycle has been requested;
its results and log retrieval remain pending in the
[live installation record](evidence/upstream-37-upload-2026-10-17.md).

Before a future upload, confirm the adapter is physically on its USB cap, off
the camera, and the official updater/app are closed. Use the original verified
50mm f/1.4 profile and explicit `apply-trace-upstream` action. Preserve the fresh
backup/journal, then send no reports after upload until the owner physically
unplugs/reconnects and explicitly confirms it. Use the existing strict native
verification and independent offline byte audit of the complete application,
metadata and protected data. The log tail must still be pristine at this gate.
Version display alone is insufficient. Do not skip this gate to test a camera.

After verification, coordinate a single loaded-lens lifecycle cycle. With the
A7C II off and USB disconnected, mount the adapter, C/Y-to-M converter and
Contax Zeiss 50mm f/1.4. Set the physical focus ring to infinity and iris to f/1.4.
Separately select still-photo A, MF, Pre-AF Off, EV 0 and Auto ISO where available;
the exposure dial does not select MF. Record unavailable settings as unknown.
Switch on without shutter/AF-ON, confirm the live preview updates, note aperture
and brightness, and wait ten seconds after movement stops. Take at most one
photo only if MF and normal behavior are confirmed, then switch off once. AF-S
is a later gate; it is not part of this first diagnostic cycle.

For a freeze, grinding, repeated stop impacts or abnormal continuous drive for
about two seconds, stop. Switch off; remove the battery if unresponsive or motion
continues. Do not restart or repeat the failed operation. Record whether the
freeze was at half/full press, actual focus/exposure settings, whether a photo
saved, motor behavior and shutdown/battery-removal outcome without guessing.

Once unpowered and stopped, return the adapter to its cap and have the owner
explicitly confirm physical reconnect with the updater closed. Save a read-only,
two-pass native backup using the existing guarded action. Keep it private; the
decoder can include command operands and local identifiers. Decode offline:

```sh
python3 scripts/decode-startup-diagnostics.py /ABSOLUTE/PRIVATE/after-cycle.ea9backup --output /ABSOLUTE/PRIVATE/decoded.json
```

The decoder first verifies the pristine candidate/manifest/prefix pins and
native backup integrity, then recognizes v3 record cohorts. Structural CRC
validity, writer consistency and complete association are separate. A missing
snapshot/footer prevents trusting later markers as a complete shutdown chain;
its readable local bytes remain visible. Saturating sample counts and wrapping
timestamps are handled without inventing time order across wrap.

Read the fault-time motion snapshot, completion disposition, raw/ordinary
ownership and immutable TX identities, then the terminal prefix. A wrong-way
observation alone does not justify reversing motor polarity or removing guards.
TX RETURN proves a software send returned, not a shutter event or camera
acceptance. PA23/delay markers do not prove body power-off. Missing logs can
result from lost RAM, exhausted capacity or interrupted programming.

Publish only a sanitized evidence record, then commit/push it. Review the record
before authorizing another camera trial or a separately versioned control fix.
