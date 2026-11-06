#!/usr/bin/env python3
"""Build the motor-disabled probe without opening any hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'firmware/startup-probe'
CANDIDATE = ROOT / 'firmware/candidates/4.3.0'
TRIAL = ROOT / 'firmware/candidates/4.2.0/manifest.json'
STOCK = ROOT / 'firmware/recovery/stock-1.8.0/application.bin'
STOCK_SHA = 'f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564'
COMMIT = 'e054db90cfae5d67fac67a7e0db4bb100f5893ae'
DEPS = ROOT / 'tools/firmware-deps'
ARM = str(DEPS / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
INCLUDES = [SOURCE, DEPS / 'samd21-dfp-2/samd21a/include', DEPS / 'CMSIS_5-5.9.0/CMSIS/Core/Include']
IMAGE = 'startup-probe.bin'
# Addresses in the factory load image. Initializers with zero length/checksum
# are finalized by probe.c, as they are by the factory sender at runtime.
PACKETS = {
    0x01: (0x9a0c, 41), 0x05: (0x9b7c, 105), 0x06: (0x99d4, 48),
    0x07: (0x9a38, 43), 0x08: (0x9a88, 210), 0x09: (0x9b5c, 20),
    0x0b: (0x9a70, 11), 0x0c: (0x9a64, 10), 0x0d: (0x9a7c, 10),
    0x10: (0x9b70, 10), 0x19: (0x9cfc, 10), 0x1b: (0x9d24, 19),
    0x28: (0x9d38, 44), 0x32: (0x9be8, 16), 0x34: (0x9cdc, 32),
    0x3d: (0x9c54, 72), 0x3f: (0x9c08, 74), 0x4c: (0x9bf8, 16),
    0x5a: (0x9c9c, 64),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return digest(path.read_bytes())


def generate_packets(path):
    stock = STOCK.read_bytes()
    assert digest(stock) == STOCK_SHA
    entries = []
    for id_, (address, length) in PACKETS.items():
        offset = address - 0x5000
        frame = stock[offset:offset + length]
        assert len(frame) == length and frame[0] == 0xf0 and frame[5] == id_, hex(address)
        assert int.from_bytes(frame[1:3], 'little') in (0, length) and frame[-1] == 0x55
        rows = [', '.join(f'0x{b:02x}' for b in frame[i:i + 12]) for i in range(0, length, 12)]
        entries.append(f'    {{{length}, (const uint8_t[]){{\n        ' + ',\n        '.join(rows) + '\n    }},')
    path.write_text('/* Generated from the pinned public stock application. */\n'
                    'static const struct stock_packet { uint16_t length; const uint8_t *bytes; }\n'
                    'stock_packets[] = {\n' + '\n'.join(entries) + '\n};\n')


def build(checkout, output):
    assert output.is_relative_to(ROOT / 'artifacts/private')
    output.mkdir(exist_ok=False)
    known = json.loads(TRIAL.read_text())
    assert known['upstreamCommit'] == COMMIT
    for name in ('startup_samd21.c', 'system_samd21.c', 'ea9.ld'):
        data = subprocess.check_output(['git', 'show', f'{COMMIT}:src/{name}'], cwd=checkout)
        assert digest(data) == known['upstreamSourceSHA256'][name]
        replacements = {
            'startup_samd21.c': [('samd21.h', 'sam.h'), ('.pfnNMI_Handler', '.pfnNonMaskableInt_Handler'),
                                 ('.pfnSVC_Handler', '.pfnSVCall_Handler')],
            'system_samd21.c': [('samd21.h', 'sam.h')],
            'ea9.ld': [('LENGTH = 0x0001b000', 'LENGTH = 0x00004c00')],
        }
        for old, new in replacements[name]:
            assert data.count(old.encode()) == 1
            data = data.replace(old.encode(), new.encode())
        (output / name).write_bytes(data)
    generate_packets(output / 'stock_packets.h')
    units = [output / 'startup_samd21.c', output / 'system_samd21.c',
             SOURCE / 'main.c', SOURCE / 'probe.c', SOURCE / 'flash.c']
    arch = ['-mthumb', '-mcpu=cortex-m0plus']
    flags = [*arch, '-O2', '-std=gnu11', '-D__SAMD21E17A__', '-Wall', '-Wextra', '-Werror',
             '-ffunction-sections', '-fdata-sections', '-fstack-usage']
    objects = []
    for src in units:
        obj = output / (src.stem + '.o')
        subprocess.run([ARM + 'gcc', *flags, *(f'-I{p}' for p in [output, *INCLUDES]),
                        '-c', str(src), '-o', str(obj)], check=True)
        objects.append(str(obj))
    elf = output / 'probe.elf'
    subprocess.run([ARM + 'gcc', *arch, *objects, '-Tea9.ld', '-Wl,--gc-sections,-Map=probe.map',
                    '--specs=nano.specs', '--specs=nosys.specs', '-o', str(elf)], cwd=output, check=True)
    symbols = {}
    for line in subprocess.check_output([ARM + 'nm', str(elf)], text=True).splitlines():
        q = line.split()
        if len(q) == 3:
            symbols[q[2]] = int(q[0], 16)
    assert {'main', 'EIC_Handler', 'SERCOM1_Handler', 'probe_write_page'} <= symbols.keys()
    for handler in ('TCC0_Handler', 'TCC1_Handler', 'TC4_Handler', 'SERCOM0_Handler', 'ADC_Handler'):
        assert symbols[handler] == symbols['Dummy_Handler'], handler
    end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
    assert end <= 0x9b00 and symbols['_estack'] - symbols['_sstack'] == 8192
    raw_path = output / 'raw.bin'
    subprocess.run([ARM + 'objcopy', '-O', 'binary', '--gap-fill=0xff', str(elf), str(raw_path)], check=True)
    raw = raw_path.read_bytes()
    sp, reset = int.from_bytes(raw[:4], 'little'), int.from_bytes(raw[4:8], 'little')
    assert len(raw) == end - 0x5000 and sp == symbols['_estack'] and sp % 8 == 0 and sp <= 0x20004000
    assert reset == symbols['Reset_Handler'] | 1 and 0x5000 <= (reset & ~1) < end
    image = raw.ljust(0x5000, b'\xff')
    (output / IMAGE).write_bytes(image)
    pins = {p.name: sha(p) for p in sorted(SOURCE.iterdir()) if p.suffix in ('.c', '.h') and p.name != 'test_probe.c'}
    manifest = dict(loaderVersion=[4, 3, 0], cameraVersionBCD='0x18', cameraLensID='0x00ea',
                    cameraIdentity='TECHART LM-EA9', cameraBusBaud=750000, cameraQualified=False,
                    motorDrive=False, upstreamStartupCommit=COMMIT, stockPacketSourceSHA256=STOCK_SHA,
                    imageBytes=len(image), rawBytes=len(raw), imageSHA256=digest(image),
                    immutablePrefixSHA256=digest(image[:0x4c00]), codeAndDataEnd=hex(end),
                    diagnosticRange=['0x9c00', '0xa000'], diagnosticPageBytes=64, diagnosticFormat=1,
                    stackBytes=8192, staticRAMBytes=symbols['_ezero'] - 0x20000000, flags=flags,
                    sourceSHA256=pins, generatedSHA256={name: sha(output / name) for name in
                        ('startup_samd21.c', 'system_samd21.c', 'ea9.ld', 'stock_packets.h')},
                    builderSHA256=sha(Path(__file__).resolve()))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{IMAGE}: {len(raw)} linked bytes, {len(image)} upload bytes, SHA-256 {digest(image)}')


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.checkout.resolve(), args.output.resolve())
