# Independent Astra implementation audit — 2026-10-10

The current implementation has a well-bounded upload engine and meaningful offline verification, but its original host safety boundary needs correction before further hardware commands. Two P1 findings allow a nominal read to reach a loader that another session has already armed. This audit recommends retaining the native Swift host and metadata-only C candidate while fixing host coordination, recovery UX and durable publication. It does not qualify custom firmware for the A7C II or establish power-loss recovery.

## Scope and evidence boundary

Reviewed DeviceKit, CLI, app operation/UI state, firmware profile integration, linker/build controls, tests and recorded USB evidence. No USB inventory, HID open, report, readback, flash, updater launch or live app automation was performed. No production sources, shared build products, or user Application Support files were changed. The only repository output of this audit is this report.

The hardware evidence still says **stock upload acknowledged; physical reconnect and readback pending**. Recorded 1,729 ACKs are consistent with START plus 1,728 pages spanning `[0x5000,0x20000)`. They do not prove the written flash contents. The custom 50 mm f/1.4 image is not recorded as installed. The loader must continue to be treated as armed until the owner physically reconnects it.

Line references below identify the reviewed source snapshot, taken before concurrent remediation by the coordinating agent. That agent was notified early and implemented corrections during this audit. A bounded source re-review of those corrections is recorded below; the findings retain the original line references for traceability. Source hashes identifying the baseline are recorded at the end.

## Findings, ordered by severity

### P1 — Alternate CLI state directories bypass the armed-connection block

**Locations:** `apps/macos/Sources/EA9CLI/main.swift:11–15`; `apps/macos/Sources/DeviceKit/NativeHID.swift:128`, `137–143`, `302–308`.

The public CLI accepts `--state-directory` for hardware operations and passes that directory into `DeviceService`. The service stores its reconnect-required IDs in that directory. After an upload using the default directory, a later hardware command using a fresh directory sees no block even on the same registry ID. A backup begins with CHECK; in loader state 2, that 64-byte report is application programming data. At the end of a full stock upload, the pointer is already at the application range end, so sending more packets is especially unacceptable; the exact out-of-range consequence is not established here.

This is a static execution-path finding, not a hardware experiment. The `--idle` assertion cannot override a known armed connection; changing a library/test path should not erase that knowledge.

**Fix:** use one canonical safety store for every production DeviceService, independent of library, journal and output locations. Remove hardware-operation redirection or keep test injection internal to an explicitly fake backend. Preserve/migrate existing blocked IDs without clearing them. Fail closed on an unreadable canonical marker.

**Required test:** plant a blocked synthetic ID in the canonical test safety store, create clients with different library directories, and prove every report-producing operation fails before the injected native boundary.

### P1 — Per-instance reservation leaves a cross-process check/open race

**Locations:** `apps/macos/Sources/DeviceKit/NativeHID.swift:125–135`, `302–317`.

The NSLock and `busy` flag reserve one DeviceService instance. Neither protects the shared marker against a second GUI/CLI process. Exclusive HID access prevents simultaneous ownership, but the marker is checked before that ownership is acquired. One possible ordering is: B reads an empty marker and pauses; A completes an upload, saves its block, and closes HID; B resumes from its stale marker state, acquires the now-free HID handle and issues CHECK/READ with a fresh idle phase. Thus canonicalizing the marker alone does not close the safety gap.

**Fix:** acquire a canonical interprocess operation lock before loading/checking safety state; hold it until native handles are closed and final state is published. All GUI/CLI service instances must use it. Re-read pending transaction state under the same coordination where it governs the operation. Prefer a bounded/nonblocking busy response. Atomic rename is not a lock. Existing external updater checks and HID seizure remain useful additional controls.

**Required test:** use two processes or independently instantiated services and an injected native boundary. Pause one client at admission, let the other perform a simulated upload, then show that the first client re-evaluates the persisted block rather than sending a report. No physical device is needed.

### P2 — Corrupt local history disables the GUI stock-recovery path

**Locations:** `apps/macos/Sources/OpenLMEA9/AppModel.swift:222–239`, `136–139`, `270–271`; `apps/macos/Sources/OpenLMEA9/DeviceOverview.swift:203`.

