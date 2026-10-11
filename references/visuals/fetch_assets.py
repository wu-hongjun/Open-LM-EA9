#!/usr/bin/env python3
"""Restore or verify pinned local product photos; never rewrite their catalogue."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def matches(path, asset):
    if not path.is_file():
        return False
    data = path.read_bytes()
    return len(data) == asset['bytes'] and hashlib.sha256(data).hexdigest() == asset['sha256']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    root = base.parents[1]
    resources = root / 'apps/macos/Sources/OpenLMEA9/Resources'
    manifest = base / 'assets.json'
    assets = json.loads(manifest.read_text())['assets']
    for asset in assets:
        name = asset['file']
        if Path(name).name != name or not name.endswith('.jpg') or not asset['imageURL'].startswith('https://'):
            raise ValueError('Invalid photograph catalogue entry')
        original = base / 'photos' / name
        bundled = resources / 'Photos' / name
        if args.verify_only:
            if not matches(original, asset) or not matches(bundled, asset):
                raise ValueError(f'Missing or changed original/resource: {name}')
            continue
        if matches(original, asset):
            data = original.read_bytes()
        elif matches(bundled, asset):
            data = bundled.read_bytes()
        else:
            request = urllib.request.Request(asset['imageURL'], headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(4_000_001)
            if len(data) != asset['bytes'] or hashlib.sha256(data).hexdigest() != asset['sha256']:
                raise ValueError(f'Remote bytes differ from the reviewed catalogue: {name}')
        for destination in (original, bundled):
            if not matches(destination, asset):
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix('.jpg.partial')
                temporary.write_bytes(data)
                temporary.replace(destination)
    if manifest.read_bytes() != (resources / 'photo-credits.json').read_bytes():
        raise ValueError('The bundled photo catalogue differs from assets.json')
    print(f'Verified {len(assets)} original photos and {len(assets)} app resources.')


if __name__ == '__main__':
    main()
