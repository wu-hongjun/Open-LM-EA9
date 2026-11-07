# OpenLensAdapter icon

Original vector artwork drawn by **Claude Opus 5.5** through Claude Code using
the exact model ID `claude-opus-5-5`. It depicts two metal mount rings joined by
three teal bayonet lugs. No external artwork, fonts or SF Symbols are used.
The generated source was inspected before execution and the rendered master
was visually reviewed.

The editable source is [create-app-icon.swift](../../scripts/create-app-icon.swift).
`provenance.json` pins that source and the 1024px transparent PNG master.
Packaging regenerates all ten macOS PNG renditions and converts them to ICNS:

```sh
swift scripts/create-app-icon.swift artifacts/private/MyIcon.iconset
iconutil -c icns artifacts/private/MyIcon.iconset -o artifacts/private/AppIcon.icns
```