`refreshDevices` puts successful OS inventory and decoding of pending, applied and stock-qualification records inside one `do/catch`. Any malformed local record clears `devices`, sets `discoveryError`, and disables `canReadDevice`. Stock Restore is consequently unavailable even after a genuine reconnect. The service deliberately permits recovery without decoding the failed pending journal, but the GUI cannot reach that path. A corrupt applied-history record is enough to create the same problem.

**Fix:** separate connection discovery, safety-marker state and optional/local-history decoding. Preserve the inventory on history errors; expose the record error and keep normal apply/verification fail-closed. Permit explicit stock restoration from a validated backup after ordinary connection/reconnect guards pass. Preserve corrupt evidence rather than reseeding or deleting it.

**Required test:** malformed pending/applied/qualification records independently leave the recovery action reachable for a simulated qualified fresh connection while ordinary apply remains unavailable. A malformed safety marker must still block reports.

### P2 — Upload interruption is presented as “Cancel Backup”

**Locations:** `apps/macos/Sources/OpenLMEA9/DeviceOverview.swift:188–193`; `apps/macos/Sources/OpenLMEA9/AppModel.swift:322–336`, `394`; `apps/macos/Sources/DeviceKit/Upload.swift:42`.

The USB tools sheet renders a generic busy/progress panel with `Cancel Backup` for any operation. Its shared cancellation token also controls stock qualification, custom upload and restoration. Opening USB tools during an upload can therefore interrupt flash programming through an action described as canceling a read-only backup. The quit path warns about an incomplete application, but this button does not.

**Fix:** track operation kind and phase explicitly. Once START is attempted, either withhold ordinary cancellation until the bounded transfer completes or use an accurately named stop action with an incomplete-firmware/recovery warning. Keep cancellation and transport failure conservative: no retries or extra commands. A pending verification marker and reconnect requirement must survive every stopped upload.

**Required test:** operation-specific UI state for preflight, upload, reconnect and verification; selecting a backup cancellation action must never silently cancel a programming phase.

### P2 — “Durable” recovery publication lacks an explicit persistence barrier

**Locations:** `apps/macos/Sources/DeviceKit/NativeHID.swift:141–143`, `236`; `apps/macos/Sources/DeviceKit/Upload.swift:158–162`; `apps/macos/Sources/DeviceKit/Backup.swift:164–180`.

The pre-START marker and journal use Foundation atomic replacement, and backup publication uses writes, read-after-write comparisons and directory rename. The visible implementation contains no explicit file synchronization and directory publication barrier. Atomicity and successful rereads do not establish that the backup and journal have reached stable storage before device flash is changed. The current test titled `journalSurvivesArmedCrash...` checks serialization/reload, not abrupt process or host-power failure.

This is a durability guarantee gap, not evidence that normal app termination loses files. Host power loss often also resets USB, but that does not restore an original backup that was never durably published.

**Fix:** centralize private durable publication with explicit checked synchronization for backup contents, manifest, marker/journal and their directory entries before START. Keep immutable recovery copies where needed. On synchronization failure, send no START. Document the supported filesystem/storage durability limits and distinguish process-crash tests from host-power-loss evidence.

**Required test:** fault injection at each write/sync/rename stage proves that no START occurs before required publications succeed. Subprocess termination tests should prove recovery state remains interpretable after each committed boundary.

## What the current implementation gets right

