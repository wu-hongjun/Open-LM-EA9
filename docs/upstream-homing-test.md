# AF 3.9 — separate upload, one camera cycle and log retrieval

**AF 3.9 upload and strict complete-image/protected-data verification passed,
but camera acceptance subsequently failed. Further 3.9 camera trials are held.**
The owner reports two photos followed by blocked further capture and normal
shutdown. [Read-only logs](evidence/upstream-39-camera-failure-2026-10-20.md) retain
a drive-phase failure with insufficient stillness before the cap and later
consumed requests. No repeat, restart or further camera cycle is requested.
[Installation record](evidence/upstream-39-upload-2026-10-20.md).

The steps below preserve the historical requested one-cycle procedure. Actual
focus/Pre-AF, saved-file status and adherence remain unknown. The owner reported
two photos; this is not relabeled a controlled MF or AF-S comparison. A later
reviewed candidate needs its own separate authorization and verification gates.

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
   C/Y-to-M converter and 50mm f/1.4. Set the physical focus ring to infinity
   and iris to f/1.4. Select still-photo A on the exposure dial.
5. Switch on once without shutter/AF-ON input. Check live preview updates,
   brightness, aperture (expected f/1.4) and whether movement stops. If normal,
   use the powered-on menus to select **MF** in Focus→AF/MF→Focus Mode, Pre-AF
   Off if available, EV 0 and Auto ISO. Do not press shutter/AF-ON before MF is
   confirmed. A or AUTO exposure does not establish focus mode; inherited
   startup focus mode remains unknown unless observed. Wait ten seconds after
   any movement stops. Only if preview/aperture/motor behavior is normal and
   MF is confirmed, take one photo. Otherwise skip it. Switch off once and
   leave off; do not restart or add AF attempts before evidence review.
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

AF-S is not a next gate for held 3.9. A later reviewed candidate needs separate
installation/verification and test authorization. A single photograph cannot
establish sustained capture or factory parity. Preserve original stock 1.8
recovery and every historical image; no stock restoration was performed during
this read-only analysis.
