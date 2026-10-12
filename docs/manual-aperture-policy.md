# Manual aperture reporting on LM-EA9

Research and owner feedback, October 11, 2026. The owner reports that original
stock 1.8 hunts much less than AF 2.3, but allows camera aperture changes without
physically stopping down the Contax Zeiss lens. They requested an unknown
aperture display. These observations are recorded in the
[stock comparison evidence](evidence/stock-18-comparison-2026-10-11.md).

The adapter cannot sense or operate a passive C/Y lens's iris. The desired
product behavior is manual aperture control on the lens, with the physical
working aperture shown as **unknown**, with any owner-supplied numeric camera report kept separate. Lens
maximum aperture, a manually supplied working aperture, and the values needed
by Sony's AF protocol are separate facts. A camera display of **F-- while AF
continues working has not been established** by the current references or our
A7C II tests.

## What stock and the current candidate actually do

The [official Techart manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf)
uses camera aperture selections to configure focal length, parking and focus
options, then tells the user to return the body to f/2 and set the working iris
on the lens. The exposed range is a configuration channel, not physical iris
control. This matches the recovered stock menu at `0x56cc`; see the
[compiled factory model](../research/stock-1.8/stock_model.c) and
[metadata-patch assessment](reverse-engineering/stock-metadata-patch-feasibility.md).

Our frozen AF 2.3 already removes the variable-range declaration:

- [`lens_profile.c`](../firmware/ea9/src/lens_profile.c) applies the **same saved
  reported aperture** to both range endpoints and the current-aperture fields.
  For the installed 50mm test profile this was AV `0x1100`, nominal f/1.4.
- [`emount.c`](../firmware/ea9/src/emount.c) answers `0x1b` with its own declared
  value instead of echoing a different requested iris position. It never drives
  an aperture mechanism. A7C II dial behavior with that fixed range was not
  explicitly recorded, so camera lockout remains a test result to collect.
- [`AdapterLensSetting`](../apps/macos/Sources/DeviceKit/LensImage.swift) uses
  `currentAperture ?? maximumAperture` to prepare the numeric report. A blank
  physical setting in the Mac library therefore **does not send unknown**; it
  assumes the maximum as the fixed camera-facing value.
- [`LensProfile`](../apps/macos/Sources/LensCore/LensLibrary.swift) already stores
  an optional owner-declared camera f-number (legacy `currentAperture` key). That value is owner-entered metadata,
  never a live reading. The live physical setting is unknown even if this field is filled; leaving it
  blank makes the numeric report default to the maximum aperture.

The constant report will be inaccurate if the owner stops down without updating
the saved value. It should always be presented as declared metadata. The body
cannot make the real iris match an electronic request.

## Why zero is not an established unknown encoding

The pinned
[upstream aperture specification](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/aperture_value.md)
documents current aperture in message `0x05` payload bytes 0–3 and a legacy
maximum/minimum descriptor at payload 44–59. Its author reports that zeroing
the legacy descriptor on LM-EA9 made an **a9 II show F1.0 and refuse AF**.
This is another owner's a9 II observation, not our own A7C II experiment. It
rules out treating an empty descriptor as a demonstrated safe solution; it
does not prove that every possible unknown encoding fails.

Nor does zero in message `0x28` establish unknown aperture. That optional field
is populated only when the body asks for it through message `0x08`; stock can
leave it zero while the photograph still has an aperture tag. See the pinned
[0x28 specification](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/msg_0x28.md).
It is a capability-dependent omission, not a lens-wide unknown switch.

Values such as `0xffff`, arbitrary capability-bit changes, or clearing the
entire aperture block have no verified unknown semantics in the collected
sources. The existing profile-v1 validators deliberately reject such values;
changing that validation would not prove how Sony interprets them.

## Recommended design and next evidence

Keep three distinct model concepts: lens specification, optional manually
supplied working aperture, and camera-facing reporting policy. The current
supported policy is a fixed declared aperture, with no variable iris range.
The desired future policy is unknown current aperture/EXIF while retaining
known lens geometry for AF, **if** the wire protocol and A7C II support it.
Do not silently map an unknown physical setting to a made-up unknown sentinel.

Before adding that second policy, obtain either a documented/captured AF-capable
device that reports F--, or a narrowly scoped experiment with a justified
encoding. Retain known maximum-aperture/optical geometry where required, vary
one field group at a time and record the body's aperture display, dial behavior,
AF-S acquisition, exposure, photograph EXIF and shutdown. Camera appearance
alone does not prove the EXIF omission or AF/metering correctness. Returning to
a verified image must remain available. No such experimental firmware was
built or uploaded in this investigation; the frozen 2.3 pins remain unchanged.

The owner's qualitative stock result also means that fixed metadata is not
enough to achieve factory AF behavior. Compare motion timing, completion,
position/reference and optical declarations against stock under matched
loaded-lens conditions before tuning gains or claiming parity. The current
candidate's optical rows are not calibrated for this actual Contax lens, and
changing the displayed aperture alone is not a demonstrated hunting fix.

## Implemented in app 0.7 / AF 2.4

Device always displays **Actual aperture: Unknown · set on lens**, including when
it has a USB-verified fixed f-number. Its numeric preview is labeled **camera
metadata: fixed f/...**. The library editor calls the optional override **Fixed
camera aperture** and explains that a blank value reports the maximum. Existing
libraries keep their `currentAperture` storage key and values; neither these
values nor USB readback become an actual-aperture measurement.

