# App reference photographs

Collected October 10, 2026. The app bundles nine original photographs: the
LM-EA9 and all eight lenses. Images are loaded from the application resource
bundle with `NSImage`; normal use does not request images over the network.
SwiftUI scales each original to fit. No crop, background removal, retouching or
generated replacement was applied.

[assets.json](assets.json) records each source page, image URL, depicted model,
author/source credit, retrieval date, byte count, SHA-256 and license observation.
The app bundles an identical `photo-credits.json` and exposes **Open LM-EA9 →
Photo Credits…**, also available in the Lens Library options menu.

| Photograph | Source |
| --- | --- |
| LM-EA9 | [Shoten Kobo's TECHART distributor announcement](https://prtimes.jp/main/html/rd/p/000000199.000071960.html) |
| Contax Zeiss 28mm f/2 | [Kamerastore Distagon](https://kamerastore.com/products/carl-zeiss-28mm-f2-distagon-t-contax-yashica) |
| Contax Zeiss 35mm f/1.4 | [Kamerastore Distagon](https://kamerastore.com/products/carl-zeiss-35mm-f1-4-distagon-t-ae-contax-yashica) |
| Contax Zeiss 50mm f/1.4 | [Kamerastore Planar](https://kamerastore.com/products/carl-zeiss-50mm-f1-4-planar-t-contax-yashica-t99266) |
| Contax Zeiss 85mm f/1.4 | [Kamerastore Planar](https://kamerastore.com/products/carl-zeiss-85mm-f1-4-planar-t) |
| Contax Zeiss 100mm f/2.8 macro | [Kamerastore Makro-Planar](https://kamerastore.com/products/contax-100mm-f2-8-makro-planar-t-1) |
| Contax Zeiss 135mm f/2.8 | [Kamerastore Sonnar](https://kamerastore.com/products/carl-zeiss-135mm-f2-8-sonnar-t-ae-contax-yashica) |
| Contax Zeiss 28–70mm | [Kamerastore Vario-Sonnar](https://kamerastore.com/products/carl-zeiss-28-70mm-f3-5-4-5-vario-sonnar-t-contax-yashica) |
| Zeiss Jena Biotar 58mm f/2 | [Alf Sigaro / Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Biotar-F2-58mmByAlfSigaro.jpg) |

These are model references, not photographs of the owner's individual equipment.
Dealer images can show production variants and inventory stickers. The zoom
photo depicts f/3.5–4.5; the owner's nominal f/3.5 is retained without inventing
a variable-aperture table. The owner confirmed the Biotar's engraved focal
length is **58mm f/2**. Its old identifier `zeiss-jena-biotar-55-f2` remains
stable so existing libraries and local selections continue to resolve.

The Biotar image is licensed [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/)
by Alf Sigaro. An open redistribution license was not identified for the dealer
and distributor photos. They are local prototype reference assets; public app
distribution needs cleared or replacement photographs. Photo downloads and
HTML research snapshots are Git-ignored. Attribution and hashes are tracked.

## Local copies and reproduction

Original files live in `references/visuals/photos/`. Identical copies are bundled
from `apps/macos/Sources/OpenLMEA9/Resources/Photos/`. To reconstruct missing
downloads on a checkout with network access, run from the repository root:

```sh
python3 references/visuals/fetch_assets.py
python3 references/visuals/fetch_assets.py --verify-only
./scripts/build-macos-app.sh
```

The script accepts only the recorded HTTPS URLs and verifies exact bytes before
publishing a local copy. Changed remote bytes fail verification and need a
reviewed manifest update. Existing matching originals require no download.
`--verify-only` performs no network requests. Packaging compares the canonical
credit catalogue with the app's copy and verifies all asset digests.

`research-pages.json`, `discovered-images.json` and `optyczne-page.html` retain
intermediate discovery evidence, including failed Techart/older dealer URLs.
They are not the final asset catalogue; `assets.json` identifies the images
actually used.
