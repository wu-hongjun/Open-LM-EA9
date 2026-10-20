# Astra 46 — post-fault requests and shutter readiness

**No camera-shutter behavioral fix is established.** The exact AF3.8 foreground, homing, query and focus-entry paths continue to serve operand queries and shutdown after a drive-phase home failure, while refusing motor/servo execution. Raw readiness still disables periodic status until ordinary readiness re-arms it. The justified change is a narrowly scoped diagnostic: count motion requests consumed after a recorded home fault without inventing focus completion.

The [camera evidence](../evidence/upstream-38-camera-failure-2026-10-20.md) reports apparent acquisition for one photo, a motor reset, no further photos and normal shutdown. Actual focus mode and a saved first image remain unknown. Its raw readiness exchange occurs just before shutdown and cannot be identified as the first shutter event. Local TX return does not establish camera acceptance.

## Source binding and reproduced limitation

Frozen input is `artifacts/private/readiness38-repeat`, reconstructed from published AF3.8: image SHA-256 `8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9`, manifest SHA-256 `be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0`. The replay verifies all 49 source digests and the host shim before and after running. No frozen input is changed.

`home_service()` takes a command through `home_command()` before checking `HOME_FAILED`. Non-Stop requests can therefore be consumed and deferred after failure without entering `focus_exec()`. That entry also rejects an unreferenced or inhibited state. Neither path begins the servo collector. A zero AF3.8 motion collector consequently cannot distinguish absent requests from requests consumed while motion was inhibited.

A source-bound frozen control delivers three valid synthetic motion records after actual drive-phase failure. The requests are consumed, no motor/servo execution or completion event occurs, and byte115 remains zero; the prospective assertion that it retains three observed requests fails. This reproduces a missing discriminator, **not a demonstrated cause of the shutter block**.

Stop has separate established semantics. It is consumed, clears pending motion, changes the software home state to cancelled and posts its acknowledgement. A later Move can increment the attempt counter from one to two, but sticky inhibition makes the attempted home return immediately as failed: no second drive, brake, coordinate reset or position report occurs. Lane46 preserves this behavior and counts the later Move. Checking only the transient `HOME_FAILED` enum at command consumption would miss it.

## Transformation and ownership

The [applicator](../../firmware/upstream-hardening/followup/46-shutter-readiness/apply.py) pins the complete frozen `home_command()` body and both motion collector source/header files. It permits the disjoint lane45 home snapshot transformation elsewhere in `main.c`. Apply lane45 before lane46.

After a non-Stop command has been taken, the addition obtains the existing mutable collector backing storage and increments byte115 only when motor inhibition is set, the lane45 failure tail is initialized with tag `0x39`, and the byte is below255. It does not touch the first112 servo bytes. It reads no sensor or ADC, sends no message, adds no event and changes no command/session/pending state. No module API, protocol packet layout, query guard, readiness policy, timeout, gain or motor guard changes.

Lane45 initializes bytes112–143 only after failure cutoff. It owns the marker, phase, flags and timing/position/work fields, and initializes the counter to zero. Lane46 owns only the subsequent saturating byte115 update. The failure tail is diagnostic storage inside the already reserved32 bytes; the host decoder must interpret it under the new candidate version, preserving AF3.8 semantics.

The counter means **non-Stop requests actually taken by the foreground after the retained failure snapshot**. It is not a count of shutter attempts, received frames, all parsed requests, motor starts, completed focus moves, or accepted photos. Multiple received requests can overwrite the pending slot; session transitions can discard pending requests. Zero does not rule out those arrivals or commands before the fault. At255 the count is a lower bound. Since motor inhibition is sticky, later sessions may add to the same boot's record; no session attribution is implied. After shutdown/abort, the existing foreground guards prevent further service.

## Offline checks

The [runner](../../firmware/upstream-hardening/followup/46-shutter-readiness/run.py) compiles actual source-extracted foreground/home/query/focus-entry bodies together with the production parser, owner, session, shutdown, query mapping and trace units under Clang ASan/UBSan. Synthetic UART/VD, encoder and time boundaries replace hardware. Time advances through the independent `millis()` mock; ADC sampling has no scheduling role, supporting lane48's telemetry removal.

