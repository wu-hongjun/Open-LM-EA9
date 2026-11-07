# System design

The firmware remains C on the SAMD21E17A, using upstream protocol and motor
control with the proven 750 kbaud fallback. The macOS app remains SwiftUI/AppKit
and Swift IOHID. A Rust rewrite is deferred while building on the working base.

The firmware separates the E-mount parser/status engine (`emount.c`), packet
and optical data, motor/encoder/servo control, focus mapping, and the aperture
reporting mailbox (`reported_aperture.c`). Release diagnostics are compiled out;
there are no runtime log writes. Source hashes and a clean rebuild protect the
working image. The 4.6 preparation changes only range constants in a build copy.
Optical tables are inherited, not calibrated for every lens.

The native app has three layers:

- `LensCore`: local library, versioned JSON, validation and lens metadata.
- `DeviceKit`: descriptors, exclusive IOHID, qualified backup, pinned image
  admission, durable update journal, guarded upload, reconnect verification
  and stock recovery. Presentation cannot bypass these checks.
- `OpenLMEA9`: two-card Device home (Adapter left, Lens right), secondary Lens Library, and a compact USB panel.
  Automatic refresh enumerates connections and reads local history only.

`ea9ctl` uses the same native service. Firmware preparation never touches USB.
The USB cap still enters the vendor loader; this project does not claim a
running-application USB management service. Camera-selected aperture is volatile
and inaccessible to the app after power-off. Profile edits stay local until a
separate compiled image exists. Older journals use read-only code pins rather
than bundling retired executable firmware.
