# Astra 39 — targeted trace decoder and host review

Offline source and synthetic-fixture review, 2026-10-15. The parent integrated the proposed decoder fixes; the integrated decoder passes all 60 independent adversarial controls. A separate disposable-repository CLI suite passes 27 candidate, manifest, registry, immutable-prefix, native-backup and size controls. The parent reports that the existing 49-case v1/v2 compatibility suite also passes.

No USB, HID, updater, app launch, real camera backup, canonical Application Support state, or commit was accessed or changed by this review. These checks do not qualify camera behavior or authorize flashing.

## Exact inputs and test evidence

- Candidate 3.7.0 image SHA-256: `6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5`.
- Published manifest SHA-256: `15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b`.
- Compiled writer synthetic fixture SHA-256: `5ebc0a86d83da1b9b0f6d2322b744a4acefd851d2f97e1c0bf2072e868ee0d5b` (`artifacts/private/trace35-suite8/synthetic.bin`; no real camera data).
- Reviewed initial decoder SHA-256: `53bbd85b90964fa108c3b0eb65e09455123789c528d9562c04b94bc2de5c5a57`.
- Integrated decoder SHA-256: `7662e1472dfd4db179368d46d8cff64cdb5462a587d11b66ee3dda1ee9c2cb83`.
- Tests, proposal, baseline results, proposal results, integrated results and registry results: `firmware/upstream-hardening/followup/39-decoder-host-review/`.

The 60-case negative controls were written from the writer's source invariants, with repaired CRCs for semantic mutations. The initial decoder passed 11 and failed 49; the integrated decoder passes 60. This distinguishes semantic detection from the existing byte-flip CRC sweep. The source basis is followup 35's schema and `append`/`st_flush`/`st_terminal`, followup 33's motion structure and writer, and the final followup 36 capture helper in the exact candidate.

## Findings resolved

1. **P1: terminal association could recover across missing or malformed preceding records.** The writer latches append failure and never writes a later page in that cohort after failure. A decoder cannot establish the terminal sequence through an erased/CRC-invalid planned snapshot page, a different cohort occupying a planned slot, or an erased/invalid preceding footer. Previously such a later footer could remain `writer-consistent`; a malformed footer's kind could also seed the next valid transition. The fix retains each CRC-valid local payload, marks association gaps, and admits only the contiguous usable terminal prefix after a complete snapshot into `terminalFooters`. Missing records remain unknown evidence; they do not establish an actual write failure, physical shutdown, or successful motion.

2. **P2: extra same-cohort child outside the plan could coexist with `snapshotStatus=complete`.** A shortened valid snapshot plus an extra same-cohort event page is impossible under the plan. The fix marks the cohort inconsistent rather than allowing the summary to say complete. Invalid motion payloads now also clear `motionSnapshotComplete`.

3. **P2: unsaturated motion cursor validation covered only counts below four.** The writer increments the ring cursor modulo four on every sample and saturates the count at 65535. Thus `sampleNext == count % 4` is required for every count below 65535; once saturated every cursor is possible. The fix uses that exact condition. Positive controls retain all four saturated cursor states, order samples by the cursor, and preserve timestamps crossing `UINT32_MAX` without treating wrap as a clock fault. Additional source-bound checks reject unknown retained sample state bits, nonzero unused sample slots, and a last-sample timestamp that differs from the newest retained sample.

4. **P2: focused-event retention rules and field semantics were missing from decoder output.** The writer discards OWNER_CS/OWNER_PHASE without RAW and TX_START/TX_RETURN without CONTROL or SHUTDOWN. CRC-repaired records violating those rules are now inconsistent. Kind-specific fields distinguish control-TX owning-request sequence from non-control TX transmitted-frame sequence, COMPLETE's session-still-valid bit from its send-return result, OFFER acceptance, and shutdown admission. Phase events remain software boundaries, not atomic owner snapshots. None of these fields establishes camera acceptance.

## Host and identity review

`autofocusTargetedTrace` is a separate 3.7.0 variant and resource with an exact template hash. The existing `autofocusStartupHandoff` enum case, 3.6.0 resource/hash, command mapping and held app action remain separate. The explicit `prepare-trace-upstream`/`apply-trace-upstream` commands map to 3.7; existing handoff commands still map to 3.6. The added app action calls the new variant directly, and merely discovering a device does not invoke it. The app remains subject to its existing explicit Apply confirmation.

The new variant declares `supportsLensProfileChanges=false`, so the existing exact compiled-profile equality check rejects edited or different lens profiles before an upload begins. The ordinary Apply action remains disabled for unsupported installed runtime profile changes. The new workflow test source checks the old hold, explicit new candidate availability, rejection of the 85mm profile, the 3.7 workflow state and unknown actual iris position. Parent-run Swift tests are the execution evidence for those app assertions; this review did not launch the app. Info.plist identifies version 0.20.0, build 25.

The 27 CLI controls use a disposable copied repository and newly generated 128 KiB flash. They verify exact candidate and published manifest pins, independent registry image/manifest/prefix pins, descriptor range/version/hash checks even after repairing the manifest digest, immutable-prefix endpoints, candidate code/tail/size tampering, native backup pass/count/hash checks, and input size limits. Every rejected case exits before producing decoded JSON. The mutable diagnostic tail remains accepted and locally decoded as intended. Registry pins are repository trust anchors, not cryptographic authentication of the registry itself or proof that firmware is installed.

## Limits

The decoder distinguishes structural/CRC validity, checked writer consistency, and association. Its invariants are not an exhaustive proof that every possible payload was produced by the firmware. Sealed snapshot completeness describes retained software records. VD, PA23, tail-delay and terminal-fault records are software observations only. Missing data, a complete trace, or a TX return cannot prove physical lens motion, power removal, shutter success, camera acceptance, or the cause of the reported freeze.