Firmware profile-v1 sets identical minimum/maximum/current camera AV values
and overrides body requests in `0x1b`. The later 2.5 audit found that 2.4 still
echoed requests in `0x34`, contradicting that fixed policy; 2.5 overrides both.
Stop down using the manual ring whenever needed;
changing metadata is optional and does not control the iris. If a photo must
carry the manually chosen f-number in EXIF, prepare that fixed numeric report
before shooting. The numeric report may also affect camera AF assumptions, so
stopped-down behavior remains part of camera qualification. No F-- sentinel or
unknown-camera-aperture firmware is introduced. The [factory-derived AF
baseline](reverse-engineering/factory-af-baseline.md) is a separate motion change.

## Stock exposure observation after AF 2.4 rollback

AF 2.4 later failed the owner's focus attempt, with a dark view and no shown
f-number in P/A; it remains suspended. Original stock 1.8 recovery passed normal
strict verification and an independent audit before camera use. The owner then
reported blown-out AUTO photos and selectable camera aperture in P, widest f/2.
See the [recovery and observation record](evidence/stock-18-af24-recovery-2026-10-11.md).

Stock's f/2 is the manufacturer's normal virtual camera setting. It does not
limit the physical iris or measure it. The original P/Auto comparison does not
hold that setting fixed and is unsuitable as a controlled stock exposure
baseline. Use A with the body at f/2 and set the actual working iris on the lens.
P/Auto may compensate for an electronic stop-down the passive lens never makes;
that is an inference for the owner report, not a proven cause without the shot
settings/original image. The next reply reports a correct preview but an
overexposed saved photo after selecting f/4.5; the owner subsequently confirmed
“Camera aperture only.” The physical iris
was unchanged during that adjustment, consistent with the unperformed electronic
stop-down explanation. Exact exposure adjustment and image clipping remain
unmeasured. Correct preview is not saved-photo qualification. The
stock body must stay at f/2 when the owner changes the physical ring. If the
body did stay at f/2, the unperformed electronic stop-down explanation alone
does not resolve that failure. A/body-f2 saved exposure and shutdown remain
unverified.

The owner subsequently reports a saved photo at physical f/1.4 and camera f/2
as one stop overexposed. The stock body-f2 check therefore failed under the
reported setup; it is not qualified by the manufacturer's recommendation.
Original image/shutter/ISO, mode, compensation, metering and shutdown remain
unverified. The displayed-versus-physical f-number difference has a roughly
one-stop arithmetic ratio, but the camera measures scene light through the
lens, so that ratio alone does not establish a one-stop metering fault.
The owner has confirmed that the original photo was not retained. Accept the
exposure failure from the owner report and continue firmware investigation;
the missing file is not a blocker. Original files/settings can support a later
diagnosis or quantitative comparison. The earlier camera-only f/4.5 change
remains a separate observation, consistent with an unperformed stop-down.

The custom design goal remains fixed accepted camera reporting, known lens
geometry and unknown physical iris in the app. Acceptance must include saved
exposure and EXIF in A/P/Auto and physical stop-down, alongside AF. The failed
2.4 display is not a demonstrated unknown-aperture mode. No new firmware or
USB operation was performed for this observation follow-up.

## Next firmware acceptance

The problem is accepted; the exact metering cause remains open. AF 2.4 already
writes a fixed range/current aperture and rejects conflicting `0x1b` requests, yet its
camera test had no shown f-number and failed focus. Repeating those setters or
subtracting one stop is not an established repair. Audit the complete lens-init
and aperture request/reply/status sequence against the factory reconstruction
and upstream traffic, separately from the actuator's fault/completion policy.

- Keep lens specification, declared camera aperture and unknown physical iris
  as distinct model values. The 50mm profile's declared nominal value is f/1.4;
  only the physical lens ring operates the iris.
- Make every known current/range/maximum aperture field coherent, including
  optional EXIF fields only when negotiated. A conflicting body request must
  not acknowledge that an unavailable physical stop-down occurred. Check the
  complete response/initialization sequence, not just serialized field values.
- On the A7C II, verify that the declared aperture appears and that the body
  accepts the fixed-range policy. Correct captured exposure must hold in A,
  P and Auto, including physical stop-down, without an invented one-stop bias.
  EXIF remains declared metadata rather than a sensor reading of the iris.
- Continue AF controller/completion work independently. Qualify startup,
  shutdown and AF-S separately from exposure. Pure-model equality, USB image
  verification and a correct preview are not substitutes for these outcomes.

An owner-reported failure is sufficient to fail a candidate. An original image
is useful diagnostic evidence, not a prerequisite for further development.
Quantitative exposure/EXIF or sharpness claims still require the corresponding
measurement. Hardware acceptance criteria are future checks, not claims that
the next implementation already passes. No new candidate is built or uploaded
by this documentation update.

The next pass is now implemented in [AF 2.5](evidence/af-25-candidate-2026-10-11.md):
coherent `0x34` aperture replies, consumed-snapshot negotiation and separately
classified motion terminations pass offline regressions. Physical exposure and
AF acceptance remain pending; no one-stop compensation was applied.
