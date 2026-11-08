# Verification

The bank migration suite adds production Swift transaction/recovery tests and
three isolated failing controls. Native-generated wire/journal bytes are also
fed into unchanged compiled 4.8 ARM startup code. The loader audit covers all
65,536 command pairs and both PA23 startup branches with a suffix-read control.
These are offline models; see [scope and evidence](bank-migration-2026-11-07.md).

    python3 scripts/test-bank-failing-controls.py --output artifacts/private/NEW-controls
    tools/rea-analysis/venv/bin/python scripts/audit-bank-metadata.py --output artifacts/private/NEW-audit
    # Export synthetic native vectors during a normal test run:
    OPENLENSADAPTER_BANK_VECTORS=/absolute/path/artifacts/private/NEW-vectors.json scripts/swift-local.sh test
    tools/rea-analysis/venv/bin/python scripts/test-bank-migration-arm.py --build BANK_BUILD --native-vectors PRIVATE_VECTORS --output artifacts/private/NEW-arm

`make test` builds and exercises the actual firmware C with supplied host UART,
CS/time and motor simulation, then runs the native Swift tests. It never opens
or enumerates the adapter.

Firmware checks cover validated aperture commands, recurring/status fields,
optional capture fields, fractional values, every unsigned aperture operand,
malformed frames and window padding, receive-during-transmit behavior,
interrupt-mask preservation and shutdown/new-session behavior. Removing the
receive hook or publishing inside the receive callback must fail their specific
assertions. Broad upstream protocol, servo, focus map/distance, buffered startup,
no-body and slow-body tests remain. The no-body tally expectation is adjusted
for a diagnostic-free release; the wait/frame-sync assertions remain intact.

```sh
python3 scripts/test-firmware.py
# Test the separate wide-range candidate:
python3 scripts/test-firmware.py --build artifacts/private/my-46-build \
  --output artifacts/private/my-46-tests
scripts/swift-local.sh test
# Offline 4.7 template and per-lens startup checks:
python3 scripts/build-firmware.py --lens-profile-template --output artifacts/private/my-47-template
python3 scripts/test-firmware.py --build artifacts/private/my-47-template --output artifacts/private/my-47-tests
python3 scripts/test-lens-profile-template.py --build artifacts/private/my-47-template --output artifacts/private/my-47-profile-tests
python3 tools/test_stock_recovery.py --key PRIVATE_KEY
# After building the custom example and default baseline:
python3 scripts/test-firmware-config.py --build artifacts/private/my-custom-firmware \
  --negative-control-build artifacts/private/my-45-build
```

Native tests exercise bounded upload, no reads after START, lost acknowledgements
and cancellation, durable journals and corruption, same-unit/new-connection
verification, protected data, exact-source admission and rollback, read-only
legacy compatibility, local library persistence, automatic discovery, preview
inhibition and truthful lens/range presentation. The archived journal test reads
its original fixture from the archive tag; it does not bundle retired images.

The 4.8 bank suite also runs in make test, or separately with make test-profile-bank.
It tests the actual C journal and boot consumer under ASan/UBSan, corruption,
prefix-cut erase/program models followed by reboot/retry, replay/no-op behavior,
uniform sixteen-row wear rotation and eight lens fixtures through the production
protocol. Broken record-CRC, erase-target and startup-aperture variants must fail
specific assertions. The compiled ARM NVM/startup and saved-loader instruction
checks are optional Unicorn tests, documented in the
[profile-bank record](profile-bank-2026-11-07.md). They use synthetic registers
and flash; they do not establish real power-loss behavior or camera stability.

The rename adds a legacy-storage/shared-lock compatibility check. Custom recipe
checks reject malformed names, invalid ranges, overflow, unknown fields and
published-version collisions. The custom example is ARM-built and its real C
responder is exercised under ASan/UBSan for name/checksum, focal fields, boot/range
and all 65536 aperture operands. Running it against the unmodified Biotar is a
failing control. No custom image is automatically admitted to the uploader.

Two clean builds reproduce working 4.5 and the separate 4.6 candidate. Native
Device, Library and USB panel previews are reviewed with all USB operations
inhibited. These software checks do not qualify camera acceptance. The owner
confirms AF, photos, aperture dial and shutdown on 4.5; exact mode/settings,
quantitative exposure/EXIF, extended endurance and other setups are unverified.
4.6 passed its separately authorized upload, physical reconnect and full-byte/
protected-data checks on November 7. The owner initially reported more hunting,
then improvement, and disclosed use of a heavier 35mm Distagon. Neither a
same-lens regression nor a mass-related cause is established. Actual settings
and remaining dial/capture/shutdown observations are pending.
[Installation record](evidence/biotar-46-install-2026-11-07.md).
