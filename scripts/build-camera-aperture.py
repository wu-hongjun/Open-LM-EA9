#!/usr/bin/env python3
"""Build a Biotar 58mm f/2 camera-dial reporting experiment from pinned 4.4.0."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'firmware/candidates/4.4.0'
OVERLAY = ROOT / 'firmware/camera-aperture'
DEPS = ROOT / 'tools/firmware-deps'
ARM = str(DEPS / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
DFP = DEPS / 'samd21-dfp-2/samd21a/include'
CMSIS = DEPS / 'CMSIS_5-5.9.0/CMSIS/Core/Include'
IMAGE = 'biotar-camera-aperture.bin'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def materialize(base, work):
    manifest = json.loads((BASE / 'manifest.json').read_text())
    assert (base / 'manifest.json').read_bytes() == (BASE / 'manifest.json').read_bytes()
    assert sha(base / 'upstream-stock-speed.bin') == manifest['imageSHA256']
    for name, expected in manifest['builtSourceSHA256'].items():
        assert sha(base / 'src' / name) == expected, name
    work.mkdir(exist_ok=False)
    for directory in ('src', 'tools'):
        shutil.copytree(base / directory, work / directory)
    shutil.copy2(base / 'Makefile', work / 'Makefile')
    shutil.copy2(base / 'bounded-release.mk', work / 'bounded-release.mk')

    changes = {}
    source = work / 'src'
    p = source / 'emount.h'
    changes[p] = p.read_text().replace('#define EM_FOCAL_MM10 500u', '#define EM_FOCAL_MM10 580u')
    for name, value in [('MAX', '0x1200u'), ('MIN', '0x1800u'), ('NOW', '0x1200u')]:
        pattern = r'(#define EM_APERTURE_' + name + r'\s+)0x11C0u[^\n]*'
        changes[p], count = re.subn(pattern, r'\g<1>' + value, changes[p])
        assert count == 1
    assert changes[p] != p.read_text()
    start = changes[p].index('/* THE APERTURE this adapter declares')
    end = changes[p].index('#define EM_APERTURE_MAX', start)
    changes[p] = changes[p][:start] + (
        '/* Camera-side aperture range for the Biotar. The user sets the iris\n'
        ' * on the lens and selects the matching reported value on the body.\n'
        ' * Commands are staged and published from foreground protocol code. */\n'
    ) + changes[p][end:]

    p = source / 'emount.c'
    s = replace_once(p.read_text(), '#include "optical_file.h"', '#include "optical_file.h"\n#include "reported_aperture.h"')
    s = replace_once(s, '\tem_frames_rx++;\n', '''\tif (!em_shutdown_acked || (rx[3] == EM_CLASS_INIT && rx[5] == EM_ID_SESSION)) {
\t\treported_aperture_offer(rx, n);
\t}
\tem_frames_rx++;
''')
    s = replace_once(s, 'void em_init(void)\n{', 'void em_init(void)\n{\n\treported_aperture_init();')
    s = replace_once(s, '\tg_in_poll = 1;\n', '\tg_in_poll = 1;\n\treported_aperture_commit();\n')
    s = s.replace('/* The current aperture, 256 x AV + 4096: message 0x05 payload[0..1] (fixed,\n * in the template -- there is no iris) and message 0x28 payload[9..10], which',
                  '/* Current reported aperture, 256 x AV + 4096: message 0x05\n * payload[0..1] and message 0x28 payload[9..10], which')
    start = s.index('\t/* Message 0x1B, the aperture command: COUNTED, NOT OBEYED.')
    end = s.index('\n\t/* MESSAGE 0x08', start)
    s = s[:start] + '\t/* Aperture requests are validated and staged by reported_aperture. */\n' + s[end:]
    start = s.index('\t/* MESSAGE 0x03\'s APERTURE REQUEST.')
    end = s.index('\n\tif (rx[3] != EM_CLASS_INIT && rx[5] == 0x03u && n >= 16)', start)
    s = s[:start] + (
        '\t/* Retain the body-request telemetry. The reporting module validates\n'
        '\t * the complete frame before staging this operand for foreground use. */'
    ) + s[end:]
    changes[p] = s

    p = source / 'emount_packets.c'
    s = p.read_text()
    start = s.index('uint8_t em_msg_3F[')
    end = s.index('\n};', start) + 3
    name = b'Zeiss Jena Biotar 58mm f/2'
    frame = [0xf0, 74, 0, 2, 0, 0x3f, 0, *name]
    frame += [0] * (74 - len(frame))
    frame[-1] = 0x55
    rows = [', '.join(f'0x{b:02x}' for b in frame[i:i+12]) for i in range(0, len(frame), 12)]
    replacement = 'uint8_t em_msg_3F[EA9_LEN_3F] = {\n\t' + ',\n\t'.join(rows) + ',\n};'
    changes[p] = s[:start] + replacement + s[end:]
    patch = []
    for path, after in changes.items():
        before = path.read_text()
        assert before != after
        path.write_text(after)
        relative = str(path.relative_to(work))
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                           fromfile='a/'+relative, tofile='b/'+relative, n=0))
    for name in ('reported_aperture.c', 'reported_aperture.h'):
        shutil.copy2(OVERLAY / name, source / name)
    (work / 'from-44.patch').write_text(''.join(patch))
    return manifest


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base, work = args.base_build.resolve(), args.output.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    manifest = materialize(base, work)
    makefile = work / 'bounded-release.mk'
    makefile.write_text(makefile.read_text() + '\nOBJS += $(OBJDIR)/reported_aperture.o\n'
                       'build/ea9-rebuild-release.elf: $(OBJDIR)/reported_aperture.o\n')
    with (work / 'build.log').open('w') as log:
        subprocess.run(['make', '-f', makefile.name, 'BUILD=release', 'OPT=-Os', f'TOOLCHAIN={ARM}',
                        f'INCLUDES=-Isrc -I{DFP} -I{CMSIS}', 'build/ea9-rebuild-release.elf'],
                       cwd=work, check=True, stdout=log, stderr=subprocess.STDOUT)
    elf = work / 'build/ea9-rebuild-release.elf'
    symbols = {}
    for line in subprocess.check_output([ARM+'nm', str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    assert {'reported_aperture_offer', 'reported_aperture_commit', 'motor_drive', 'em_poll'} <= symbols.keys()
    assert 'em_uart_set_baud' not in symbols
    assert not any(name.startswith(('diag_', 'trail_')) for name in symbols)
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    assert end <= 0x9f00 and symbols['_estack'] <= 0x20004000
    raw_path = work / 'raw.bin'
    subprocess.run([ARM+'objcopy', '-O', 'binary', '--gap-fill=0xff', str(elf), str(raw_path)], check=True)
    raw = raw_path.read_bytes()
    assert len(raw) == end - 0x5000
    assert int.from_bytes(raw[:4], 'little') == symbols['_estack']
    assert int.from_bytes(raw[4:8], 'little') == symbols['Reset_Handler'] | 1
    image = work / IMAGE
    image.write_bytes(raw.ljust(0x5000, b'\xff'))
    pins = {p.name: sha(p) for p in sorted((work / 'src').iterdir()) if p.is_file()}
    changed = {name for name in manifest['builtSourceSHA256'] if pins[name] != manifest['builtSourceSHA256'][name]}
    assert changed == {'emount.c', 'emount.h', 'emount_packets.c'}
    output = dict(loaderVersion=[4,5,0], cameraVersionBCD='0x20', cameraBusBaud=750000,
                  lensID=manifest['lensID'], lensName='Zeiss Jena Biotar 58mm f/2', focalMM10=580,
                  apertureMaximumAV=4608, apertureMinimumAV=6144, apertureInitialAV=4608,
                  baselineImageSHA256=manifest['imageSHA256'], imageSHA256=sha(image),
                  imageBytes=image.stat().st_size, rawBytes=len(raw), codeAndDataEnd=hex(end),
                  stackBytes=symbols['_estack']-symbols['_sstack'], cameraQualified=False,
                  from44PatchSHA256=sha(work/'from-44.patch'),
                  sources=pins, builderSHA256=sha(Path(__file__)))
    (work / 'manifest.json').write_text(json.dumps(output, indent=2)+'\n')
    print(f'{IMAGE}: {len(raw)} linked bytes, SHA-256 {sha(image)}')


if __name__ == '__main__':
    main()
