# Aperture protocol audit and proposed design

Independent audit, October 11, 2026. Reviewed the pinned upstream protocol and
firmware snapshots, the original 1.8 reconstruction, AF 2.5 source and its offline
evidence. This audit changes no firmware, binaries or hardware. Source locations
refer to repository HEAD `7efac6b` unless stated otherwise.

## Recommendation

Use a **fixed camera-facing aperture with manual physical stop-down** as the
first supported product policy. For this profile, declare nominal f/1.4 and
expose no electronic aperture range. The physical iris remains unknown to the
adapter and is operated only by the Contax lens ring. The app should require
selecting the lens once, not editing metadata every time the owner stops down.
This is a design to qualify on the A7C II, not an already verified metering mode.

Retain the original factory behavior of protocol fields whose meaning has not
been established. In particular, **do not classify message `0x34` as an aperture
channel solely because its handler echoes a word also copied by `0x1b`**.
That inference made AF 2.5's policy broader than the evidence supports.
Prepare a separately versioned follow-up that removes the unsupported `0x34`
aperture override, preserves the frozen 2.5 image, and keeps the new AF wrapper
fixes. The known aperture sinks remain fixed and consistent.

**Readiness amendment:** AF 2.5 is not recommended for the next hardware
aperture/exposure comparison while this `0x34` override lacks established
semantics. Its passing regression demonstrates the implementation's chosen
policy, not the camera's acceptance or the field's meaning. There is no evidence
that the override caused damage, but no need to introduce that uncontrolled
variable into a metering experiment.

An unknown camera f-number (`F--`) would be an attractive eventual interface,
but the collection contains no demonstrated AF-capable encoding for that mode.
Do not send zero, `0xffff`, or erase legacy descriptors to simulate it. The app
can correctly display **Actual aperture: Unknown — set on lens** today.

## What the evidence establishes

`pl[n]` below means payload byte `n`; absolute frame offset is `n + 6`.
Confidence distinguishes original-instruction data dependency, source-author
hardware observations, and a proposed policy. A source's “CERTAIN” label is not
a measurement repeated on this owner's A7C II.

| Field or behavior | Evidence and confidence | Recommended treatment |
| --- | --- | --- |
| `0x05 pl[0..1]` and `pl[2..3]` | Strong captured/reconstructed evidence for duplicated current AV words | Both equal the fixed declared AV |
| `0x05 pl[44]`, `pl[51]`, `pl[52]` | Strong evidence for legacy maximum/copy/minimum descriptors; relevant to lens ID 234 | Equal fixed endpoints; keep real lens maximum separately in the profile |
| `0x05 pl[46]` | Equality with maximum proved in this stock image; purpose and cross-profile rule unknown | Retaining that equality after AV changes is a controlled compatibility hypothesis, not known semantics or a metering repair |
| `0x05 pl[4]`, `pl[8] bit 0` | Upstream interpretation as iris transit/rest; not independently qualified here | Preserve unrelated bits; no iris-in-transit claim |
| `0x1b` requested/replied words | Upstream calls this aperture command; factory handler echoes the parsed request into two reply words | Fixed-policy response returns the only declared accepted value; qualify body acceptance |
| `0x03 pl[5..6]` | Upstream identifies the per-frame aperture command; `pl[3..4]` distinction remains unknown | Record request independently; do not make a virtual stop-down happen or alter physical-state claims |
| `0x28 pl[9..10]` | Optional AV with a `0x08` request-bit dependency; meaning/output consumer less certain than focal length | Populate fixed AV only when negotiated; otherwise zero |
| `0x35 pl[9..10]` | Same gating is described, but meaning may be a delta; no body request observed in collected traces | Keep unsupported/not emitted by the current dispatcher; do not add a speculative sink |
| `0x34` reply offset 7 word | Original instructions prove a request-word echo; semantic type unknown | Opaque bounded request echo, outside aperture module |
| `0x34` stored duplicated 850 words | Separate stored offsets; source only hypothesizes exit-pupil distance | Preserve; do not merge with the echoed word |

