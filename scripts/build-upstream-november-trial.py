#!/usr/bin/env python3
"""Materialize and build the pinned November upstream release for a local trial."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'e054db90cfae5d67fac67a7e0db4bb100f5893ae'
BASE = ROOT / 'firmware/candidates/4.2.0'
BASE_SHA = '2a11822d47672355455dc4415db95f1487527e4f9865270ea368f24fc0ceaa7b'
DEPS = ROOT / 'tools/firmware-deps'
ARM = DEPS / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-'
DFP = DEPS / 'samd21-dfp-2/samd21a/include'
CMSIS = DEPS / 'CMSIS_5-5.9.0/CMSIS/Core/Include'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keep_stock_speed(work):
    """Refuse the speed offer and remove the associated extra CS pulse."""
    source = work / 'src/emount.c'
    pinned = json.loads((BASE / 'manifest.json').read_text())
    assert sha(BASE / 'upstream-november-trial.bin') == pinned['imageSHA256'] == BASE_SHA
    assert sha(source) == pinned['builtSourceSHA256']['emount.c']
    before = source.read_text()
    start = before.index('/* The baud switch after the 0x0C reply')
    end = before.index('static void em_send_id(', start)
    assert 'em_uart_set_baud(EM_BAUD_FAST);' in before[start:end]
    after = before[:start] + before[end:]
    start = after.index('\t/* Message 0x0C: the template answers 01')
    end = after.index('\n\tem_transmit(frame, p->len);\n}', start)
    assert after[start:end].count('em_baud_switch();') == 1
    after = after[:start] + (
        '\t/* Decline the speed change and keep SERCOM1 at the boot rate. */\n'
        '\tif (id == EM_ID_BAUD) {\n'
        '\t\tframe[6] = 0;\n'
        '\t}\n'
    ) + after[end:]
    source.write_text(after)
    diff = difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                               fromfile='a/src/emount.c', tofile='b/src/emount.c', n=0)
    (work / 'stock-speed.patch').write_text(''.join(diff))
    return pinned


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization; the build requires assertions.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stock-speed', action='store_true', help='Build the fixed 750 kbaud experiment.')
    args = parser.parse_args()
    checkout, work = args.checkout.resolve(), args.output.resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    assert subprocess.check_output(['git', 'rev-parse', COMMIT], cwd=checkout, text=True).strip() == COMMIT
    work.mkdir(exist_ok=False)
    archive = work / 'upstream.tar'
    subprocess.run(['git', 'archive', '--format=tar', f'--output={archive}', COMMIT], cwd=checkout, check=True)
    subprocess.run(['tar', '-xf', archive], cwd=work, check=True)

    source_pins = {p.name: sha(p) for p in sorted((work / 'src').iterdir()) if p.is_file()}
    changes = {
        'startup_samd21.c': [('#include "samd21.h"', '#include "sam.h"'),
                            ('.pfnNMI_Handler', '.pfnNonMaskableInt_Handler'),
                            ('.pfnSVC_Handler', '.pfnSVCall_Handler')],
        'system_samd21.c': [('#include "samd21.h"', '#include "sam.h"')],
        'ea9.ld': [('LENGTH = 0x0001b000', 'LENGTH = 0x00005000')],
    }
    diff = []
    for name, replacements in changes.items():
        path = work / 'src' / name
        before = after = path.read_text()
        for old, new in replacements:
            assert after.count(old) == 1, (name, old)
            after = after.replace(old, new)
        path.write_text(after)
        diff.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile='upstream/src/' + name, tofile='build/src/' + name, n=0))
    (work / 'compatibility.patch').write_text(''.join(diff))
    baseline = keep_stock_speed(work) if args.stock_speed else None

    target = 'build/ea9-rebuild-release'
    # The pinned toolchain's all-O2 image exceeds the preserved stock boundary.
    # Retain -O2 for peripheral ISR and actuator units.
    timing_units = ['em_uart', 'em_eic', 'abs_encoder', 'motor', 'servo']
    size_flags = work / 'bounded-release.mk'
    size_flags.write_text('include Makefile\n' + ' '.join('$(OBJDIR)/' + unit + '.o' for unit in timing_units)
                          + ': CFLAGS += -O2\n')
    with (work / 'build.log').open('w') as log:
        subprocess.run(['make', '-f', size_flags.name, 'BUILD=release', 'OPT=-Os', f'TOOLCHAIN={ARM}',
                        f'INCLUDES=-Isrc -I{DFP} -I{CMSIS}', target + '.elf'],
                       cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
    elf, raw_path = work / (target + '.elf'), work / 'raw.bin'
    symbols = {}
    for line in subprocess.check_output([str(ARM) + 'nm', str(elf)], text=True).splitlines():
        fields = line.split()
        if len(fields) == 3:
            symbols[fields[2]] = int(fields[0], 16)
    assert {'Reset_Handler', 'motor_drive', 'em_poll', 'optical_file'} <= symbols.keys()
    assert ('em_uart_set_baud' in symbols) != args.stock_speed
    assert not any(n.startswith(('diag_', 'trail_', 'st_crash_', 'st_watchdog_')) for n in symbols)
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    assert end <= 0x9f00 and symbols['_estack'] - symbols['_sstack'] == 8192
    subprocess.run([str(ARM) + 'objcopy', '-O', 'binary', '--gap-fill=0xff', elf, raw_path], check=True)
    raw = raw_path.read_bytes()
    sp, reset = int.from_bytes(raw[:4], 'little'), int.from_bytes(raw[4:8], 'little')
    assert len(raw) == end - 0x5000 and sp == symbols['_estack'] and sp % 8 == 0 and sp <= 0x20004000
    assert reset == symbols['Reset_Handler'] | 1 and 0x5000 <= (reset & ~1) < end
    image = work / ('upstream-stock-speed.bin' if args.stock_speed else 'upstream-november-trial.bin')
    image.write_bytes(raw.ljust(0x5000, b'\xff'))
    host_patch = ROOT / 'firmware/candidates/4.4.0/hosttest.patch'
    if args.stock_speed:
        subprocess.run(['git', 'apply', '--unidiff-zero', '--whitespace=error', str(host_patch)], cwd=work, check=True)
    with (work / 'hosttests.log').open('w') as log:
        subprocess.run(['make', 'hosttest', 'HOSTCC=clang'], cwd=work,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=90)
    built_pins = {name: sha(work / 'src' / name) for name in source_pins}
    expected_changed = set(changes) | ({'emount.c'} if args.stock_speed else set())
    assert {name for name in source_pins if source_pins[name] != built_pins[name]} == expected_changed
    manifest = dict(upstreamCommit=COMMIT, loaderVersion=[4, 2, 0], cameraVersionBCD='0x20',
                    fixedFocalMM10=500, nominalApertureAV=4544, lensID=50496,
                    rawBytes=len(raw), imageBytes=image.stat().st_size,
                    rawSHA256=sha(raw_path), imageSHA256=sha(image), applicationRange=['0x5000', '0xa000'],
                    codeAndDataEnd=hex(end), stackBytes=8192, optimization='-Os',
                    extraUnitFlags={unit + '.c': ['-O2'] for unit in timing_units},
                    upstreamSourceSHA256=source_pins, builtSourceSHA256=built_pins,
                    compatibilityPatchSHA256=sha(work / 'compatibility.patch'),
                    upstreamMakefileSHA256=sha(work / 'Makefile'), hostTestsPassed=True,
                    releaseLogsCompiledOut=True, cameraQualified=False)
    if baseline:
        assert source_pins == baseline['upstreamSourceSHA256']
        assert manifest['compatibilityPatchSHA256'] == baseline['compatibilityPatchSHA256']
        assert manifest['upstreamMakefileSHA256'] == baseline['upstreamMakefileSHA256']
        assert {name for name, digest in built_pins.items()
                if digest != baseline['builtSourceSHA256'][name]} == {'emount.c'}
        manifest.update(loaderVersion=[4, 4, 0], baselineImageSHA256=BASE_SHA, cameraBusBaud=750000,
                        speedOfferReply=0, stockSpeedPatchSHA256=sha(work / 'stock-speed.patch'),
                        hostExpectationPatchSHA256=sha(host_patch))
    (work / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{image.name}: {len(raw)} linked bytes, {image.stat().st_size} upload bytes, SHA-256 {sha(image)}')


if __name__ == '__main__':
    main()
