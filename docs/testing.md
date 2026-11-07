# Verification

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
python3 tools/test_stock_recovery.py --key PRIVATE_KEY
```

Native tests exercise bounded upload, no reads after START, lost acknowledgements
and cancellation, durable journals and corruption, same-unit/new-connection
verification, protected data, exact-source admission and rollback, read-only
legacy compatibility, local library persistence, automatic discovery, preview
inhibition and truthful lens/range presentation. The archived journal test reads
its original fixture from the archive tag; it does not bundle retired images.

Two clean builds reproduce working 4.5 and the separate 4.6 candidate. Native
Device, Library and USB panel previews are reviewed with all USB operations
inhibited. These software checks do not qualify camera acceptance. The owner
confirms AF, photos, aperture dial and shutdown on 4.5; exact mode/settings,
quantitative exposure/EXIF, extended endurance and other setups are unverified.
4.6 needs a separate flash/reconnect/full-byte check and camera test.
