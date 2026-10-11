#!/bin/bash
set -euo pipefail
ea9_root="$(cd "$(dirname "$0")/.." && pwd)"
# The canonical inventory is reviewed outside the application. Packaging must not silently use a stale copy.
cmp "$ea9_root/profiles/requested-lenses.json" "$ea9_root/apps/macos/Sources/LensCore/Resources/requested-lenses.json"
cmp "$ea9_root/references/visuals/assets.json" "$ea9_root/apps/macos/Sources/OpenLMEA9/Resources/photo-credits.json"
python3 "$ea9_root/references/visuals/fetch_assets.py" --verify-only
"$ea9_root/scripts/swift-local.sh" build -c release
ea9_bin="$("$ea9_root/scripts/swift-local.sh" build -c release --show-bin-path)"
mkdir -p "$ea9_root/dist"
ea9_destination="$ea9_root/dist/Open LM-EA9.app"
ea9_stage="$(mktemp -d "$ea9_root/dist/.ea9-app.XXXXXX")"
# Build and verify the complete bundle before replacing the last usable build.
trap 'if [[ -d "$ea9_stage/previous.app" && ! -e "$ea9_destination" ]]; then
    printf "Previous usable app retained at %s\n" "$ea9_stage/previous.app" >&2
else
    rm -rf "$ea9_stage"
fi' EXIT
ea9_app="$ea9_stage/Open LM-EA9.app"
mkdir -p "$ea9_app/Contents/MacOS" "$ea9_app/Contents/Resources"
cp "$ea9_bin/OpenLMEA9" "$ea9_app/Contents/MacOS/OpenLMEA9"
cp -R "$ea9_bin/OpenLMEA9_DeviceKit.bundle" "$ea9_app/Contents/Resources/"
cp -R "$ea9_bin/OpenLMEA9_LensCore.bundle" "$ea9_app/Contents/Resources/"
cp -R "$ea9_bin/OpenLMEA9_OpenLMEA9.bundle" "$ea9_app/Contents/Resources/"
cp "$ea9_root/apps/macos/Info.plist" "$ea9_app/Contents/Info.plist"
# Publish a signed new inode, preserving any running CLI's mapped executable.
cp "$ea9_bin/ea9ctl" "$ea9_root/dist/.ea9ctl-next"
codesign --force --sign - "$ea9_root/dist/.ea9ctl-next"
codesign --verify --strict "$ea9_root/dist/.ea9ctl-next"
mv -f "$ea9_root/dist/.ea9ctl-next" "$ea9_root/dist/ea9ctl"
# SwiftPM's standalone CLI resolves bundles beside its executable. Keep the
# DeviceKit template and LensCore seeds available outside the app bundle too.
for ea9_bundle in OpenLMEA9_DeviceKit.bundle OpenLMEA9_LensCore.bundle; do
    if [[ -e "$ea9_root/dist/$ea9_bundle" ]]; then
        rm -rf "$ea9_root/dist/$ea9_bundle"
    fi
    cp -R "$ea9_bin/$ea9_bundle" "$ea9_root/dist/"
done
ea9_iconset="$ea9_root/apps/macos/.build/AppIcon.iconset"
env CLANG_MODULE_CACHE_PATH="$ea9_root/apps/macos/.build/local-cache/modules" \
    SWIFT_MODULECACHE_PATH="$ea9_root/apps/macos/.build/local-cache/modules" \
    swift "$ea9_root/scripts/create-app-icon.swift" "$ea9_iconset"
iconutil -c icns "$ea9_iconset" -o "$ea9_app/Contents/Resources/AppIcon.icns"
codesign --force --deep --sign - "$ea9_app"
codesign --verify --deep --strict "$ea9_app"
if [[ -e "$ea9_destination" ]]; then
    mv "$ea9_destination" "$ea9_stage/previous.app"
fi
if ! mv "$ea9_app" "$ea9_destination"; then
    if [[ -e "$ea9_stage/previous.app" ]]; then
        mv "$ea9_stage/previous.app" "$ea9_destination"
    fi
    exit 1
fi
printf 'Built %s\nCLI: %s\n' "$ea9_destination" "$ea9_root/dist/ea9ctl"
