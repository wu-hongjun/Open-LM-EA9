# AF 3.7 targeted tracing milestone — October 15, 2026

The owner separately authorized offline motion/capture/shutdown tracing after
AF 3.6 failed capture and shutdown on the A7C II. The expired eight-hour campaign
remains closed and its heartbeat paused. This milestone does not authorize
hardware access or flashing; the owner will coordinate that separately.

The C foundation remains the pinned upstream implementation with the reviewed
3.6 changes. The actual 3.6 retained log establishes a sticky software wrong-way
inhibit and progress through UART-disable shutdown. It does not establish the
fault-time coordinates, whether a returned 0x0a was a raw capture echo or an
ordinary reply, the body's awaited completion, or shutdown past PA23. See the
[3.6 failure record](evidence/upstream-36-camera-failure-2026-10-15.md).

Three parallel gpt-6-astra scopes extend that evidence:

- Lane33: accepted motion command/target, existing encoder samples, retarget and
  rebase state, requested drive and a sticky first wrong-way/runaway snapshot;
  completion suppression/queue/return disposition stays separate from success.
- Lane34: raw versus ordinary capture ownership, immutable request identity and
  session at transmit START versus successful RETURN, owner phase transitions,
  and shutdown admission before the generic RX event.
- Lane35: a bounded v3 storage format, recent focused events, and terminal footer
  pages after the initial sealed snapshot for VD result, PA23 write, delay return
  and a later terminal fault.

Root owns integration, the host decoder and explicit new-version app/CLI action,
release evidence, preservation checks and commits. Lane reports distinguish
synthetic coverage, failing controls and physical unknowns. No UART frame, motor
polarity, origin, control gains, guard, timeout, factory recovery or published
candidate may be changed merely to make a test pass or fit the image.

The flash log range stays [0x9c00,0xa000): sixteen 64-byte append-only pages,
without runtime erase, retry or rewrite. Instrumentation adds execution and
terminal flash-write time; unchanged control decisions and synthetic wire bytes
do not establish physical timing equivalence. Missing/torn records cannot prove
no fault, a completed shutter request, a changed pin voltage or camera shutdown.
The next image is diagnostic and camera-unqualified, with a separate version,
digest and installation action; it is not presented as a shutter-freeze fix.

All seven Astra lanes33–39 completed and root integrated the reviewed composition.
The [final evidence record](evidence/upstream-37-tracing-2026-10-15.md) binds the
candidate, 23 passing acceptance groups, exact repeat build, 53 Swift tests,
signed app/native preparation and 131 preserved release/recovery/pin files.
[Candidate3.7](../firmware/candidates/3.7.0/README.md) and its
[future test procedure](upstream-targeted-trace-test.md) are ready for a separate
owner-coordinated flash. The adapter/cap, updater, motor and canonical Application
Support state were untouched; camera qualification and the failure cause remain
unresolved.

## October 17 hardware follow-up

The separately authorized 3.7 upload and strict reconnect verification passed.
The owner then reported some movement, no achieved focus and a freeze after one
photo. Read-only log retrieval and Astra40–41 review are complete in the
[camera failure record](evidence/upstream-37-camera-failure-2026-10-17.md).
The retained snapshot records `home-failed`, completed local capture/shutdown
transmissions and VD-timeout/PA23 footers. Failure phase and camera-freeze cause
remain unresolved. Further 3.7 camera trials are held; no replacement firmware
or timeout/polarity change was made from these observations.
