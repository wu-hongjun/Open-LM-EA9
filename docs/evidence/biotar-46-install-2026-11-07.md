# Biotar 58mm wide aperture-dial trial: 4.6.0

The owner authorized uploading 4.6.0 for the Zeiss Jena Biotar 58mm f/2 and
testing the reported f/1.2–f/22 dial range on the Sony A7C II. The physical iris
remains controlled by the lens ring; the compiled lens specification and startup
report remain 58mm/f/2. This does not give the physical lens an f/1.2 opening.

## Upload and reconnect verification: passed

Preflight found one LM-EA9 descriptor and no running updater or OpenLensAdapter
process. The previous 4.5.0 upload was already verified. The signed native CLI's
offline preparation produced the exact 20,480-byte release image:

`feeef5558f053f150923791af935953df112350519e08bad86712fde6901c318`

Public stock-recovery checks passed and the private original recovery key remained
present. Private transaction state was snapshotted before the update.

`ea9ctl apply-wide-aperture --idle` completed a fresh two-pass flash/auxiliary
backup with 4,359 read exchanges, admitted only the exact pinned 4.5.0 application
and existing same-unit qualification, then completed START and all 320 pages.
Upload finished at **17:31:12 UTC on November 7, 2026** (12:31:12 PM EST).
No post-upload USB report was sent before the owner confirmed a physical
unplug/reconnect through the cap with both apps closed.

`ea9ctl verify --idle` completed another matching two-pass backup and strict
verification at **17:33:58 UTC** (12:33:58 PM EST). A separate offline audit of
the published backups confirmed the same unit on a new connection, all 20,480
application bytes, all 58 planned metadata bytes, and unchanged boot code, saved
records, upper flash, user row, calibration and device ID. The six established
loader-scratch bytes at `0x403a..0x403f` are excluded. NVM geometry qualified and
its observed status snapshot also matched; the register snapshot does not prove
restoration of lock state. [Sanitized result](biotar-46-install-2026-11-07.json).

## Camera test: increased AF hunting reported

After verification, the owner was guided through one powered cycle: A exposure
mode, explicit MF/Pre-AF Off where available, dial through f/1.2, f/2, f/5.6 and
f/22 and back to f/2; one matched camera/lens f/2 photo and one matched f/5.6 photo;
then, if normal, a single AF-S focus/photo at f/2 and shutdown. Stop conditions
were supplied for freeze or abnormal drive. The owner then reported that
"the autofocus hunts a lot more than before" and asked whether this was intentional.
Increased hunting is not intended. The owner was asked for the already-observed
camera f-number, physical ring position, focus mode, saved photo and shutdown
result, without requiring another attempt. Those details and the actual dial
endpoints remain unknown. This is a possible regression, not a controlled A/B
comparison or a successful acceptance test. 4.5.0 remains the working baseline.

An offline source and ELF/binary comparison found exactly 13 changed image bytes.
Only `emount.h` differs in the release source manifests. The changed instruction
bytes belong to `reported_aperture_offer`; changed initialized data belongs to
`em_msg_05` and `em_msg_08`. They implement the accepted range and advertised
maximum/minimum descriptors, including the maximum BCD f-number. AF command,
motor, servo, focus mapping, timing and capture/shutdown sources are unchanged.
The camera now sees an advertised maximum of f/1.2 while the physical Biotar is
f/2. A body-side response to those changed descriptors is a hypothesis; no Sony
AF decision trace establishes it as the cause. No additional firmware was flashed.

Release diagnostics remain compiled out, and the USB cap does not expose the
volatile Sony-dial selection after power-off. No runtime camera log or exposure
measurement is claimed. The immutable preparation manifest is retained unchanged.

## Artifact cleanup

At the owner's additional request, retired outputs and the old Swift cache were
archived outside the repo with no permanent deletions. Current install evidence,
the signed app/CLI, all profiles, stock recovery, published images and reference
sources remain available. [Retention and recovery details](../artifact-retention.md).
