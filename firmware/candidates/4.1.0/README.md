# AF 4.1 — crash diagnostics

**Prepared offline; not uploaded or camera-qualified.** Fixed to the original
Contax Zeiss 50mm f/1.4, lens ID 234, nominal AV 4352. Physical iris remains unknown;
lens-library edits stay local. This adds evidence and fail-stop behavior, not a
proven homing, shutter-freeze, optical AF or factory-parity fix. The upstream C
controller, capture/shutdown policies and 4.0 homing qualification remain inherited.

After the [4.0 battery-required crash](../../../docs/evidence/upstream-40-camera-failure-2026-10-21.md)
left all 16 diagnostic pages erased, three Astra lanes reviewed retained checkpoints,
original boot instructions, watchdog/flash ownership and interrupted writes.
A 48-byte summary with CRC/commit marker occupies a fixed 56-byte retained SRAM area.
A nominal four-second independent watchdog is serviced only by foreground progress;
HardFault requests system reset using a naked, stack-independent handler. On a
qualifying warm reset, one boot-time flash page can preserve the last checkpoint
before battery removal. When app recovery is reached, motor GPIOs are released before persistence; a crash or damaged
storage stops before normal motor/protocol initialization and remains latched.

Immediate battery removal before persistence, failed bootloader handoff, a fully
erased failed write and a camera-only stall while foreground health continues are
uncovered. Physical retention/watchdog timing and flash power-fail behavior are
unqualified. No active-protocol flash writes, runtime erase, new motor algorithm,
fault-stack dereference or automatic restart/rehoming was added.

| Artifact | SHA-256 |
| --- | --- |
| [20,480-byte image](contax-zeiss-50-f1-4.bin) | `fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641` |
| [Manifest](contax-zeiss-50-f1-4.manifest.json) | `557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b` |

[Exact delta](from-40.patch) extends the trace/flash modules and main/servo service
points, linker reservation and camera version. Code/data end 39412 (`0x99f4`),
margin 524 before the unchanged 1024-byte diagnostic region; ordinary static RAM 3048,
retained 56 at`0x20003fc0`, reserved stack 8192. Servo additionally uses`-Os` to retain
the 256-byte flash floor. Failed-home tag0x40 is inherited. Only 4.1 admits the new
standalone type 5 record under the image/manifest registry pins.

[Integrated evidence](../../../docs/evidence/upstream-41-crash-diagnostics-2026-10-21.md) ·
[Build/test workbench](../../upstream-hardening/next41/README.md) ·
[Later installation/test/log procedure](../../../docs/upstream-crash-diagnostic-test.md).

All151 historical release/recovery/pin artifacts and older registry entries remain
exact. Original stock 1.8 recovery is preserved. App 0.24.0/build 33 exposes an explicit
4.1 research action;4.0 remains held. No adapter access, canonical host-state edit,
app launch or new camera observation belongs to this offline milestone.
