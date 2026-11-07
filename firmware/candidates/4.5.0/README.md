# Biotar 58mm camera-dial aperture trial 4.5.0

Prepared offline at the owner's request to select the reported f-number with
the Sony camera dial. The attached lens is now confirmed as a Zeiss Jena Biotar
58mm f/2. This candidate builds on the working [4.4.0 comparison](../4.4.0/README.md),
keeping its native lens ID `0xC540`, 750 kbaud operation and upstream motor,
servo and capture/shutdown code. Camera qualification is pending.

The boot profile is **58mm, f/2**, with a **reported range f/2–f/16**. The upper
f-number is an initial product choice, not a measurement of this particular
lens's engraved scale. The camera commands a reported aperture; the owner
must separately turn the physical iris ring. The firmware cannot sense or
move the iris. Selection is volatile and resets to f/2 at boot or a valid
fresh session opener. It adds no persistent settings or diagnostic writes.

- [Application image](biotar-camera-aperture.bin): 20,480 bytes in `[0x5000,0xa000)`.
- SHA-256: `8fba0303581fd684ae279a73aab7be136508f5d90b6fc975c5e4406a210c9f35`.
- [Manifest](manifest.json) pins all generated source files and the builder.
- [Patch against 4.4](from-44.patch), plus the new [reporting module](../../camera-aperture/).
- Linked code/data end: `0x9dd4` (19,924 bytes); 300 bytes before the `0x9f00`
  build guard. The image has no linked baud setter or persistent diagnostic code.

## Protocol design

The dedicated module accepts the first aperture word of init-class `0x1B`
and payload bytes 5–6 of normal-class `0x03`. Each input requires a valid
start, little-endian declared length, operand bounds, additive checksum,
terminator and message class. Window padding is excluded from the operand
and checksum. Values outside `[0x1200,0x1800]` are ignored. The full fractional
byte is retained, including thirds of a stop.

The receive callback stages a single latest value. Foreground `em_poll`
commits it before transmission, preserving the interrupt mask and updating
both `0x05` current-aperture words, both `0x1B` reply words, and the optional
`0x28`/`0x35` words coherently. The latter still follow the body's existing
`0x08` capability bit. This avoids updating serialized buffers during a UART
send. After shutdown acknowledgement, new aperture offers are ignored until
a fresh opener. These checks cover the added aperture path; the broader
upstream parser and readiness limitations are inherited.

The declared range in `0x08` and legacy aperture descriptors in `0x05` derive
from the same constants. The reported lens name changes to the Biotar; the
existing library ID `zeiss-jena-biotar-55-f2` is retained for saved-library
compatibility despite its legacy spelling. Native USB inspection identifies
the compiled startup f/2 setting, not a live reading of either the Sony dial
or the physical iris. App 0.25.0/build 36 labels this explicitly.

The command locations follow the archived upstream specifications for
[aperture values](../../../references/upstream/weiziqian/E-mount-protocol-RE/docs/aperture_value.md),
[`0x03`](../../../references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x03.md),
[`0x1B`](../../../references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x1B.md)
and [`0x28`](../../../references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x28.md).
Those captures describe other bodies and lenses; they do not establish the
A7C II's live dial behavior. No unknown-aperture sentinel is introduced.

The upstream optical tables and optical-file contents remain unchanged and
are not Biotar calibration. Some inherited source prose describes an f/1.8
optical row, while the pinned `EM_SLOT_B_TYPE1` is actually all zero. No
invented rescaling or claimed optical calibration accompanies this metadata
change. AF quality at 58mm and stopped-down exposure require camera checks.

## Offline verification

Two independent clean builds match byte-for-byte, including their manifests.
ASan/UBSan tests execute the actual generated protocol sources with synthetic
UART, CS and time. They cover boot metadata; `0x1B` and `0x03`; both optional
aperture-field settings; fractional values; all 65,536 possible unsigned
operands; invalid class/checksum/length/terminator; padded windows; a request
injected during transmission; interrupt-mask preservation; and shutdown/new
session handling. Removing the real receive hook and publishing directly
from the receive callback each fail the specific expected assertion.

The broad upstream protocol suite passes with only the expected focal/range
literals updated. Servo simulation, focus mapping, focus distance, buffered
startup rescue, and no-body/slow-body waits pass. The inherited no-body test
initially failed because it expected a persistent tally; the release builds
compile that tally out. Its adapted expectation requires no tally and retains
the actual wait and frame-sync assertions. This is a fixture adjustment, not
a repaired startup behavior.

All 58 Swift tests pass, including parameterized upload/verification/journal
tests for this image, exact-source admission and rollback rejection controls,
and startup-versus-live app labels. The native prepare-only command emits the
exact firmware bytes. The release app/CLI are packaged and signature-verified
locally. [Offline result](offline-evidence.json) records scope and digests.
No USB access or canonical application-state changes occurred in preparation.

Reproduce from a checkout containing pinned upstream commit
`e054db90cfae5d67fac67a7e0db4bb100f5893ae` with the toolchain dependencies
described in the [4.2 build](../4.2.0/README.md):

```sh
python3 scripts/build-upstream-november-trial.py --checkout CHECKOUT \
  --stock-speed --output artifacts/private/aperture-base
python3 scripts/build-camera-aperture.py --base-build artifacts/private/aperture-base \
  --output artifacts/private/aperture-build
python3 scripts/test-camera-aperture.py --build artifacts/private/aperture-build \
  --output artifacts/private/aperture-test
scripts/swift-local.sh test
scripts/build-macos-app.sh
dist/ea9ctl prepare-camera-aperture artifacts/private/biotar-prepared.bin
```

## Separate installation and camera qualification

The explicit `ea9ctl apply-camera-aperture --idle` path requires the unit's
existing stock-upload qualification and a fresh two-pass backup matching the
exact installed 4.4.0 application. Existing shared lock, updater exclusion,
durable journal, bounded upload and reconnect guards apply. The ordinary
profile API also enforces this source check for 4.5.0. After the final upload
page, physically reconnect before `ea9ctl verify --idle`; match the complete
application and protected data before camera use.

For rollback, `ea9ctl apply-upstream-stock-speed --idle` also accepts the exact
4.5.0 image, then requires another physical reconnect and full verification.
Modified images fail admission. Original same-unit
[stock recovery](../../recovery/stock-1.8.0/README.md) and all earlier pins remain
preserved.

For the first coordinated trial, start once without shutter/AF-ON input and
check responsive live view, f/2 and quiet idle. In A or M exposure mode, confirm
MF and Pre-AF Off before a single capture. First try a camera-dial change to
f/4 with the lens ring matched to f/4; record whether the display accepts it.
Record the actual settings, saved-file aperture/exposure and shutdown. Changing
both virtual aperture and transmitted light can affect metering assumptions;
matching the ring is not proof of correct exposure. Compare under fixed
lighting/ISO before broader AF-S/video trials. P/Auto may command the report
too; the firmware cannot distinguish a user dial change from an automatic
camera request. The camera never acquires physical iris control.

End the cycle for frozen preview, unresponsive capture/shutdown, grinding,
repeated stop impacts or abnormal sustained drive. Switch off; remove the
battery if unresponsive or movement continues. Return to the USB cap for
read-only inspection rather than repeating a failed camera trial. This build
retains 4.4's lack of persistent runtime traces. Camera stability, exposure,
EXIF and factory parity are not established by the offline tests.
