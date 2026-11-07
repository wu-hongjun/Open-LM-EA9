# Aperture reporting

The lens ring controls the physical iris. LM-EA9 cannot sense or move it.
The app therefore keeps **actual aperture unknown**, independently of lens
specifications and camera-selected reporting.

| Fact | Biotar setup |
| --- | --- |
| Nominal lens specification | 58mm f/2 |
| Startup reported aperture | f/2 |
| Working 4.5 camera range | f/2–f/16 |
| Offline 4.6 camera range | f/1.2–f/22 |
| Physical aperture | Unknown; set on lens |

The selectable range is virtual. A reported f/1.2 does not make an f/2 lens
open to f/1.2. The owner separately matches the iris ring when desired.
Selections reset at boot/fresh session and are not persisted. USB inspection
identifies the compiled startup profile, not the prior live Sony selection.

Validated `0x1B` and normal `0x03` commands stage a latest aperture operand;
foreground publication updates replies/status coherently. Optional `0x28` and
`0x35` fields follow the camera's `0x08` capability bit. Fractional stop values
are preserved. The 4.6 endpoints use standard marked-stop encodings `0x1080`
and `0x1900`; the initial report stays `0x1200`.

The owner confirms aperture-dial operation and normal use on 4.5. Individual
saved exposure/EXIF measurements and exact camera settings were not supplied.
The wider 4.6 range needs its own camera check. Earlier investigations and
failed policies are retained in the [archive](history.md), not active guidance.