- UploadEngine enforces a nonempty 256-byte-aligned image no larger than `0x1b000`, emits exactly one START and one report per 64-byte page, requires byte-exact echoes, never retries, and sends no post-upload marker. The stock-sized test reaches exactly `0x20000`; the custom image ends at `0xa100`.
- NativeTransport marks the phase armed before attempting START. Same-session reads and repeated START are rejected. Errors after attempted reports leave conservative reconnect state. Callback validation rejects wrong type/ID/length and duplicates; cancellation never causes an automatic retransmission.
- Backup qualification pins boot code, descriptor, MCU identity and flash geometry, compares two complete flash reads, and publishes a bounded manifest with digests. Restoration requires the unit-matched known stock application. Unknown metadata versions are admitted only through the recovery path with pinned boot code.
- Verification compares the complete intended application, unchanged boot code and remaining flash, 58 known START metadata bytes, and factory snapshots. It requires a new connection identity with the same serial. The six loader-overread metadata bytes are explicitly excluded and still retained in full backups; this is a documented exception, not full metadata equality.
- The app does not automatically call CHECK/READ on launch, refresh, tab changes or local lens selection in the reviewed code. Manual firmware reads remain behind acknowledgment and service guards. Cached observations are not a substitute for byte verification.
- The custom firmware is small and constrained: code `[0x5000,0xa000)`, one 256-byte profile at `0xa000`, CRC and canonical range/string validation shared through cross-language fixtures. The linked ELF contains motor initialization/release but no surviving motor-drive/brake/seek, servo, diagnostic or trail implementation. Absence of those symbols does not itself electrically qualify startup pin transients or camera shutdown behavior.

## Independent offline checks performed

A copy of `apps/macos` was built under a newly allocated temporary directory, leaving shared build products untouched. All **28 Swift tests passed: 7 LensCore and 21 DeviceKit**. The only DeviceService tests terminate at pre-native guards; no hardware-facing command was run. These tests are valuable but do not cover the P1 cross-process/path findings.

Compiled the E-mount framing test and profile test separately with `-fsanitize=address,undefined`, `-Wall -Wextra`, and ran the profile test against all **seven existing prime-lens fixtures**. All passed with no sanitizer findings. The linker emitted only its common-section alignment warning in these host builds. This run adds memory/undefined-behavior coverage for the exercised paths, not hardware timing coverage.

Independently hashed the generated firmware binary and the bundled DeviceKit resource: both are **20,736 bytes**, SHA-256 `d7f85bb53897d6b83f30c528d7790ec37e7164090d882251b917060cc300f293`. Inspected ELF symbols and the linker script; profile placement is `0xa000` and the code/profile overlap assertion is present. Dead motion functions occur in discarded map sections, not in the linked symbol set.

Recorded stock-upload evidence was checked for arithmetic and scope consistency: 110,592 application bytes / 64 = 1,728 pages, plus START = 1,729 reports. Its `postUploadReadbackPerformed` and `cameraQualified` fields are false, consistent with the milestone narrative.

## Architecture and optimization priorities

1. **Finish host safety before increasing capability.** Split NativeHID into a native connection adapter, a transport-independent operation coordinator, and durable safety/recovery storage. Inject only the native boundary in tests so all production admission, journal, cancellation and verification paths can be exercised without USB. Model operation phases explicitly rather than spreading `busy`, pending, acknowledgment and reconnect booleans across UI and service code.
2. **Retain SwiftUI/AppKit + native Swift IOHID and the C reference qualification build.** No current evidence justifies an immediate firmware rewrite or shared Rust FFI layer. Extract pure profile/packet/state logic behind narrow C interfaces first; compare a Rust implementation later against the same vectors, memory budget and measured camera timing. This preserves a meaningful baseline for the A7C II.
3. **Treat the metadata image as a qualification tool, not the final management protocol.** The stock cap path cannot reach an application USB endpoint through its observed commands. A versioned profile/config service remains conditional on a qualified entry route. Define bounded envelope, operation identity, length/schema/integrity and error semantics offline now; defer transport claims and bootloader edits until independent recovery is demonstrated.
4. **Reduce flash wear by reducing full-image updates, not by unsafe loader shortcuts.** Each 64-byte packet entails a 256-byte row rewrite; the custom upload performs 324 such application writes plus START metadata. Four packets rewrite each application row four times. The legacy protocol has no safe host-addressed profile-only write or retry/resume. A future reachable application service with transactional row-aligned storage, or a preloaded profile catalog with separately qualified selection, is the appropriate optimization.
5. **Preserve full readback and no-retry behavior.** Do not remove the two-pass backup or verification to make the UI feel faster. Measure transport timing first. The transport inserts two 2 ms run-loop windows per report; its lower-bound contribution over 4,359 backup exchanges is roughly 17.4 seconds before flash/USB work. Any reduction needs late/duplicate-report tests. Use monotonic elapsed-time deadlines in preference to wall-clock time.
6. **Keep the device page simple and make recovery discoverable.** The secondary library and clear local-versus-verified states fit the user goal. Give connection, local-record failure, pending upload and installed setting distinct states; retain last-verified timestamps. Explain the next physical action and avoid generic “prepare/cancel backup” labels during programming.
7. **Expand camera and fault evidence selectively.** First custom candidate remains the confirmed Contax Zeiss 50 mm f/1.4. Qualification still needs A7C II startup, MF metadata display, actual EXIF, shutdown and repeat reconnection, followed by restoration/readback evidence. Biotar 58 mm f/2 is confirmed; the 28–70 zoom’s exact maximum aperture remains unconfirmed and its active focal length must be supplied manually. Neither metadata fixtures nor inherited AF tests qualify actual autofocus or passive-ring sensing.

