#!/usr/bin/env python3
"""Test the production C probe and its offline decoder with synthetic data."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'firmware/startup-probe'


def reject(module, backup, text):
    try:
        module.decode(backup)
    except ValueError as error:
        assert text in str(error), error
    else:
        raise AssertionError(f'Expected decoder to reject {text} control')


def run(build, tmp):
    exe = tmp / 'host'
    tail = tmp / 'tail.bin'
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-g',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    f'-I{build}', f'-I{SOURCE}', str(SOURCE / 'probe.c'),
                    str(SOURCE / 'test_probe.c'), '-o', str(exe)], check=True)
    subprocess.run([str(exe), str(tail)], check=True)
    decoder = ROOT / 'scripts/decode-startup-probe.py'
    spec = importlib.util.spec_from_file_location('probe_decoder', decoder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    backup = tmp / 'synthetic.ea9backup'
    backup.mkdir()
    flash_path = backup / 'flash.bin'
    manifest_path = backup / 'manifest.json'
    image = (build / 'startup-probe.bin').read_bytes()
    assert image == (module.CANDIDATE / 'startup-probe.bin').read_bytes()
    assert image[-1024:] == b'\xff' * 1024
    data = bytearray(b'\xff' * 0x20000)
    data[0x4000:0x4003] = b'\x04\x03\x00'
    data[0x5000:0xa000] = image
    assert len(tail.read_bytes()) == 1024
    data[0x9c00:0xa000] = tail.read_bytes()

    def publish():
        flash_path.write_bytes(data)
        manifest_path.write_text(json.dumps({'schemaVersion': 1, 'flashReadPasses': 2,
            'auxiliaryReadPasses': 2, 'reportedFirmwareVersion': '4.3.0', 'files': {
            'flash.bin': {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}}}))

    publish()
    output_path = tmp / 'decoded.json'
    subprocess.run(['python3', str(decoder), str(backup), '--output', str(output_path)], check=True)
    out = json.loads(output_path.read_text())
    assert out['nativeFlashManifestMatched'] and out['immutableApplicationMatches']
    assert out['latestValidSlot'] == 1 and out['appendSpaceAvailable']
    assert out['pages'][0]['state'] == 'invalid-or-torn'
    assert all(page['state'] == 'erased' for page in out['pages'][2:])
    last = out['pages'][1]
    assert last['flags']['finalEchoReleased'] and last['reason'] == 'shutdown-echo-released'
    assert last['exchanges']['lastPairedTX'] == {'id': '0x0a', 'bytes': 25, 'ms': 112}
    assert last['exchanges']['firstNormalRX'] == {'id': '0x03', 'bytes': 29, 'ms': 113}
    assert not module.decode(flash_path)['nativeFlashManifestMatched']

    data[0x9c40 + 20] ^= 1
    flash_path.write_bytes(data)
    reject(module, backup, 'manifest')
    publish()
    assert module.decode(backup)['latestValidSlot'] is None  # Wrong CRC.
    start = 0x9c40
    data[start + 60:start + 64] = zlib.crc32(data[start:start + 60]).to_bytes(4, 'little')
    publish()
    assert module.decode(backup)['latestValidSlot'] is None  # Valid CRC, impossible pair.
    data[0x6000] ^= 1
    publish()
    reject(module, backup, 'Immutable')
    data[0x4000] = 3
    publish()
    reject(module, backup, 'USB firmware version')
    flash_path.write_bytes(data[:-1])
    reject(module, flash_path, '128 KiB')
    print('Probe decoder accepted the synthetic backup and rejected manifest, CRC, semantics, image, version and length controls.')


if __name__ == '__main__':
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ea9-startup-probe-') as directory:
        run(args.build.resolve(), Path(directory))