The numerical aperture encoding is `4096 + 256 × 2 log2(N)` in a little-endian
word. The legacy descriptor uses eighth-stop units, related by
`AV_word = 4096 + 32 × (descriptor − 8)`; nominal f/1.4 is `0x1100` and descriptor
`0x10`. An empty descriptor is not a documented unknown value. Upstream reports
an a9 II test where clearing it produced F1.0 and disabled AF. This limits that
specific experiment; it does not prove unknown aperture is universally
impossible. [Pinned aperture research](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/aperture_value.md).

The descriptor's stored f/2.8 data must not be mistaken for the stock runtime
report. Original boot routine `0x8a8c` converts descriptor `0x18`, writes f/2
current words and both maximum copies, and changes the minimum to `0x70`.
The stored `pl[46]` was already `0x18` and is not changed there, so it equals the
runtime maximum. This is an instruction-level relationship in this stock image;
it does not establish that this field must track the maximum across different
profiles. Preserving equality when changing the declared AV is a controlled
compatibility hypothesis, not known semantics or a guaranteed metering correction. See
[stock boot reconstruction](../../research/stock-1.8/stock_model.c#L262) and
[original-instruction validation](../../research/stock-1.8/validate_protocol.py).

Optional capture metadata must obey session negotiation. The pinned author
reports an a9 II metering regression when optional `0x28` AV was populated
against the body's `0x08` bit; clearing it corrected that experiment. The A6000
offers a different bit value. AF 2.5 correctly commits the capability from the
consumed snapshot in foreground code, reducing races with a later request.
These are other-body observations, not proof of the A7C II's exact bit or
metering response. [0x08 negotiation](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/msg_0x08.md),
[capture-time message](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/msg_0x28.md).

## The unsupported `0x34` inference

The original dispatcher at `0x58a4` copies SRAM `0x69a` into reply SRAM `0x30f`
and clears `0x30e`. The source snapshot begins at `0x694`; the echoed word is
therefore request payload bytes 0–1. This proves where the reply bytes come from,
not what they mean. Setting that memory to f/1.4, f/2 or f/8 in an emulator does
not establish an aperture type: an opaque cookie or query argument produces the
same result. [Reconstructed dispatcher](../../research/stock-1.8/stock_model.c#L358).

The separate stored 850 pair lives at response payload bytes 4–7, whereas the
echoed word is at payload bytes 1–2. The documentation explicitly leaves `0x34`
semantics unknown and contains stale “focus position” wording for `0x1b` that
contradicts its own updated aperture page. It also calls a 32-byte response a
32-byte payload, while the actual table has a 32-byte total frame. Resolve such
disagreements through byte offsets and original code, not prose alone.
[Pinned 0x34 document](https://github.com/weiziqian/E-mount-protocol-RE/blob/3a94a8d2e6a7786ab3e05b1319b421e76744b4c0/docs/msg_0x34.md),
[packet table and fixups](../../firmware/ea9/src/emount_packets.c#L129).

AF 2.5 skips the `0x34` RX fixups and unconditionally writes declared AV there
from `lens_aperture_publish`. Its test names the query `capture`/`AV` and sends
the same f/8-shaped operand to `0x1b` and `0x34`. That test catches a difference
between 2.4 and 2.5, but the expected value encodes the unproved interpretation.
[Implementation](../../firmware/ea9/src/lens_aperture.c#L21),
[probe](../../firmware/tests/test_aperture_query.c),
[oracle harness](../../scripts/test-refined-candidate.py).

For the follow-up, keep `0x34` on the known stock echo dependency, using the
validated consumed request snapshot. Independently validate that the two echoed
bytes are in the actual payload, excluding checksum and terminator. A
payload-free frame must not turn its checksum into a query operand. This
generic memory-safety condition is not a claim about the message's complete
legal grammar or exact request length. Until a real request grammar is captured
or recovered, reject/defer a truncated request rather than fabricate a value.
Do not prescribe an 11-byte protocol-wide request merely because the synthetic
test has 11 bytes.

## Optics: stale header versus active packet data

The warning in `emount.h` is valid **for its donor model**: a copied SEL5518Z
pupil-size row and its declared f/1.8 must be changed together. Those constants
do not describe the active 2.5 path. Production `em_init` does not call
`em_set_optical_rows`; it explicitly retains the stock packet rows before
applying the profile. Consequently, the current image does not actively install
the header's f/1.8 Sony pupil-size row and then relabel it f/1.4.
[Unused donor constants](../../firmware/ea9/src/emount.h#L490),
[production initialization](../../firmware/ea9/src/emount.c#L1322).

The active rows still have a limitation: they originate from the stock/cloned
packet table, not a measured Contax 50mm calibration. Matching numerical aperture
fields is not proof that optical correction or PDAF geometry is correct. Keep
these retained rows as a separately identified stock-compatibility baseline.
Do not rescale or install the unused Sony donor row just to make a numerical
identity hold. A future optics module needs a provenance tag, a lens/working
aperture validity range and independent measurement before claiming calibration.

Fix stale comments separately: `emount.c` around 784–803 still says `0x1b` echoes
and optional AV is reapplied immediately in the receive path, while current
foreground behavior overrides the former and commits the latter from a consumed
snapshot. These comments should not serve as evidence against the executable
path. The header's “honest permanent wide-open” language is also too strong:
a fixed report is a compatibility declaration, not a sensed physical state.

## Product policy and modular design

| Policy | Strength | Limitation | Decision |
| --- | --- | --- | --- |
| Fixed nominal camera AV, equal electronic endpoints | No false electronic stop-down range; simple select-once workflow | EXIF is a declared number; body clamp/metering still needs qualification | First supported policy to test |
| Variable virtual body AV, original menu/echo style | Closest to stock configuration mechanism | Camera may expose for a stop-down the lens never makes; owner's stock behavior already fails desired workflow | Recovery/reference only |
| Owner-entered fixed working AV | Can record a manually supplied f-number | Requires future reflashing; may change AF assumptions; remains stale after ring changes | Optional advanced metadata, not default workflow |
| Unknown camera AV | Honest camera display if supported | No established AF-capable encoding; clearing known fields has a negative reference test | Research only |

Build a small pure aperture policy layer, leaving transport and optics separate:

1. **Lens facts:** nominal maximum, focal length and lens identity. These describe
   the lens, not a measurement of the iris.
2. **Physical state:** `unknown` for this hardware. An optional owner declaration
   records provenance and freshness; it does not become a sensor reading.
3. **Camera declaration:** one validated fixed AV, normally the nominal maximum;
   electronic range endpoints both equal it. A future different policy is an
   explicit versioned enum, not special values smuggled through the numeric field.
4. **Session input:** separately record `0x03` requested AV, `0x1b` requested AV
   and negotiated optional capture metadata. Requests do not change the fixed
   declaration. Opaque `0x34` arguments belong to transport, not this state.
5. **Encoder/sinks:** one checked conversion function derives native AV and
   legacy descriptors. Publish only established aperture fields; preserve
   unrelated bits, capability behavior and opaque reply fields. Build replies
   from the request being consumed and one coherent foreground state snapshot.
6. **Optics:** retained stock rows or a future calibrated model, with confidence
   and provenance explicit. Neither the aperture policy nor a lens-name change
   silently manufactures a pupil calibration.

The camera must meter the light already passing through the chosen physical
iris; it must not schedule a nonexistent relative stop-down. Equal electronic
endpoints are intended to make that happen. This causal explanation is a
hypothesis to test, because no camera internals or A7C II transcript demonstrate
the whole path yet. Reject a blanket −1 EV correction: it would conceal one
setup's symptom and could break other modes or physical apertures.

The manufacturer's stock workflow uses body f/2 after focal configuration and
then the physical ring; it confirms that manual aperture operation is intended,
but does not override this owner's failed stock f/2 exposure report.
[Techart original manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf).
Native Voigtländer E-mount lenses also combine a manual aperture ring with
electrical metadata, demonstrating the general separation of iris control and
electronic communication; those lenses can report their own settings and are
not evidence for an unknown-iris AF adapter encoding.
[Manufacturer manual-aperture lens description](https://www.voigtlaender.de/lenses/e-mount/110-mm-12-5-macro-apo-lanthar/?lang=en).

Correct preview is not capture qualification. Sony documents display modes that
can decouple preview brightness from saved exposure, and documents metering of
scene light by image regions. Neither proves that the fixed numerical report
alone determines exposure. The owner report is enough to fail the old candidate;
a missing old photo does not block engineering.
[Sony live-view behavior](https://helpguide.sony.net/ilc/2360/v1/en/contents/0414_live_view_disp_set.html),
[Sony metering](https://helpguide.sony.net/ilc/2360/v1/en/contents/0406_metering_mode.html).

## Offline checks and minimum acceptance

The next offline suite should separate wire-preservation tests from policy
tests. Verify stock `0x34` request-word echo across arbitrary operands and
sequence numbers, exact preserved response bytes, checksum and consumed-request
ownership. Include missing/truncated payloads so checksum bytes cannot become
data. Keep the 2.5 regression as historical implementation evidence; do not
rewrite its results as stock correctness.

For aperture sinks, test all supported profiles, native/descriptor round trips,
both fixed endpoints, fixed `0x05`/`0x1b` behavior under conflicting body requests,
`0x03` requests not mutating state, both `0x08` capability choices, session reset
and back-to-back request snapshots. Assert `0x35` remains unsupported/not emitted
by the current dispatcher; absence of a dispatcher entry alone does not prove
what the advertised capability bits mean. Check that lens-profile application
does not install donor rows unexpectedly. Test
actual transmitted frames, not only the module's backing buffer.

USB-cap checks qualify image identity and recovery, not exposure or AF. After a
separately coordinated upload and strict reconnect readback, the smallest useful
A7C II comparison is:

1. Loaded 50mm, lens focus ring at infinity, physical f/1.4. Establish a normal
   lifecycle in MF/Pre-AF Off and confirm the exact aperture display and whether
   the body can select a different f-number. Unexpected dial freedom is a policy
   failure to diagnose, not permission to keep compensating manually.
2. Stable indoor scene, no flash, EV 0 and documented ISO/metering/display
   settings. Check A mode with physical f/1.4, then physical f/4 **without updating
   the app or camera declaration**. Both saved exposures should be normal; the
   shutter/ISO response should account for the reduced transmitted light.
3. Repeat the two physical aperture states in P and Auto to qualify the promised
   seamless workflow. Compare saved results rather than preview alone. An
   owner-reported exposure failure stops qualification; retained files are
   useful for quantitative/EXIF claims, not prerequisites for accepting failure.
4. Only after normal lifecycle/metering, use AF-S/Pre-AF Off and a central
   contrasting subject. Check a near/far acquisition at f/1.4, then physical f/4.
   Bound each acquisition attempt: release the half-press or AF-ON after roughly
   two seconds of unsuccessful hunting, and do not repeat a failed attempt to
   force a result. Record motor stop, achieved focus, shutter release, hunting
   and shutdown.
   Loss of AF when stopped down is a qualification limit to document, not a
   reason to report a fictional physical aperture.

Use existing motor stop conditions for abnormal continuous drive, grinding or
repeated stop impacts. No new repeated stock-photo exercise is required now.
Failure in one mode does not prove all others fail or that the encoding itself
caused the failure; keep the exact setup and result attached to each check.

Remaining unknowns are the A7C II's aperture/capture transcript, whether equal
endpoints actually clamp the dial in every mode, the role of `0x05 pl[46]`, the
semantics/legal grammar of `0x34`, optional capture metadata consumption, and
real stopped-down PDAF geometry. These are bounded integration questions. They
do not justify indefinitely delaying a corrected, carefully versioned candidate,
and they prevent claiming seamless behavior before the camera checks pass.
