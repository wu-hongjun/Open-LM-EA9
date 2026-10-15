# Device workflow: prototype 0.19.0, build 23

Open `dist/Open LM-EA9.app`. The **Device** tab shows the adapter photo,
connection, dated firmware read and the last USB-verified lens setting.
Actual aperture is **Unknown**; the displayed fixed f-number is camera metadata.
Use the lens ring to stop down. The library editor can declare a fixed camera
f-number for firmware with a runtime profile row. Upstream candidates instead
compile the original 50mm f/1.4 profile; library edits stay local on those images.
The secondary **Lens Library** tab retains the photographs and metadata editor.

The latest packaged candidate is **upstream AF 3.6.0**, camera-unqualified.
Its [authorized upload](evidence/upstream-36-upload-2026-10-15.md) is complete;
owner physical reconnect and strict verification are pending. USB tools provide **Install Upstream AF 3.6.0** as a separate
action; changing the dropdown does not install it. The native CLI equivalents
are `prepare-handoff-upstream` and `apply-handoff-upstream`. Other/edited profiles
are rejected. [Build/test evidence](evidence/upstream-36-handoff-2026-10-15.md)
and the [coordinated installation/camera procedure](upstream-handoff-test.md)
describe the exact image and its limits.

Startup diagnostic **3.2.0** was uploaded for the original 50mm f/1.4
profile on October 15. [Strict verification passed](evidence/upstream-32-upload-2026-10-15.md)
after owner-confirmed physical reconnect, resolving that transaction before 3.6.
Do not delete or edit a pending journal or reconnect marker.
The historical `prepare-startup`/`apply-startup`
commands still select 3.2. Installed 3.2–3.6 routes the main action to USB tools,
labels camera compatibility unqualified and avoids ordinary profile application.
After one coordinated camera cycle, save a read-only backup and use the offline
decoder before further camera trials.
Initial full-image verification includes the blank log area. Later log retrieval
does not relax that check; ordinary image inspection still rejects changed bytes.

AF 3.0 was prepared offline. Its October 14 upload and strict physical-reconnect
verification passed. Camera acceptance subsequently failed with full-press
freeze requiring battery removal; further AF 3.0 trials are held. See
[the failure record](evidence/af-30-camera-failure-2026-10-14.md) and
[the installation record](evidence/af-30-upload-2026-10-14.md).
AF 2.9 is explicitly held after capture/shutdown failure. See
[the historical AF 3.0 milestone](evidence/af-30-candidate-2026-10-13.md).

The [upstream 3.1 baseline](evidence/upstream-baseline-2026-10-14.md) is uploaded
and strictly byte-verified after physical reconnect, with a separate offline
audit. Camera acceptance subsequently failed: aperture `--`, blocked shutter,
no motor movement and normal shutdown. Actual focus mode remains unverified;
further 3.1 trials are held. App 0.14.1 marks that installed image as held and
disables ordinary baseline installation, retaining the verified USB history.
See [the failure investigation](evidence/upstream-31-camera-failure-2026-10-14.md) and
[the installation record](evidence/upstream-31-upload-2026-10-14.md).
App 0.14 prominently marks installed AF 3.0 as held
and routes the primary action to USB tools. Its strict USB result remains valid
while camera capture/shutdown acceptance is failed.

## Choose a lens and apply supported metadata

All eight lenses can be edited and prepared locally. **Apply profile** requires
verified firmware with a runtime profile row. The upstream 3.1–3.6 candidates
are fixed to the original 50mm f/1.4 and offer USB tools instead. They cannot
switch to the selected lens or use an aperture override without a new firmware
candidate. The following apply sequence is for supported runtime-profile images.

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
verified installed firmware variant, including legacy AF 2.1. Installing an
upstream candidate is a separate **USB tools → Experimental autofocus** action,
with its own pinned image and coordinated test. Installed fixed upstream firmware
explains its compiled configuration and offers USB tools from the dropdown.
The CLI `apply-upstream` still selects held 3.1 for explicit recovery/research;
do not retry it for camera use. Historical `apply-af` still selects held 3.0.
Plain `apply` selects metadata-only 2.0.

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

A corrupt local firmware history now shows **Review recovery state**, hides stale
on-adapter lens information and blocks conflicting changes. The corrupt file is
retained; repairing the history is recognized on refresh. The app cannot infer
current adapter settings from an unreadable local record.

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

## Historical validation

The main view uses the existing sourced photos, compact adapter/firmware card,
verified lens photo and a visible dropdown/apply row. No new remote images or
runtime network requests were added. The earlier visual release was built and inspected with
the connected adapter; 0.14 packaging and tests were offline. Its last saved 2.1.0/50mm f/1.4 history loaded correctly;
the 85mm dropdown selection was exercised and restored to 50mm without an upload.
See [the test and hardware-boundary evidence](evidence/af-reconciliation-2026-10-10.md).

After the AF 2.2 reconnect/readback on Oct 11, the same app loaded the completed
2.2.0/50mm f/1.4 history and displayed **USB verified** and **Up to date** without
a rebuild or explicit HID read. See the [completed installation record](evidence/af-22-upload-2026-10-11.md).

App 0.7 and the AF 2.4 baseline were validated offline; see [the preparation evidence](evidence/factory-af-baseline-2026-10-11.md). The stock restore was subsequently resolved by an explicit reviewed-motion policy retaining its strict failure. The authorized AF 2.4 upload and strict byte verification passed after physical reconnect, with an independent audit. The later owner focus attempt failed, with a dark view and no shown f-number in P/A; further 2.4 camera trials are suspended. Stock recovery passed normal strict verification after physical reconnect and an independent audit. The new stock display/lifecycle and AF-S baseline remain pending. See [the failure investigation](evidence/af-24-camera-failure-2026-10-11.md) and [completed recovery record](evidence/stock-18-af24-recovery-2026-10-11.md).

App 0.9.0/build 12 offers explicit AF 2.6 installation. Normal dropdown changes
preserve the verified installed variant. The [2.6 record](evidence/af-26-candidate-2026-10-11.md)
covers offline preparation and the restored opaque `0x34` reply; exposure and
optical AF remain unqualified. The previous [2.5 candidate](../firmware/candidates/2.5.0/README.md)
remains frozen and held after the [aperture audit](audits/aperture-protocol-design-2026-10-11.md).
The adapter was disconnected during 2.6 preparation; that dated record describes
its own preparation boundary and does not select 2.6 in the current app.
