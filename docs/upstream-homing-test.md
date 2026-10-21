# AF 3.9 — separate upload, one camera cycle and log retrieval

AF 3.9 upload is complete; **owner-confirmed reconnect and strict byte verification
are pending. No camera test has occurred.** [Upload record](evidence/upstream-39-upload-2026-10-20.md).
The ADC dependency repair is source-verified, but a physical homing or shutter
cure remains unproven. The owner has separately authorized this upload,
verification and one test cycle. Keep the adapter off-camera until verification
passes; existing 3.8 camera testing remains held.

[Candidate/pins](../firmware/candidates/3.9.0/README.md) ·
[Evidence and limits](evidence/upstream-39-homing-2026-10-20.md).

1. Confirm the adapter is on its USB cap, the updater and Open LM-EA9 app are
   closed, and the camera is off. Resolve any existing pending verification
   using its original journal; never edit a reconnect/safety marker manually.
2. Through the guarded native `apply-homing-upstream` route, use only the
   original unedited `contax-zeiss-50-f1-4` profile. Preserve a fresh matching
   two-pass backup and the durable upload journal. Historical prepare/apply
   commands still select their historical images.
3. After upload completes, stop USB reports on that connection. Have the owner
   physically unplug/reconnect the cap and explicitly confirm it. Strictly
   verify the complete pristine3.9 application, metadata/version and unchanged
   protected flash/auxiliary data before camera use. Do not substitute a
   diagnostic-prefix comparison for initial complete-image verification.
4. With the A7C II off and its USB cable disconnected, mount the LM-EA9,
   C/Y-to-M converter and50mm f/1.4. Set the physical focus ring to infinity
   and iris to f/1.4. Choose still-photo A exposure, EV0 and AutoISO. Separately
   choose **MF** in Focus→AF/MF→Focus Mode and Pre-AF Off if available. A or
   AUTO exposure does not establish the focus mode. If MF cannot be confirmed,
   skip the photo.
5. Switch on without shutter/AF-ON input. Note live preview updates, brightness,
   aperture display (expected f/1.4), movement and whether it stops. Wait ten
   seconds after movement stops. Only if preview/aperture/motor behavior is
   normal and MF is confirmed, take one photo. Switch off once and leave off.
   Do not restart or add AF attempts before reviewing this cycle's evidence.
6. Stop for frozen preview, grinding, repeated stop impacts or abnormal
   continuous drive for about two seconds. Switch off; remove the battery if
   unresponsive or motion continues. No retry. Report saved-file presence,
   actual focus/Pre-AF settings, brightness/aperture, movement/quiet idle and
   whether shutdown worked. Unknown observations stay unknown.
7. After the camera is off/unpowered and the motor has stopped, return to the
   USB cap, physically reconnect with both apps closed and explicitly confirm
   it. Retrieve one guarded two-pass read-only backup; retain raw dumps,
   identifiers and real frames privately. Decode offline with the registry-bound
   decoder, and independently compare every byte outside the diagnostic range
   to the pristine installation/protected-data baseline.

The 3.9 failure tail records phase 17/18/19, drive qualification, phase/cutoff and
last-iteration ticks, initial position, stillness anchor coordinate/tick and
shared poll count. A separate saturated count records consumed non-Stop requests
after the tagged failure. It does not count shutter attempts or motor execution.
No tail means no conclusion: cancellation, interrupted persistence, full storage
or another path can omit it. Tick intervals are not measured wall time. The
stillness anchor is the initial or last threshold-crossing observation, not a
final encoder sample. A successful local TX
return or complete planned log snapshot does not establish camera acceptance.

Only after reviewing this result should a separately agreed AF-S comparison be
considered. A single photograph cannot establish sustained capture or factory
parity. Preserve original stock 1.8 recovery and every historical image; no stock
restoration is part of this offline preparation.
