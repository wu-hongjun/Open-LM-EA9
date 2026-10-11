#!/bin/bash
set -euo pipefail
ea9_root="$(cd "$(dirname "$0")/.." && pwd)"
ea9_cache="$ea9_root/apps/macos/.build/local-cache"
mkdir -p "$ea9_cache"
exec env CLANG_MODULE_CACHE_PATH="$ea9_cache/modules" SWIFT_MODULECACHE_PATH="$ea9_cache/modules" \
    swift "$@" --disable-sandbox --package-path "$ea9_root/apps/macos" \
    --cache-path "$ea9_cache/packages" --config-path "$ea9_cache/config" --security-path "$ea9_cache/security"
