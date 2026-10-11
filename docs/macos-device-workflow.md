# Device workflow: prototype 0.5.0, build 8

Open `dist/Open LM-EA9.app`. The **Device** tab shows the adapter photo,
connection, dated firmware read and the last USB-verified lens setting.
The secondary **Lens Library** tab retains the photographs and metadata editor.

## Change a lens

1. Connect the adapter through its USB cap with TECHART Update closed.
2. Choose a lens in the **Lens profile** dropdown on Device. All eight requested
   lenses are included, with the corrected Biotar 58mm f/2.
3. Confirm **Updater closed · USB cap reconnected**, then click **Apply profile**.
4. After upload, physically unplug and reconnect the cap. The app detects the
   new connection; confirm the prerequisite again and click **Verify lens**.
5. Use the adapter on the camera after byte verification succeeds.

Choosing a profile saves only a local preparation. The on-adapter photo and
setting retain the last verified value until the uploaded image is verified.
An unchanged profile shows **Up to date**. The primary action preserves the
verified installed firmware variant, including legacy AF 2.1. Upgrading to the
new AF 2.2 is a separate **USB tools → Experimental autofocus** action.
The CLI `apply-af` now selects 2.2; plain `apply` selects metadata-only 2.0.

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
