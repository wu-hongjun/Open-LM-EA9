#!/usr/bin/env python3
"""Reproduce working 4.5.0 from checked-in C sources. No USB access."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEPS = ROOT / 'tools/firmware-deps'
ARM = str(DEPS / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
RELEASE = ROOT / 'firmware/releases/4.5.0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not __debug__:
        raise SystemExit('Build assertions require Python without optimization.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--wide-aperture', action='store_true', help='Prepare separate 4.6.0 f/1.2–f/22 candidate.')
    args = parser.parse_args()
    work = (args.output or ROOT / 'artifacts/private' /
            ('firmware-build-' + datetime.now().strftime('%Y%m%d-%H%M%S'))).resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    manifest = json.loads((RELEASE / 'manifest.json').read_text())
    for name, expected in manifest['sources'].items():
        assert sha(ROOT / 'firmware/src' / name) == expected, name
    assert sha(RELEASE / 'biotar-camera-aperture.bin') == manifest['imageSHA256']
    if not Path(ARM + 'gcc').exists():
        raise SystemExit('Install the pinned ARM toolchain and CMSIS/SAMD21 headers; see docs/development.md.')
    work.mkdir(parents=True, exist_ok=False)
    shutil.copytree(ROOT / 'firmware/src', work / 'src')
    shutil.copytree(ROOT / 'firmware/hosttest', work / 'tools/hosttest')
    if args.wide_aperture:
        header = work / 'src/emount.h'
        text = header.read_text()
        assert text.count('#define EM_APERTURE_MAX  0x1200u') == 1
        assert text.count('#define EM_APERTURE_MIN  0x1800u') == 1
        header.write_text(text.replace('#define EM_APERTURE_MAX  0x1200u', '#define EM_APERTURE_MAX  0x1080u')
                         .replace('#define EM_APERTURE_MIN  0x1800u', '#define EM_APERTURE_MIN  0x1900u'))
    for name in ['release.mk', 'optimizations.mk']:
        shutil.copy2(ROOT / 'firmware' / name, work / name)
    includes = f'-Isrc -I{DEPS}/samd21-dfp-2/samd21a/include -I{DEPS}/CMSIS_5-5.9.0/CMSIS/Core/Include'
    with (work / 'build.log').open('w') as log:
        subprocess.run(['make', '-f', 'optimizations.mk', 'BUILD=release', 'OPT=-Os',
                        f'TOOLCHAIN={ARM}', f'INCLUDES={includes}', 'build/ea9-rebuild-release.elf'],
                       cwd=work, check=True, stdout=log, stderr=subprocess.STDOUT)
    elf = work / 'build/ea9-rebuild-release.elf'
    symbols = {}
    for line in subprocess.check_output([ARM + 'nm', str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    assert not any(n.startswith(('diag_', 'trail_')) for n in symbols)
    assert 'em_uart_set_baud' not in symbols
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    assert end <= 0x9f00 and symbols['_estack'] <= 0x20004000
    raw = work / 'raw.bin'
    subprocess.run([ARM + 'objcopy', '-O', 'binary', '--gap-fill=0xff', str(elf), str(raw)], check=True)
    data = raw.read_bytes()
    assert len(data) == end - 0x5000
    image = work / ('biotar-wide-aperture.bin' if args.wide_aperture else 'biotar-camera-aperture.bin')
    image.write_bytes(data.ljust(0x5000, b'\xff'))
    if args.wide_aperture:
        baseline = manifest['imageSHA256']
        manifest.update(loaderVersion=[4,6,0], apertureMaximumAV=4224, apertureMinimumAV=6400,
                        baselineImageSHA256=baseline, imageSHA256=sha(image), rawBytes=len(data),
                        codeAndDataEnd=hex(end), cameraQualified=False,
                        sources={p.name:sha(p) for p in sorted((work/'src').iterdir()) if p.is_file()},
                        builderSHA256=sha(Path(__file__)))
        manifest.pop('from44PatchSHA256',None)
        (work/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    else:
        assert sha(image) == manifest['imageSHA256'], 'Build differs from the working release; use a new version for behavior changes.'
        shutil.copy2(RELEASE / 'manifest.json', work / 'manifest.json')
    evidence = dict(imageSHA256=sha(image), imageBytes=image.stat().st_size,
                    codeAndDataEnd=hex(end), builderSHA256=sha(Path(__file__)),
                    sourcePinsMatch=True, publishedImageMatches=not args.wide_aperture, hardwareAccess=False)
    (work / 'build-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f"{'.'.join(map(str,manifest['loaderVersion']))}: {sha(image)}\nBuild: {work}")


if __name__ == '__main__':
    main()
