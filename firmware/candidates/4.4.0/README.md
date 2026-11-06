# Upstream 750 kbaud comparison 4.4.0

This candidate isolates the speed change in the [November upstream 4.2.0
trial](../4.2.0/README.md) of [commit e054db9](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9/commit/e054db90cfae5d67fac67a7e0db4bb100f5893ae).
The original answers the body's `0x0C` offer with `01`, waits for the
switching pulse and reconfigures the UART to 1.5 Mbaud. The comparison
answers `00` and stays at 750 kbaud. It preserves upstream's identity
`0xC540`, advertised speed, startup and receive admission, nominal
50 mm f/1.8 optics, and motor/AF implementation. USB 4.4.0 identifies this
image separately. The build is motor-enabled.

- [Image](upstream-stock-speed.bin) is 20,480 bytes in `[0x5000,0xa000)`.
- [Manifest](manifest.json) pins the image, original 4.2.0 digest and build inputs.
- [Firmware patch](stock-speed.patch) changes only the `0x0C` behavior in
  `src/emount.c`. [Host expectation patch](hosttest.patch) adjusts the
  upstream suite's original baud-switch assertions for this experiment.

The [A7C II trace](../../../docs/evidence/startup-probe-43-2026-11-06.md)
showed that a separate stock-identity probe reached normal traffic at
750 kbaud. That probe changed several variables and did not establish which
difference mattered. This build controls the code difference against 4.2.0.
The 4.2.0 trial failed on the owner's A7C II. With 4.4.0 the owner
reported f/1.8 display and working autofocus in both still-photo and
video modes. A matched repeat of the control and a wire trace are
still missing. [Camera result](../../../docs/evidence/upstream-stock-speed-44-2026-11-06.md).

## Offline checks

A clean control build reproduced the released 4.2.0 image and manifest.
Two independent comparison builds matched. The two linked images use the
same compiler settings. The fixed-speed image has no linked UART speed
setter. The original upstream host test rejected the expected four baud
and pulse differences. With those expectations adjusted, the upstream
suite passed.

The [synthetic replay](../../upstream-hardening/followup/59-stock-speed/run.py)
runs the exact linked-in C protocol sources through the upstream host shim
under ASan/UBSan. With a valid pulse, a missing rise, or a missing fall,
12 of the 13 output frames were byte-identical. Only the `0x0C` payload and
its checksum differed. The control selected 1.5 Mbaud in all three cases.
The comparison stayed at 750 kbaud and made no speed-switch CS reads.
Both images still reproduced the buffered-opener loss and header-only
readiness behavior. The synthetic UART and pins supply no body acceptance
or electrical timing evidence.

```sh
python3 scripts/build-upstream-november-trial.py --checkout CHECKOUT --output artifacts/private/ea9-speed-a
python3 scripts/build-upstream-november-trial.py --checkout CHECKOUT --output artifacts/private/ea9-speed-b --stock-speed
python3 firmware/upstream-hardening/followup/59-stock-speed/run.py \
  --control artifacts/private/ea9-speed-a --candidate artifacts/private/ea9-speed-b \
  --output artifacts/private/ea9-speed-replay
scripts/swift-local.sh test
```

## Camera comparison

The source-built `ea9ctl apply-upstream-stock-speed --idle` uses the
existing qualification, pre-upload two-pass backup and durable update
journal. It accepts known stock 1.8.0, the exact 4.2.0 control, or the pinned
immutable 4.3.0 probe prefix. With 4.3.0, the complete backup preserves its
diagnostic tail before the application write. Keep the original same-unit
[stock recovery](../../recovery/stock-1.8.0/README.md) available.

After an authorized upload, physically reconnect and run `ea9ctl verify
--idle` before camera use. On the A7C II, first compare one startup and
shutdown cycle with shutter and AF-ON untouched. Record actual body
firmware and camera settings if known, live view, aperture display (the
compiled nominal value is f/1.8), any movement, and shutdown. Stop after
a freeze, grinding, repeated impacts, or sustained drive. Use the power
switch and remove the battery if the camera is unresponsive.

The result supports investigating the speed negotiation path. The
upstream startup transport is retained, including the earlier buffered
opener and readiness findings. This candidate records no persistent
startup trace. Capture, recording, exposure and shutdown are separate
checks.
