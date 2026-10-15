# Upstream 3.1 camera failure — October 14, 2026

**Camera acceptance failed; further 3.1 trials are held.** The owner reports
that the shutter does not activate, the focus motor is not moving and the
aperture display shows `--`. A follow-up confirms **normal camera shutdown**.
This is a different reported failure from AF 3.0's full-press freeze requiring
battery removal. Do not repeat either failed image to obtain missing settings.

The [complete pinned 3.1 image and protected regions passed strict USB
verification and an offline second audit](upstream-31-upload-2026-10-14.md).
That result remains valid evidence of the installed bytes. The failed camera
result is recorded separately in [structured evidence](upstream-31-camera-failure-2026-10-14.json).
No USB report, new flash, stock restoration or firmware change followed this
failure report. The adapter's current location was not confirmed.

## Observations and limits

The requested check was loaded-lens A / MF / Pre-AF Off, infinity and physical
f/1.4, followed by one photo only if preview and motor behavior were normal and
MF confirmed. The actual focus mode, Pre-AF, physical iris/focus ring, exposure
mode, preview behavior and saved-photo result remain unverified. Do not relabel
this as a controlled AF-S or MF test. Motor silence is expected in some MF
states and alone does not prove an AF fault.

`--` establishes missing displayed aperture; it does not locate the fault in
the adapter's boot, handshake or aperture field. A shutter that will not release
can have more than one cause. Normal shutdown does not prove the adapter sent
its protocol acknowledgement or parked; the camera can stop without a working
lens exchange. No camera bus capture or runtime fault record is available.
The release firmware deliberately disables persistent diagnostic writes.

The [upstream README](https://github.com/weiziqian/E-mount-impl-on-Techart-EA9#12-test-platform)
documents Sony a9 II testing, not A7C II qualification. This comparison shows
that using the upstream implementation directly has not resolved this owner's
camera compatibility. It neither exonerates our previous AF implementation nor
proves a single shared cause across these different failures.

## Bounded offline startup/aperture investigation

The new [five-case probe](upstream-31-startup-probe-2026-10-14.json) compiles
checksum-checked 3.1 `emount.c`, packet tables, configured header and the upstream
host shim using `-O2 -DNDEBUG -DEA9_NO_LOG`, AddressSanitizer and
UndefinedBehaviorSanitizer. It supplies checksum-valid synthetic init requests;
every case passes without a sanitizer diagnostic. No production source or
firmware artifact is modified.

| Supplied state | Handshake flag | Status frames after VD | Aperture in 0x05 | Optional aperture in 0x28 |
| --- | --- | --- | --- | --- |
| Initialized, no requests | false | 0 | 4352 (nominal f/1.4) | 0 |
| Seven init IDs, 0x08 requests field | false | 0 | 4352 | 4352 |
| Seven init IDs, 0x08 omits field | false | 0 | 4352 | 0 |
| Eight init IDs through 0x0a, field requested | true | 2 | 4352 | 4352 |
| Eight init IDs through 0x0a, field omitted | true | 2 | 4352 | 0 |

The actual main loop runs encoder/ADC/motor initialization before `em_init`,
then reads the encoder reference before entering `em_poll`. Several peripheral
and first chip-select waits are unbounded in this upstream baseline. Answering
queued init ID `0x0a` sets `em_handshake_done`; that flag gates periodic status
and the main loop's homing entry. These are concrete places to instrument,
not recovered execution states from this camera.

Message `0x08` frame byte 7, bit 7, controls only the optional `0x28` aperture
copy: set means omit it. The fixed `0x05` aperture remains 4352 in every probe
case. Therefore forcing `0x28` nonzero is not justified by `--` alone. Lens ID
50496 is upstream's retained experimental value; the prior fork used 234.
Neither value's effect on this A7C II handshake has been measured.

The probe does not execute real startup, main, motor, sensor, MCU interrupts or
electrical UART timing. It does not prove that the observed boot failed to
complete its handshake or establish why the shutter was blocked. Reproduce it
after materializing the pinned upstream build:

```sh
python3 scripts/investigate-upstream31-startup.py --output /new/startup-check
```

The output directory must be new under an existing parent. It accesses only
public pinned source/build provenance and the committed candidate; no USB,
private backup, owner identifier or canonical state is accessed.

## Follow-up boundary

Resolve startup, first CS/UART window, lens identification and handshake/status
ownership before changing AF gains. Compare those paths with the original
factory instructions. A later diagnostic build should distinguish entry to
main, peripheral readiness, first CS, parsed request IDs, transmitted replies
and handshake completion. Its storage boundaries, write budget and recovery
behavior require review before any separately coordinated diagnostic upload.
Do not re-enable the old flash logger wholesale, force motor movement, relax
readiness or change camera release settings to conceal this failure.

App 0.14.1/build 18 marks installed 3.1 as held, retains the verified USB history
and disables the ordinary baseline installation action. Firmware bytes and the
explicit native recovery paths remain preserved. No replacement candidate is
claimed by this investigation.

Validation: all 53 Swift tests pass (7 LensCore, 35 DeviceKit, 11 app workflow),
including the verified 3.1 failure hold after local history refresh and lens
dropdown changes. Signed app/CLI packaging passed. The five sanitized startup
cases pass and the firmware image pin remains unchanged. See
[the validation record](upstream-31-failure-validation-2026-10-14.json).
