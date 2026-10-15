# Astra lane 25 — multi-boot diagnostic cohorts and semantic trust

**Offline host-only proposal; root integration pending.** The frozen public
decoder can call a CRC-valid but writer-impossible snapshot complete. This is a
reproduced interpretation defect, not an observed corruption on a real unit.
No production firmware change, new image/version, registry change or hardware
action is justified by this finding.

## Reproduction and scope

The actual public decoder baseline is
`scripts/startup_diagnostic_registry.py`, SHA-256
`e01c4b210577a22eec7cacd535a29ef31a272214247780e4432f7c958895ede8`.
The unchanged v1 parser script is SHA-256
`86357d857408608bb6e6a24cf568d0f67207ddf42109861f58af7d5a88ce5586`.
The production `startup_trace.c` in frozen 3.3, 3.4 and 3.5 has identical hash
`701fbaaaf330cf05401e00936128f0cff83ad0318381b84f9e436d430a89d1fd`.
The runner separately binds legacy 3.2 source, all four published image and
manifest pins, and each trace header. Current 3.5 is the frozen image
`04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632`
from `artifacts/private/absolute35a`.

A small inert-flash harness calls the actual production serializer. Eight
synthetic events produce summary slot 0 and four-event pages in slots 1 and 2.
Moving the second event page to slot 5, updating its encoded slot, and recomputing
its CRC produces an impossible serialization layout. The public decoder still
reports `persistedEvents: 8` and `eventSnapshotComplete: true`, because it sums
all later pages sharing `boot`. The same false completeness occurs through the
actual CLI with the exact published 3.3, 3.4 and 3.5 prefixes and version bytes.
The proposal reports four associated events, an inconsistent snapshot and an
out-of-plan event page. It does not call the missing page a successful write.

Another control removes the first cohort's event page, then relabels the second
cohort's event page with the first cohort marker and recomputes its CRC. The
frozen decoder borrows that page across the second cohort's summary and calls
the first complete. The proposal detects the out-of-plan page. Balanced total
counts in incorrectly sized/placed pages, impossible boot markers, record format
mismatch, impossible retention accounting, nonboolean flags, nonzero reserved
bytes, and RX/TX counts below surviving records also receive explicit trust
failures. A forged duplicate summary does not invalidate an otherwise consistent
earlier completed cohort; its own binding is inconsistent and cannot impose a
plan on the earlier records.

These controls intentionally recompute CRCs. They demonstrate missing semantic
checks and misleading output, not a probability estimate for random corruption
or proof that hardware produced any such bytes. CRC32 is not authentication.

## Minimal proposal

[`followup/25-diagnostic-cohorts`](../../firmware/upstream-hardening/followup/25-diagnostic-cohorts/README.md)
contains the isolated module, exact frozen baseline, guarded staged applicator,
production-source fixture and runner. The registry changes only by calling the
new module at its return boundary. Its staged SHA-256 becomes
`776c80f6cf7b9b60672d6053595dd56b9a6193ae40bcb0725750b2697e74a915`.
Existing test staging lists gain the new module dependency.

The audit applies v2's one-summary, summary-first, sealed snapshot rules only to
v2. It checks summary slot/boot binding, planned count against the remaining
append budget, dropped count against retention/budget omissions, event position
and per-page count, unused bytes and surviving RX/TX lower bounds. It annotates
`recordTrust` and `semanticIssues`; existing `state: valid` explicitly means
structural/CRC validity, not provenance or semantic trust. `eventSnapshotStatus`
separates complete, partial and inconsistent snapshots. `persistedEvents`
counts associated, consistent event records rather than arbitrary later pages
with the same marker.

A valid summary survives missing or torn event pages as partial evidence.
Intact later pages within its expected positions remain usable if an earlier
page is corrupted. An intact event page whose summary is damaged remains
visible as **unassociated**, not falsely rejected as writer-impossible. A new
boot may legitimately reuse the erased slot of a zero-byte failed write; its
records never count toward the prior boot's snapshot. Erased holes below the
highest occupied/torn page remain stranded, and the frontier stays unchanged.
V1 permits repeated summary/event flushes; it retains that layout and all its
existing decoded fields. No timestamp monotonicity is imposed because the
32-bit counter can wrap and recorded time is not a calibrated physical clock.

## Verification

Run:

```sh
python3 firmware/upstream-hardening/followup/25-diagnostic-cohorts/run.py \
  --output artifacts/private/astra-25-cohorts-repeat \
  --build artifacts/private/absolute35a
```

The completed suite covers:

- 448 exact production-serializer histories under ASan/UBSan, decoded 896 times
  across the published formats/versions. Histories include multiple boots,
  complete/zero-byte/torn writes, storage exhaustion and stranded erased holes.
- Six legitimate repeated-flush v1 summaries with unchanged legacy output.
- 19 synthetic semantic failing controls against the frozen decoder. They are
  all structurally/CRC valid in the baseline; several falsely report complete.
- 1,827 CRC-recomputed field-mutation decodes, covering both existing rejection
  boundaries and the newly checked writer invariants.
- Two changed-source controls: altering either the production C source or its
  header causes the runner to fail its published-source pin before decoding.
- Existing 25-case and 37-case pin/page/native-backup decoder suites pass against
  the staged proposal.
- Actual CLI comparisons for all four published images, retaining
  `installationVerificationPerformed: false`, `cameraAcceptanceProven: false`
  and zero hardware reports.

This supplements lane 08's passing storage-cut/writer tests with decoder
interpretation and multiple-cohort properties; it does not claim another NVM
writer certification. The [source-bound result](../../firmware/upstream-hardening/followup/25-diagnostic-cohorts/result.json)
from `artifacts/private/astra-25-cohorts-07/result.json` includes exact inputs, module
hashes and each control's frozen/proposed completeness output. Private binary
fixtures and synthetic full-flash containers stay under the lane's private
output directory. Public evidence contains only synthetic results and source
hashes.

## Boundaries

No enumeration, device open, HID report, updater, flash, motor action, app launch
or canonical Application Support mutation occurred. All published images,
manifests, registry pins and recovery remain unchanged. No raw unit bytes or
private camera exchange was read or published. Uploaded 3.2 still requires its
owner-confirmed physical reconnect and strict verification; this diagnostic
output cannot satisfy either gate. Prefix matching, writer consistency and
surviving terminal notes do not establish installation correctness, camera
acceptance, physical shutdown or the absence of an unrecorded fault.
