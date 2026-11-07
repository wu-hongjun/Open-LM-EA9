# Lens switching and flash endurance

The owner asked whether switching lenses reflashes the application and whether
flash endurance should change the design. Yes: the existing USB image-update
path and the offline 4.7 personalization prototype rewrite the application for
each explicitly requested update. Choosing the app dropdown writes only its local
choice on the Mac. USB discovery, CHECK, READ and verification do not erase flash.
No new profile firmware or settings operation was sent to hardware for this work.

## Endurance evidence

[Microchip's SAM D21/DA1 data sheet, DS40001882](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU32/ProductDocuments/DataSheets/SAM-D21-DA1-Family-Data-Sheet-DS40001882.pdf)
lists 25k minimum cycling endurance in its NVM characteristics table under the
specified conditions. Its cycle is an erase/write operation, not a whole-device
firmware update. Temperature, retention conditions and prior use matter; no
remaining-life counter was measured on this unit.

The pinned vendor loader's 0x0e78 flash-write helper performs a 256-byte
read/modify/erase/write for each 64-byte application report. Thus four reports
covering one row erase that row four times. A 20,480-byte upload has 320 reports
over 80 application rows, plus the START metadata write at 0x4000. This makes
frequent whole-image updates an unsuitable normal lens-selection mechanism.
It does not establish that the owner's existing adapter is near wear-out.
The original static evidence is retained in the
[archived loader-contract study](https://github.com/wu-hongjun/OpenLensAdapter/blob/9a6905cc99eb6ad62b7885a42a3eddf3d5f3071e/docs/usb-metadata-milestone.md).

The [official Techart manual](https://techartpro.com/wp-content/uploads/2023/01/User-Manual-LM-EA9.pdf)
documents using camera aperture selections and a capture to set focal metadata.
Those are application-level settings commands; they do not require a Mac
firmware upload. Our normal f/1.2–f/22 dial values currently mean reported
aperture, so stock command meanings must not silently replace them.

## Preferred product architecture

- Install one firmware containing a profile bank, with optical identity separate
  from hardware/motion tuning. Updating firmware or the bank is an explicit,
  infrequent operation.
- Select a profile in RAM. Persist only an actual committed change, not each AF
  movement, status frame, aperture click or repeated selection of the same lens.
- Store selection/configuration in a reserved, wear-leveled flash journal with
  schema, sequence, bounds, checksum and commit marker. Use redundant valid
  records so a torn write leaves the previous setting usable. SAMD21 EEPROM
  emulation still consumes flash; it is not unlimited physical EEPROM.
- Read the device-confirmed active profile back into the app. Keep the local
  dropdown choice distinct until the device acknowledges and verification passes.
- Add a deliberately separate camera-side selection command if needed; do not
  hijack ordinary aperture reporting. This is feasible application work, but its
  UI gesture and persistence are not implemented or qualified yet.

## USB-cap boundary and next investigation

With the unchanged cap the pinned stock bootloader samples PA23 high and remains
in its USB loop; it does not run the custom application. Its inspected command
dispatcher supports CHECK, READ and START/upload. There is no verified arbitrary
settings write or application launch command. Adding a USB driver or parameter
function only to the application does not make it reachable through that gate.

Investigate two distinct routes before claiming lightweight USB switching:

1. Audit a metadata-only mailbox using START without application pages. The
   inspected START writes its metadata row and arms the upload pointer, while
   application programming occurs on later reports. This is a static candidate,
   **not an approved or hardware-qualified settings operation**. Field ownership,
   complete erase footprint, zero-page/reset behavior, journal binding and strict
   application/protected-data invariance must all be established. Never assume
   apparently unused metadata or the six overread scratch bytes are free storage.
   Even if qualified, the loader's fixed metadata row remains a wear hotspot;
   an application wear-level journal cannot erase that cost.
2. Establish a qualified entry/transport for an application management service.
   This could support configuration-only writes to a dedicated journal, but the
   existing cap/loader does not provide entry. A bootloader change requires a
   demonstrated independent recovery route; USB backups alone do not qualify
   recovery from a damaged loader. No bootloader modification is authorized or
   performed by the app UI work.

Until a route is qualified, the prototype labels the fallback action **Update
lens firmware** and confirms that it rewrites the application. It must not
present that operation as a cheap parameter write or perform it on dropdown
selection. The normal product target is bank-plus-settings, not per-lens flashing.

A future settings operation must not silently fall back to a firmware rewrite.
Firmware updates remain a separately named, explicitly reviewed action.
