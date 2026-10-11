# Offline factory metadata patch feasibility: 50mm f/1.4

**Verdict: not ready for a firmware patch.** The expected-byte manifest is private and non-flashable; no replacement bytes or image were emitted. Keeping factory control code intact is plausible, but changing a few apparent metadata constants is insufficient to establish stock-preserving behavior.

This assessment is tied to official app SHA-256 `f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564`. The per-unit record is a separate original full-flash input. Expected original bytes and that record's values are retained only in `references/private/rea-analysis/phase2/patch-expectations.private.json`.

| Dependency | Verified location/path | Requirement before an edit |
|---|---|---|
| Saved focal length | Flash `0x4126`, loaded by `0x8ae4` to RAM `0x20000680` | App-only image does not contain this record. Preserve unit reference and all other fields; decide whether to use existing user focal menu or an explicit boot override. Never substitute another unit's record. |
| Runtime focal menu | `0x56cc`, dirty flag set by `0x5510` | Camera aperture-coded settings can replace active focal length and persist it. Define fixed-versus-selectable policy; suppressing it changes behavior. |
| Initial/live focal fields | Status05 flash `0x9b9a..0x9b9d`; response28 `0x9d42..0x9d45` | `0x5d2c` overwrites both with active focal×10, only when flag `0x527` is set. Establish initial handshake and subsequent status consistency. |
| Focal-dependent focus report | `0x567c`, RAM `0x20000013` | 50mm selects8; thresholds are16/24/35/50/70mm. Selecting focal length affects reported focus characteristics, not only EXIF text. |
| Boot current aperture | Conversion immediate `0x8a8e`, function `0x66b8`; status05 offsets6..9 | Descriptor `0x10` maps arithmetically to `0x1100`; optical interpretation as the quantized f/1.4 class needs camera confirmation. Static packet edits are overwritten at boot. |
| Boot descriptor and derived offsets | Immediate `0x8aa6`, status05 offsets`0x32`,`0x39` and following stores | **Do not simply change this immediate.** Register r2 is subsequently incremented by`0x22` at`0x8ab2` and used as the store index at`0x8ab4`; it is then decremented and reused for status06 offsets. A value-only edit redirects writes. A reviewed instruction-level rewrite must preserve index/data dependencies. |
| Stored wide-aperture field | Status05 offset`0x34`, flash `0x9bb0` | Not one of the two boot descriptor stores; must agree with intended max-wide/max-tele semantics. |
| Minimum/current aperture policy | Boot path above, camera echo response1b | The adapter cannot sense a manual aperture ring. Distinguish lens maximum specification, assumed shooting aperture and camera menu control. Echo handlers overwrite static response bytes and have focal/options side effects. |
| Textual identity | Response3f candidate name field starts flash `0x9c0f` | Capacity/encoding and exact field semantics need camera confirmation. A string does not prove lens identification or EXIF acceptance. |
| Numeric identity | Response07 candidate ID at flash `0x9a47` | Do not invent or reuse a proprietary lens ID without establishing camera interpretation. Independent from display text. |
| Optical tables | Copied response/status tables, especially05/08/28 | Pupil, focus distance, aperture geometry and scaling are not calibrated for the actual 50mm lens. No evidence that preserving donor tables preserves AF accuracy. |
| Frame checksum | Send routine `0x51d4` | Recomputed at send time, including dynamic fields; static checksum changes are not a complete validation. |

The menu's 50mm selection is high byte`0x16`, low byte`0x00`; adjacent choices select60/75mm. Other high-byte ranges select12..800mm. High byte`0x1b` controls park and an unresolved option. This is a recovered protocol encoding, not an instruction to issue camera or USB commands during this offline phase.

A future patch proposal needs one explicit metadata policy, a complete write/overwrite map, expected-original checks for every changed site, differential tests proving unchanged address calculations and unrelated packet fields, and camera/optical evidence appropriate to the lens. Binary acceptance, image-level checksums and updater/package integrity also require verification before any deliverable could be described as flashable.

Excluded now: bootloader, vectors, PWM/coil routines, encoder arithmetic, PID, protocol timing, per-unit reference, NVM policy, USB identity and updater state. Even edits outside these regions can alter AF indirectly through focal/optical reporting; “same code” is not sufficient to prove “same behavior.”

Rollback would require the exact original app plus this unit's preserved settings and a separately authorized, validated restore procedure. Those inputs exist privately, but no rollback operation or live restore test was performed. The current safest deliverable is this dependency dossier and expected-byte manifest, not a patched image.
