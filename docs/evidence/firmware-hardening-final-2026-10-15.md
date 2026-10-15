# Eight-hour firmware hardening — final status

**The authorized time window is closed. The stable, factory-parity firmware
goal was not achieved. AF 3.6 failed A7C II capture/shutdown and remains held.**
The heartbeat is **PAUSED**. Completed source changes, tests, diagnostic evidence
and app guidance are preserved; this closeout starts no further firmware work.

The window was October 15, 2026, **00:55:51–08:55:51 America/New_York**
(04:55:51–12:55:51 UTC). The closing heartbeat arrived at 09:01:03 EDT;
the native automation tool confirmed pause at **09:02:16 EDT**
(13:02:16.178 UTC). Closing administration occurred after the deadline; no new
firmware change, test campaign, hardware operation or agent lane was started.
The automation's name, prompt, schedule and target were preserved.
[Machine-readable closeout](firmware-hardening-final-2026-10-15.json).

## Delivered and verified

| Area | Result and evidence |
| --- | --- |
| Parallel audit | 32 numbered scopes: 28 completed Astra reviews, three interrupted Astra scopes continued by root, and one root-only extension. The requested minimum ten Astra lanes was exceeded. [Matrix and individual dispositions](../audits/astra-hardening-campaign-2026-10-15.md). |
| Modular upstream C | Separately frozen 3.3–3.6 integrate reproduced frame/operand admission, capture/shutdown ownership, bounded transport, homing readiness, query capacity/service, coordinate arithmetic, shared-sample target handoff, sampled deadlines and startup EIC ownership fixes. [3.3](upstream-33-hardening-2026-10-15.md), [3.4](upstream-34-bounded-2026-10-15.md), [3.5](upstream-35-absolute-2026-10-15.md), [3.6](upstream-36-handoff-2026-10-15.md). |
| Software acceptance | Repeat image/manifest/patch builds, production-path regressions with frozen failures, sanitizer controls, compiled writer/stack/order checks and decoder checks passed within their documented cuts. Latest app passes all 53 Swift tests. These passes do not override the failed physical trial. |
| Diagnostics | Multi-boot cohort checks reject writer-impossible completeness claims. Actual 3.6 read-only recovery preserves 13 valid pages and 48 retained first/last events with 6,429 evictions. Real frames, payloads, identifiers and raw dumps remain private. |
| Host app | Signed app0.19.1/build24 marks installed 3.6 held and disables its ordinary installation action. Backup/recovery remain available; CLI bytes and transport guards are unchanged. The workflow control fails against the prior app in three intended assertions, then the 53-test suite passes after the fix. |
| Original factory research | New boot-entry and terminal-tail instruction evidence refine mask/UART/sleep contracts. The old shutdown replay's pre-format GPIO observation was corrected to distinguish formatted UART bytes; historical JSON/pins remain exact. [Boot audit](../audits/astra-24-boot-entry-2026-10-15.md), [tail audit](../audits/astra-31-factory-shutdown-tail-2026-10-15.md). |
| Preservation | All 60 prior release/recovery/pin artifacts and the current 3.6 image/manifest/resource remain exact. Original stock1.8 application and encrypted same-unit recovery are retained; keys remain private. No existing image was overwritten under its version. |

3.6 is 20,480 bytes, SHA-256
`d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f`.
Its code/data ends at 0x9af4, with 268 bytes before diagnostics, 3,064 static RAM
bytes and 8,192 reserved stack bytes. The 1,560-byte compiled stack envelope is
conditional; physical high-water, IRQ execution and timing remain unmeasured.
The controller remains upstream C, with the fixed original 50mm f/1.4 profile.
Runtime lens-library edits cannot change this image. Actual physical iris stays
Unknown; application USB management without reflashing remains future work.

## Actual hardware outcome

Scheduled runs and agents stayed offline. In separate owner-coordinated turns,
3.2's pending strict verification passed at 08:02:46 EDT. The authorized 3.6
upload completed at 08:05:50 EDT, and its own physical-reconnect verification
passed at 08:23:54 EDT. Complete application/metadata and protected-data checks
passed without relaxing the blank diagnostic tail or editing safety state.
[Installation evidence](upstream-36-upload-2026-10-15.md).

The owner then reported inability to take a photo, slight focus movement,
shutter-press camera freeze and shutdown nonresponse. Actual focus mode,
aperture, Pre-AF, half/full press and battery-removal action remain unknown.
This is a failed capture/shutdown trial; it cannot be labeled a successful MF
cycle, controlled AF-S comparison or optical accuracy result.

After the reported computer return, a native read-only same-unit backup
completed at 08:30:35 EDT. Only 830 bytes inside diagnostic storage changed;
all other flash and protected auxiliary data match the strict pre-camera
readback. No subsequent flash, restore or camera retrial was requested by the
agent. The last recorded firmware is 3.6, held; the last reported adapter
location is the USB cap. This closeout performs no fresh connection check.

The trace records historical connected/handshake progress, a sticky
`servo-wrong-way` inhibit, and later successful-return shutdown echo followed by
the UART-disable/flush marker. The inhibit suppresses further motion/completion,
but its fault-time sensor trajectory and relation to shutter press are absent.
The marker precedes PA23 and the sealed snapshot hides later tail faults.
Neither reply delivery nor physical camera shutdown is proved. The shutter
root cause remains unresolved. [Failure record](upstream-36-camera-failure-2026-10-15.md)
and [independent source/trace review](../audits/astra-32-af36-capture-failure-2026-10-15.md).

## Remaining work and next evidence gate

Factory reconstruction is partial: 235 application functions are inventoried,
with a 41-entry semantic-model union and bounded original-instruction AF,
sensor/origin, boot and shutdown comparisons. That is not a complete firmware
reconstruction, physical controller integration or factory parity. Current C
control remains upstream; earlier factory-derived wrappers did not establish
camera acceptance. [Reconstruction status](../reverse-engineering/status-2026-10-15.md).

Before another remedy claim, obtain fault-time motion evidence (accepted target,
leg start, encoder history, drive sign and retarget/rebase state), capture
ownership/handshake evidence tied to known camera settings, and evidence beyond
the recorded UART-disable boundary. Preserve motor cutoffs and bounded waits;
do not infer polarity, origin or gains from the single sticky fault. Any later
instrumentation must pass layout/storage and production-path gates as a new
candidate version. It requires a separately coordinated upload and strict
verification before any new camera trial. This is a future scope, not a request
to repeat 3.6 or restart this expired campaign.
