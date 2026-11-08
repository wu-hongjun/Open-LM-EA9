# System design

The current [bank host integration](bank-migration-2026-11-07.md) separates
ProfileBank (pinned codecs/state), BankPlan (pure migration/selection/rollback),
BankStore (durable reconstructed evidence), BankCoordinator (injected transport)
and BankService (existing native session/lock/reconnect safety). BankWorkflow
provides the card UI; firmware source and published 4.8 segments are unchanged.
Historical preparation details below predate that integration.

The firmware remains C on the SAMD21E17A, using upstream protocol and motor
control with the proven 750 kbaud fallback. The macOS app remains SwiftUI/AppKit
and Swift IOHID. A Rust rewrite is deferred while building on the working base.

The firmware separates the E-mount parser/status engine (`emount.c`), packet
and optical data, motor/encoder/servo control, focus mapping, and the aperture
reporting mailbox (`reported_aperture.c`). Release diagnostics are compiled out;
there are no runtime log writes. Source hashes and a clean rebuild protect the
working image. The 4.6 preparation changes only range constants in a build copy.
Optical tables are inherited, not calibrated for every lens.

`firmware/core/` holds those shared protocol and mapping modules.
`firmware/targets/lm-ea9/` owns the board, startup, clock, power, encoder, motor,
servo, bus peripheral drivers, linker and exact build rules. These are explicit
porting seams; LM-EA9 is the only implemented hardware target.
`firmware/configurations/` supplies lens/build inputs; the offline builder changes
only a build copy, records provenance and labels custom images unqualified.

The native app has three layers:

- `LensCore`: local library, versioned JSON, validation and lens metadata.
- `DeviceKit`: descriptors, exclusive IOHID, qualified backup, pinned image
  admission, durable update journal, guarded upload, reconnect verification
  and stock recovery. Presentation cannot bypass these checks.
- `OpenLensAdapter`: two-card Device home (Adapter left, Lens right), secondary Lens Library, and a compact USB panel.
  Automatic refresh enumerates connections and reads local history only.

`ea9ctl` uses the same native service. Firmware preparation never touches USB.
The USB cap still enters the vendor loader; this project does not claim a
running-application USB management service. Camera-selected aperture is volatile
and inaccessible to the app after power-off. Profile edits stay local until a
separate image exists. The offline 4.7 prototype personalizes a pinned template's
focal/startup words, name and CRC-protected record; full-image reconstruction
validates every readback byte. That fallback remains a complete application
rewrite, explicitly labeled in the UI. Lightweight profile selection instead
needs a bank, wear-leveled settings and a qualified transport, as described in
[the persistence design](lens-profile-persistence.md).
The separate 4.8 sparse-package builder now integrates a portable bank/journal,
a SAMD21 NVM port and boot-time optical metadata application. It uses a new
upper-flash ownership contract without replacing existing unit data. Its offline
host planner has no transport; native source admission remains unchanged.
[Module/layout details and qualification limits](profile-bank-2026-11-07.md).
Older journals use read-only code pins rather
than bundling retired executable firmware.

The display/product name is OpenLensAdapter. Storage identity, bundle identifier,
backup type and encrypted-recovery format remain compatible with the earlier app.