## Remediation source re-review

A second offline source pass inspected the coordinating agent’s fixes after the findings above were delivered:

- `DeviceKit/USBConnectionSafety.swift:5–23` now selects the original canonical safety path; production `DeviceService` no longer relocates it with the library directory. Test isolation is an internal initializer. This addresses the alternate-directory P1 path while preserving the existing default marker location.
- `USBConnectionSafety.swift:27–41` adds a nonblocking `flock`. `NativeHID.swift` acquires it before loading blocked IDs and retains it through the operation and native handle scope. This addresses the identified cooperating GUI/CLI check/open race. The lock cannot constrain third-party tools; HID seizure and the physical-reconnect assertion still matter.
- `DurableFile` uses private temporary creation, checked `F_FULLFSYNC`, atomic rename and directory/ancestor synchronization. Fresh backup evidence is synchronized before START; UpdateStore publication uses the same writer. Recovery preservation now copies pending, applied and qualification records and synchronizes those copies. These changes address the visible durability omission; they do not constitute a destructive host-power-loss qualification.
- AppModel separates optional local-record failures from inventory, preserves recovery access, and tracks `pendingUpdateError` separately. On re-review I caught a residual issue where corrupt optional history still prevented stock recovery verification; the subsequent change gates `canVerifyUpdate` on pending-journal validity instead. The valid pending stock transaction can now reach verification and replace/remove the old optional records.
- Firmware-writing operations are marked explicitly, the button is named `Cancel USB Operation`, and cancellation presents a clear incomplete-application/recovery warning. This addresses the misleading cancellation path.

The new offline test source covers canonical safety across alternate libraries, rejection of a blocked synthetic connection before native access, competing lock ownership plus marker reload, and corrupt/private durable safety records. The coordinating agent is running the expanded suite; this reviewer’s independently executed result remains the 28-test baseline plus the sanitizer checks above. No new hardware operation is justified merely by this source re-review. Remaining useful regression work is UI recovery-state tests and fault-injected publication/abrupt-process tests.

No unresolved P1 objection was found in this bounded remediation source pass. Packaging/signature validation of the changed app and the current expanded test results belong in the implementation evidence before using that build.

## Snapshot identifiers

SHA-256 of reviewed source files, relative to `apps/macos/Sources`:

| File | SHA-256 |
| --- | --- |
| `DeviceKit/NativeHID.swift` | `ad4d79e3e0924444d61b18d2604380e3e5269b89b27374908bc29bdf7cc48b18` |
| `DeviceKit/Upload.swift` | `f71359ff3a15f78f454cdae66f08eee01bd74199f58baad42bd4f1bd7f4a4166` |
| `OpenLMEA9/AppModel.swift` | `a6948c8897a57d8ff1680380a2e6c9491a4d2b974d3bc537b973a44e86b8590a` |
| `OpenLMEA9/DeviceOverview.swift` | `ac46626ac85b28fd26eb0a52fbd617dd29c2f7756dc1afe15a70f5cc22eedde1` |
| `EA9CLI/main.swift` | `6ec8ee998110351b381daceb166c4e45099e1de454b0572fa7b05b6e26ea7f5c` |

No serial numbers or private backup contents are reproduced.
