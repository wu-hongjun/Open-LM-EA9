# Device workflow: prototype 0.7.0, build 10

Open `dist/Open LM-EA9.app`. The **Device** tab shows the adapter photo,
connection, dated firmware read and the last USB-verified lens setting.
Actual aperture is **Unknown**; the displayed fixed f-number is camera metadata.
Use the lens ring to stop down. The library editor lets you override the fixed
camera f-number while retaining the unknown physical setting.
The secondary **Lens Library** tab retains the photographs and metadata editor.

## Change a lens

1. Connect the adapter through its USB cap with TECHART Update closed.
2. Choose a lens in the **Lens profile** dropdown on Device. All eight requested
   lenses are included, with the corrected Biotar 58mm f/2. The selected-on-Mac
   preview shows the focal length and reported aperture that will be applied.
3. Confirm **Updater closed · USB cap reconnected**, then click **Apply profile**.
4. After upload, physically unplug and reconnect the cap. The app detects the
   new connection; confirm the prerequisite again and click **Verify lens**.
5. Use the adapter on the camera after byte verification succeeds.

Choosing a profile saves only a local preparation. The on-adapter photo and
setting retain the last verified value until the uploaded image is verified.
An unchanged profile shows **Up to date**. The primary action preserves the
verified installed firmware variant, including legacy AF 2.1. Upgrading to the
new AF 2.4 is a separate **USB tools → Experimental autofocus** action.
The CLI `apply-af` now selects 2.4; plain `apply` selects metadata-only 2.0.

The status panel explains the next action: connection, one-time setup, reading
unknown settings, unsaved edits, incomplete zoom data, confirmation, reconnect,
verification or a completed profile match. If an AF version is known but its
verified lens history is missing, **Read lens settings** identifies the image
before the main profile action becomes available. It cannot silently fall back to
metadata-only firmware. A newer stock-version observation hides older AF history;
a successful stock-image read archives the old lens record and clears that setting.
An unfinished update from another adapter points to USB tools rather than offering
an unavailable verification action.

If this is a new unit, **Set up adapter** performs the existing backed-up stock
upload/reconnect qualification before custom application uploads are allowed.
The zoom requires a saved current focal length before applying; **Edit lens…**
opens its editor. Unsaved edits and unresolved update journals prevent conflicting
changes. Backups and restoration remain in USB tools.

## Automatic refresh

The app checks macOS USB/HID descriptors and bounded local history every two
seconds, on launch, and when it becomes active. It detects connection changes
and reloads CLI-published verification records while the window stays open.
The monitor cancels when the view ends, skips active operations and rejects
overlapping refreshes. A changed registry ID, blocked connection or discovery
failure clears the connection acknowledgement. Multiple adapters disable USB
operations. Discovery failure clears the displayed device list.

Automatic refresh sends **no HID feature reports, CHECK, READ or START**.
Firmware and lens labels remain dated local evidence associated with the
qualified unit's serial, not fresh USB readings or identification of a passive
mounted lens. **Read Version** and **Read Adapter Lens** remain explicit in
USB tools. This distinction matters because an armed stock bootloader can
interpret an ordinary read request as the next firmware page. Keep the physical
reconnect guard even though discovery itself is automatic.

The main view uses the existing sourced photos, compact adapter/firmware card,
verified lens photo and a visible dropdown/apply row. No new remote images or
runtime network requests were added. The release was built and inspected with
the connected adapter. Its last saved 2.1.0/50mm f/1.4 history loaded correctly;
the 85mm dropdown selection was exercised and restored to 50mm without an upload.
See [the test and hardware-boundary evidence](evidence/af-reconciliation-2026-10-10.md).

After the AF 2.2 reconnect/readback on Oct 11, the same app loaded the completed
2.2.0/50mm f/1.4 history and displayed **USB verified** and **Up to date** without
a rebuild or explicit HID read. See the [completed installation record](evidence/af-22-upload-2026-10-11.md).

App 0.7 and the AF 2.4 baseline were validated offline; see [the current evidence](evidence/factory-af-baseline-2026-10-11.md). The stock restore was subsequently resolved by an explicit reviewed-motion policy retaining its strict failure. The authorized AF 2.4 upload and strict byte verification passed after physical reconnect, with an independent audit. Camera qualification remains pending. See [the current hardware record](evidence/af-24-upload-2026-10-11.md).
