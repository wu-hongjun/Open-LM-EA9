#!/usr/bin/env python3
"""Build OpenLensAdapter firmware offline; default reproduces working 4.5.0."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from firmware_config import apply_lens, assemble, load_config, load_target, require, source_files

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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--wide-aperture', action='store_true', help='Reproduce separate 4.6.0 f/1.2–f/22 candidate.')
    mode.add_argument('--config', type=Path, help='Custom offline image; requires a new unpublished version.')
    mode.add_argument('--lens-profile-template', action='store_true', help='Build the 4.7.0 app-selectable lens template.')
    args = parser.parse_args()
    work = (args.output or ROOT / 'artifacts/private' /
            ('firmware-build-' + datetime.now().strftime('%Y%m%d-%H%M%S'))).resolve()
    require(work.is_relative_to(ROOT / 'artifacts/private'), 'Output must be below artifacts/private.')
    try:
        config = load_config(args.config, ROOT / 'firmware/releases') if args.config else None
        target_dir, target = load_target(ROOT, config['target'] if config else 'lm-ea9')
        files = source_files(ROOT, target_dir)
    except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
        parser.error(str(error))
    manifest = json.loads((RELEASE / 'manifest.json').read_text())
    if not config:
        require(set(files) == set(manifest['sources']), 'Working source set changed; use a custom version.')
        for name, expected in manifest['sources'].items():
            require(sha(files[name]) == expected, 'Working source changed: ' + name + '; use a custom version.')
    assert sha(RELEASE / 'biotar-camera-aperture.bin') == manifest['imageSHA256']
    if not Path(ARM + 'gcc').exists():
        raise SystemExit('Install the pinned ARM toolchain and CMSIS/SAMD21 headers; see docs/development.md.')
    work.mkdir(parents=True, exist_ok=False)
    assemble(files, work / 'src')
    shutil.copytree(ROOT / 'firmware/hosttest', work / 'tools/hosttest')
    if config:
        apply_lens(config, work / 'src')
        (work / 'configuration.json').write_text(json.dumps(config, indent=2) + '\n')
    elif args.wide_aperture or args.lens_profile_template:
        header = work / 'src/emount.h'
        text = header.read_text()
        assert text.count('#define EM_APERTURE_MAX  0x1200u') == 1
        assert text.count('#define EM_APERTURE_MIN  0x1800u') == 1
        header.write_text(text.replace('#define EM_APERTURE_MAX  0x1200u', '#define EM_APERTURE_MAX  0x1080u')
                         .replace('#define EM_APERTURE_MIN  0x1800u', '#define EM_APERTURE_MIN  0x1900u'))
        if args.lens_profile_template:
            # A separate flash word prevents folding startup reporting into instructions.
            # Initial packet literals stay f/2; em_init commits the selected value before RX.
            header.write_text(header.read_text().replace('#define EM_APERTURE_NOW',
                'extern const uint16_t em_startup_aperture_av;\n#define EM_APERTURE_NOW'))
            packets = work / 'src/emount_packets.c'
            packets.write_text(packets.read_text().replace('const uint16_t em_focal_mm10 = EM_FOCAL_MM10;',
                'const uint16_t em_focal_mm10 = EM_FOCAL_MM10;\nconst uint16_t em_startup_aperture_av = EM_APERTURE_NOW;'))
            reporting = work / 'src/reported_aperture.c'
            s = reporting.read_text()
            assert s.count('= EM_APERTURE_NOW;') == 2
            reporting.write_text(s.replace('= EM_APERTURE_NOW;', '= em_startup_aperture_av;'))
    for name in target['buildRules']:
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_dir / name, work / name)
    includes = '-Isrc ' + ' '.join('-I' + str(DEPS / name) for name in target['includeDirectories'])
    with (work / 'build.log').open('w') as log:
        subprocess.run(['make', '-f', target['makefile'], 'BUILD=release', 'OPT=-Os',
                        f'TOOLCHAIN={ARM}', f'INCLUDES={includes}', target['elf']],
                       cwd=work, check=True, stdout=log, stderr=subprocess.STDOUT)
    elf = work / target['elf']
    symbols = {}
    for line in subprocess.check_output([ARM + 'nm', str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    assert not any(n.startswith(('diag_', 'trail_')) for n in symbols)
    assert 'em_uart_set_baud' not in symbols
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    assert end <= target['codeAndDataLimit'] and symbols['_estack'] <= target['ramEnd']
    raw = work / 'raw.bin'
    subprocess.run([ARM + 'objcopy', '-O', 'binary', '--gap-fill=0xff', str(elf), str(raw)], check=True)
    data = raw.read_bytes()
    assert len(data) == end - target['applicationStart']
    image = work / ('lens-profile-template.bin' if args.lens_profile_template else 'custom-firmware.bin' if config else
                    'biotar-wide-aperture.bin' if args.wide_aperture else 'biotar-camera-aperture.bin')
    image.write_bytes(data.ljust(target['applicationBytes'], b'\xff'))
    published_matches = False
    if not config:
        version = '4.7.0' if args.lens_profile_template else '4.6.0' if args.wide_aperture else '4.5.0'
        published = ROOT / 'firmware/releases' / version / image.name
        require(published.is_file() and sha(image) == sha(published),
                'Build differs from published ' + version + '; use a new version.')
        published_matches = True
    if config:
        # New custom provenance, never inherit the baseline's qualification or identity.
        manifest = dict(schemaVersion=1, loaderVersion=config['version'], target=config['target'],
                        lens=config['lens'], reportedAperture=config['reportedAperture'],
                        imageSHA256=sha(image), imageBytes=image.stat().st_size,
                        rawBytes=len(data), codeAndDataEnd=hex(end), cameraQualified=False,
                        uploadQualified=False, baselineImageSHA256=manifest['imageSHA256'],
                        configurationSHA256=sha(work / 'configuration.json'),
                        targetSHA256=sha(target_dir / 'target.json'),
                        buildRules={name:sha(work / name) for name in target['buildRules']},
                        sources={name:sha(work / 'src' / name) for name in sorted(files)},
                        builderSHA256=sha(Path(__file__)),
                        configurationBuilderSHA256=sha(ROOT / 'scripts/firmware_config.py'))
        (work/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    elif args.wide_aperture or args.lens_profile_template:
        baseline = manifest['imageSHA256']
        manifest.update(loaderVersion=[4,7,0] if args.lens_profile_template else [4,6,0], apertureMaximumAV=4224, apertureMinimumAV=6400,
                        baselineImageSHA256=baseline, imageSHA256=sha(image), rawBytes=len(data),
                        codeAndDataEnd=hex(end), cameraQualified=False,
                        sources={p.name:sha(p) for p in sorted((work/'src').iterdir()) if p.is_file()},
                        builderSHA256=sha(Path(__file__)))
        manifest.pop('from44PatchSHA256',None)
        if args.lens_profile_template:
            sections = []
            for line in subprocess.check_output([ARM+'objdump', '-h', str(elf)], text=True).splitlines():
                f = line.split()
                if len(f) >= 6 and f[0].isdigit():
                    sections.append((int(f[3],16), int(f[3],16)+int(f[2],16), int(f[4],16)))
            def offset(name):
                address = symbols[name]
                for start, stop, lma in sections:
                    if start <= address < stop:
                        return lma + address - start - target['applicationStart']
                raise ValueError('Missing load address: '+name)
            slots = dict(focalMM10=offset('em_focal_mm10'), startupAV=offset('em_startup_aperture_av'),
                         lensName=offset('em_msg_3F')+7, profileRecord=0x4f00)
            assert end <= 0x9f00 and image.read_bytes()[0x4f00:] == b'\xff'*256
            manifest.update(patchSlots=slots, profileRecordBytes=256, templateOnly=True,
                            sourceBaselineVersion='4.6.0', baselineImageSHA256=sha(ROOT/'firmware/releases/4.6.0/biotar-wide-aperture.bin'))
        (work/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    else:
        assert sha(image) == manifest['imageSHA256'], 'Build differs from the working release; use a new version for behavior changes.'
        shutil.copy2(RELEASE / 'manifest.json', work / 'manifest.json')
    evidence = dict(imageSHA256=sha(image), imageBytes=image.stat().st_size,
                    codeAndDataEnd=hex(end), builderSHA256=sha(Path(__file__)),
                    sourcePinsMatch=not bool(config), publishedImageMatches=published_matches, hardwareAccess=False)
    (work / 'build-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(f"{'.'.join(map(str,manifest['loaderVersion']))}: {sha(image)}\nBuild: {work}")


if __name__ == '__main__':
    main()
