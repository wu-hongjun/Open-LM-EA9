# Direct upstream 3.1 upload — October 14, 2026

**Upload and strict physical-reconnect verification passed; camera acceptance failed.**
The owner requested the direct upstream baseline after AF 3.0 focused on
half-press but froze on full press, saved no photograph and required battery
removal. The owner then confirmed the adapter returned to the computer.
The owner then confirmed physical reconnect. Native verification and a separate
offline audit passed. The later camera check failed: aperture `--`, blocked
shutter and no motor movement; normal shutdown is confirmed. Actual focus mode
and other settings remain unverified. Further trials are held.
See [the failure and offline investigation](upstream-31-camera-failure-2026-10-14.md).

## Exact image and upload

Release source: `11c2ad619a212de51b2a1e0cbf9f96d5597e99cb`, already pushed to
`origin/main`. Signed app 0.14.0/build 17 CLI matches its published validation
hash. Descriptor-only inventory found exactly one qualified adapter on a new,
unblocked connection. The previous AF 3.0 journal was verified and same-unit
stock-upload qualification was present. Native exclusive-access/updater/backup/
journal/reconnect guards were retained; no canonical state was manually changed.

Offline native `prepare-upstream` from the saved 50mm profile exactly matched
[the pinned candidate](../../firmware/candidates/3.1.0/README.md),
20,480 bytes at `[0x5000,0xa000)`, SHA-256 `528225e6f6472da0d92479da2b3e475a32f82735347231b6dc7c3d0dc7e8b39f`.
The whole image is fixed: there is **no runtime profile row**. Declared aperture
is nominal f/1.4; the actual iris is unknown and operated by the physical ring.
Upstream commit `d52ed06cc449918f938e0695fbf29a0c4141f2b2` supplies the unchanged
protocol, AF/servo, main loop, homing/park and peripheral driver C sources.
Build spelling/linker bounds, version/lens constants and pupil-row configuration
are the documented differences. This is a direct upstream comparison, not a
new factory-derived controller. See [provenance and limits](upstream-baseline-2026-10-14.md).

Command: `dist/ea9ctl apply-upstream contax-zeiss-50-f1-4 --idle` using canonical
state. The service saved a fresh, verified two-pass full-flash/auxiliary backup
and durable journal before START, then acknowledged one START and all 320
64-byte pages. It exited 0 at **2026-10-15T01:12:28.581251+00:00 UTC**
(**2026-10-14T21:12:28.581251-04:00 America/New_York**).
Transaction: `A87ABAD1-CC57-4982-AAB8-667A4E8E4B7B`. Counts follow successful native engine/
image evidence, not an independent wire capture. No post-START CHECK/READ,
end marker, retry or extra padding was sent on the armed connection. The
upload connection's guard remains retained. Boot code, protected gap, upper
flash and factory auxiliary data are not upload targets.

A separate offline audit checked backup files against their byte/hash manifest,
same-unit binding, exact planned/pending/committed image equality, upload
timestamp, fixed FF padding and retained guard. The backup reports firmware
**3.0.0**, 131,072 flash bytes, two matching
flash and auxiliary passes and 4,359 CHECK/READ exchanges. Its application
matches pinned AF 3.0; whole-flash equality with the last AF 3.0 readback is
**True**. Flash SHA-256:
`c003a458c60e8265b9f768dc1f65ea03f117c77ce97bd89ad10c782d6c3e8eef`. The boot-code hash remains the
qualified original. Raw backups, serials, calibration, canonical state and logs
remain private. Original stock recovery and older pinned images are unchanged.

## Completed reconnect verification

The owner replied **“reconnected.”** Descriptor-only inventory found one
qualified adapter on a new registry connection. Native `dist/ea9ctl verify --idle`
validated the new connection and the same unit before reports, completed a
matching two-pass flash/auxiliary readback, and exited 0 at
**2026-10-15T01:41:19.796694+00:00 UTC**
(**2026-10-14T21:41:19.796694-04:00 America/New_York**).
It reported firmware **3.1.0**, 131,072 flash bytes and 4,359 CHECK/READ
exchanges. This verification sent no writes or retries.

A separate offline audit checked every backup file against its size/hash
manifest and repeated all strict comparisons: exact 20,480-byte fixed image
including FF padding, exact 58 known metadata bytes, unchanged boot code,
protected gap, retained upper flash, user row, calibration and device-ID window.
There is no runtime profile row in this image. The six established loader
scratch bytes `[0x403a,0x4040)` remain the sole metadata exclusion. No check was
relaxed and no reconnect marker was manually changed.
Full readback SHA-256: `07f3dc251d953a128e0c0b10c6a4e172c5620a360be7507511a57f68c1c1ff4d`.

Canonical applied-lens and dated firmware-observation records now report
50mm f/1.4 / 3.1.0. The native service cleared the successful read connection's
marker and retained the original armed upload connection's marker. Raw backups,
logs and owner identifiers remain private. USB equality proves the installed
bytes; it does not qualify camera capture, exposure, focus or shutdown.

## Failed camera comparison

After strict verification, the owner was given [the camera procedure](../upstream-baseline-test.md):
first one loaded-lens MF capture/lifecycle cycle with still-photo A, Pre-AF Off,
EV 0, Auto ISO, focus ring infinity and physical iris f/1.4. Confirm actual MF
separately from the exposure dial. Record updating preview, expected f/1.4,
quiet ten-second idle, one saved photograph if normal and shutdown. Only after
that cycle succeeded would a bounded AF-S attempt have followed. The reported
cycle failed and the owner confirmed normal shutdown. No additional camera
trial, firmware upload or stock restoration followed the failure.

Neither the successful upload nor upstream's Sony a9 II results qualify A7C II
capture, focus, exposure or shutdown. AF 3.0 remains held. No stock restoration
is performed as part of this milestone.
