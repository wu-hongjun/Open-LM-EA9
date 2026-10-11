# Manual aperture reporting on LM-EA9

Research and owner feedback, October 11, 2026. The owner reports that original
stock 1.8 hunts much less than AF 2.3, but allows camera aperture changes without
physically stopping down the Contax Zeiss lens. They requested an unknown
aperture display. These observations are recorded in the
[stock comparison evidence](evidence/stock-18-comparison-2026-10-11.md).

The adapter cannot sense or operate a passive C/Y lens's iris. The desired
product behavior is manual aperture control on the lens, with the physical
working aperture shown as **unknown unless supplied by the owner**. Lens
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
  the physical ring setting as optional. That value is owner-entered metadata,
  never a live reading. Leaving it blank preserves physical uncertainty in the
  library, while the current firmware still needs its numeric declaration.

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