Frozen3.8 passes six downstream contracts: no motion, refused Move/Scan/Drive, repeated raw-readiness/ordinary-rearm cycles, query publication session cut, query publication shutdown cut, and Stop followed by Move. The additional missing-counter control fails at its specific expected assertion.

The lane45+46 composition passes ten cases: those six contracts plus explicit observed-count verification, saturation after270 consumed requests, uninitialized-tail rejection and non-inhibited-tail rejection. The raw case performs three complete cycles, including a consumed Move while periodic status is disabled, a query retained during silence, and its correct answer after ordinary re-arm. Every safety check requires no extra drive, no brake, no coordinate reset, no position report, no Move completion and an untouched first112 servo bytes. Stop acknowledgement is checked independently.

Seven source mutants must fail at the relevant assertion: reintroducing query inhibition; fabricating a Move completion; re-enabling status after raw readiness; suppressing the counter; allowing counter wrap; removing the marker guard; and removing the inhibition guard. The receipt records exact predicates, exits, original source pins and the production source digests used by each variant. Host test accessors and boundary instrumentation are applied only to private copies.

The [sanitized replay receipt](../../firmware/upstream-hardening/followup/46-shutter-readiness/results.json) is generated by the default frozen/composed run. `--candidate PRIVATE_BUILD --output PRIVATE_OUTPUT` additionally verifies that candidate's image, manifest, all source hashes and shim, tests its exact composition, retains frozen controls, and writes its receipt only under the requested private output. It does not overwrite the baseline receipt.

The standalone lane46 [ARM measurement](../../firmware/upstream-hardening/followup/46-shutter-readiness/measure.py) recompiles and links every frozen production unit with the pinned compiler/flags. It adds36 image bytes, reducing margin336→300, with no additional static RAM. This is lane46 alone; lane45's snapshot and lane48's savings require a separate complete composition measurement. Private result: `artifacts/private/astra46-size1/size.json`.

## Policy comparison and remaining limits

The pinned upstream focus entry refuses operation before `g_homed`; it provides no basis to invent completion after failed reference. The original upstream homing timeout behavior is not imported to bypass the hardened reference requirement. The existing [Astra43 policy study](astra-43-capture-status-2026-10-19.md) and the fresh original-stock raw-readiness probe documented in the camera evidence both retain silent/init mode after raw readiness and ordinary-readiness re-arm. The new replay exercises this policy through actual parser/owner paths; no speculative status re-enable is included.

This suite uses synthetic valid frames and controlled boundary timing. It does not reproduce camera acceptance, physical end-stop arrival, noise, polarity, stiction, electrical elapsed time, the owner's exposure/focus settings or the saved-photo sequence. Homing-inhibited focus provides a software explanation for unresponsive focus, but the body's shutter decision remains unobserved. The highest-value next discriminator is the combined failure-phase snapshot and count: it can separate later consumed focus requests from a run with no such consumed requests, while retaining evidence about the failed phase's timing/work/position. It cannot establish optical acquisition or identify a shutter press by itself.

All work was offline. No hardware access, firmware transfer, application/updater launch, canonical host-state access or Git mutation was performed by this lane.

## Final AF 3.9 integration and host review

The exact final production replay passes ten cases and seven rejecting mutants,
retaining six frozen3.8 contracts and its specific missing-counter control.
App0.22.0/build29 adds explicit fixed50mm prepare/apply and guarded UI routes;
53 named Swift tests across20 variants and nine isolated native prepare routes
pass. The signed package is verified without launch. Independent decoder review
closed exact poll-budget validation and initial-or-last-threshold anchor wording;
307 checks pass. The [sanitized host receipt](../evidence/upstream-39-host-2026-10-20.json)
records pins/results. Camera acceptance, physical homing and shutter repair remain
unproven. No device or canonical host state was accessed.
