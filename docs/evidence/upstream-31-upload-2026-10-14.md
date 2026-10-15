# Direct upstream 3.1 upload — October 14, 2026

**Upload complete; physical reconnect and strict byte verification pending.**
The owner requested the direct upstream baseline after AF 3.0 focused on
half-press but froze on full press, saved no photograph and required battery
removal. The owner then confirmed the adapter returned to the computer.
Keep it on the USB cap and off the camera until strict verification succeeds.

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

## Pending verification and camera comparison

Physically unplug and reconnect the cap, keep TECHART Update closed and leave
the adapter off the camera. After owner confirmation, `dist/ea9ctl verify --idle`
requires a different registry connection and the same unit before reports. Its
fresh two-pass readback must match the complete fixed image and known metadata,
with unchanged boot code, protected gap, retained upper flash and factory
auxiliary data. The established six-byte loader scratch range
`[0x403a,0x4040)` is the sole metadata exclusion. A separate offline audit follows.
No guard deletion or relaxed comparison is part of this procedure.

After strict verification, use [the camera procedure](../upstream-baseline-test.md):
first one loaded-lens MF capture/lifecycle cycle with still-photo A, Pre-AF Off,
EV 0, Auto ISO, focus ring infinity and physical iris f/1.4. Confirm actual MF
separately from the exposure dial. Record updating preview, expected f/1.4,
quiet ten-second idle, one saved photograph if normal and shutdown. Only after
that cycle succeeds request one bounded AF-S attempt. Stop on freeze or abnormal
drive; remove the battery if unresponsive or motion continues, and do not retry.

Neither the successful upload nor upstream's Sony a9 II results qualify A7C II
capture, focus, exposure or shutdown. AF 3.0 remains held. No stock restoration
is performed as part of this milestone.
