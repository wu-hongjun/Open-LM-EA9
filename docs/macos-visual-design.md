# Native app visual design

Version 0.2.0, October 10, 2026. This implements the requested small, attractive
utility around the LM-EA9 and the owner's Sony A7C II lens collection.

## Main flow

**Launch → Device → Lens Information → Lens Library → Prepare lens → Device.**

Device is always the starting tab. A large LM-EA9 photograph sits alongside
connection status and dated firmware information. The Lens Information card
contains either a small preview of the collection or the locally prepared lens.
The main button opens the secondary Lens Library tab.

Lens Library presents eight photographed cards with readable focal length,
maximum aperture and optical family. **Prepare lens** saves a local choice and
returns directly to Device. **Change lens** reopens the collection. Clicking
a photograph or its sliders opens a compact metadata editor; **Save Lens**
persists edits locally. Import/export is in the library's options menu and
File menu. There is no additional setup screen or account.

The stock loader's USB interface supplies no supported current-lens or
profile-apply operation. Therefore Device explicitly says **Adapter setting ·
Unavailable through USB**, and a local selection says **Prepared on this Mac ·
Not applied**. Selecting a lens must never imply that the ring has changed.
The future management backend should replace this state with a real profile
read, explicit apply, and verified read-back once application USB reachability
and configuration writes have been qualified.

## Presentation

- Warm off-white canvas, white rounded photo surfaces, charcoal actions and a
  restrained green connection indicator; an app-only light appearance.
- Serif headlines with native system text and rounded numeric lens labels.
- A compact top navigation with Device first and Lens Library second.
- Nine bundled photographs, with local-only image loading and no tracking or
  dependency on remote image hosts during use.
- Native controls and file panels; labeled icon buttons, text alongside status
  colors, and decorative photos hidden from accessibility to avoid duplicate
  lens announcements. The active tab exposes a selected accessibility trait.
- Scrollable content and an adaptive card grid; minimum window 920 × 680,
  default 1130 × 780. The editor and utility sheets fit within that minimum.

USB backup and manual firmware reads are under **USB tools…**. The existing
idle/reconnect prerequisite, qualification, cancellation and persistence remain
in place. Opening the sheet sends no HID reports. Firmware on Device remains a
dated last-read observation; startup and connection refresh read descriptors
only. Connection refresh is manual in this prototype; automatic hotplug and
full VoiceOver qualification remain follow-up work.

## Local data and source accuracy

`LensCore/PreparedLensStore` stores only a profile ID in `prepared-lens.json`,
separately from the versioned metadata library. It cannot read or mutate adapter
configuration. An imported library that removes that ID clears the visible
choice. A malformed or newer choice record is ignored and preserved.

The confirmed Biotar is **58mm f/2** in new seeds. Existing libraries are not
silently reseeded or migrated. The owner's saved Biotar is corrected using the
normal editor; its original stable ID remains unchanged. Other user profiles
and unknown manual settings are preserved. The zoom photograph's f/3.5–4.5
variant is disclosed in its detail editor and credits; the owner's nominal
f/3.5 stays unchanged.

Source URLs, attributions, rights observations and file hashes are in
[the visual reference catalogue](../references/visuals/README.md). A **Photo
Credits…** sheet makes these accessible inside the app. Public distribution
needs cleared or replacement dealer/distributor assets; this build is a local
development prototype.

The UI is split into `VisualDesign.swift` (palette, photo catalogue, shared
components and credits), `DeviceOverview.swift` (overview and USB tools), and
`LensGallery.swift` (gallery/editor). `AppModel` owns saved/draft state and local
preparation. `DeviceKit` retains the separately qualified transport service.

See [validation](evidence/macos-visual-redesign-2026-10-10.md), the
[user guide](macos-prototype.md), and [data formats](macos-prototype-formats.md).

## Device workflow follow-up: 0.5.0

The main screen now pairs a compact adapter photo/name card with dated firmware
information, followed by the last USB-verified lens photograph and a native
profile dropdown. The dropdown, Apply/Verify action and connection acknowledgement
fit together in the default window. The secondary photo gallery/editor remains
available through Lens Library and Edit library. Connection and local history
refresh automatically without HID feature reports. The 85mm preparation was
exercised and restored to 50mm on the connected unit without uploading.
See [workflow details](macos-device-workflow.md) and
[validation evidence](evidence/af-reconciliation-2026-10-10.md).
