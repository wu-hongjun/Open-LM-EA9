#!/usr/bin/env python3
"""Decode startup probe 4.3.0 summaries from an existing private flash backup."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'firmware/candidates/4.3.0'
REASONS = ('first-close-timeout', 'inactivity', 'init-deadline', 'peripheral-fault',
           'tx-fault', 'shutdown-echo-released')
FLAGS = ('busReady', 'finalEchoReleased', 'statusPairReleased', 'bodyCSRise', 'bodyCSFall',
         'firstPrefixPreserved', 'capabilitiesReplyReleased', 'identityReplyReleased')
MARKS = ('lastValidInitRX', 'lastPairedRX', 'lastPairedTX', 'lastInitTXC', 'firstNormalRX')


def decode_page(page, index):
    if page == b'\xff' * 64:
        return {'slot': index, 'state': 'erased'}
    bad = {'slot': index, 'state': 'invalid-or-torn'}
    if (page[:6] != b'E9SP\x01' + bytes([index]) or not 1 <= page[6] <= len(REASONS)
            or zlib.crc32(page[:60]) != struct.unpack_from('<I', page, 60)[0]):
        return bad
    flags = dict(zip(FLAGS, (bool(page[7] & (1 << i)) for i in range(8))))
    uptime = struct.unpack_from('<I', page, 8)[0]
    marks = {}
    for i, name in enumerate(MARKS):
        id_, reserved, length, ms = struct.unpack_from('<BBHI', page, 12 + i * 8)
        if not length:
            if id_ or reserved or ms:
                return bad
            marks[name] = None
            continue
        if reserved or not 9 <= length <= (210 if i in (2, 3) else 256) or ms > uptime:
            return bad
        marks[name] = {'id': f'0x{id_:02x}', 'bytes': length, 'ms': ms}
    rx, paired_rx, paired_tx, txc, normal = marks.values()
    final = flags['finalEchoReleased']
    if ((paired_rx is None) != (paired_tx is None)
            or (paired_rx and (not rx or not txc or paired_rx['id'] != paired_tx['id']
                               or not paired_rx['ms'] <= paired_tx['ms'] <= txc['ms']
                               or rx['ms'] < paired_rx['ms']))
            or (flags['busReady'] and not flags['bodyCSFall'])
            or (flags['firstPrefixPreserved'] and not flags['bodyCSRise'])
            or (not flags['busReady'] and (txc or final))
            or ((flags['statusPairReleased'] or normal) and not final)
            or (final and (not paired_rx or paired_rx['id'] != '0x0a'
                           or paired_rx['bytes'] != 25 or paired_tx['bytes'] != 25 or paired_tx != txc))
            or (normal and (normal['id'] not in ('0x03', '0x04') or normal['ms'] < paired_tx['ms']))):
        return bad
    invalid, dropped, uart, vd = struct.unpack_from('<4H', page, 52)
    return {'slot': index, 'state': 'valid', 'reason': REASONS[page[6] - 1], 'uptimeMS': uptime,
            'flags': flags, 'exchanges': marks, 'invalidWindows': invalid, 'drops': dropped,
            'uartErrorEvents': uart, 'vdEdges': vd}


def decode(source):
    native = source.is_dir()
    if native:
        manifest_file = source / 'manifest.json'
        if manifest_file.stat().st_size > 65536:
            raise ValueError('Native backup manifest exceeds its size limit.')
        backup = json.loads(manifest_file.read_text())
        source = source / 'flash.bin'
    if source.stat().st_size != 0x20000:
        raise ValueError('Expected a complete 128 KiB flash read.')
    data = source.read_bytes()
    if len(data) != 0x20000 or data[0x4000:0x4003] != bytes([4, 3, 0]):
        raise ValueError('Expected USB firmware version 4.3.0 in the flash read.')
    if native:
        flash = backup['files']['flash.bin']
        if (backup['schemaVersion'] != 1 or backup['flashReadPasses'] != 2 or backup['auxiliaryReadPasses'] != 2
                or backup['reportedFirmwareVersion'] != '4.3.0' or flash['bytes'] != len(data)
                or flash['sha256'] != hashlib.sha256(data).hexdigest()):
            raise ValueError('Native backup manifest does not match the complete flash read.')
    pin = json.loads((CANDIDATE / 'manifest.json').read_text())
    expected = (CANDIDATE / 'startup-probe.bin').read_bytes()
    if (len(expected) != 0x5000 or hashlib.sha256(expected).hexdigest() != pin['imageSHA256']
            or data[0x5000:0x9c00] != expected[:0x4c00]):
        raise ValueError('Immutable application bytes do not match the pinned startup probe.')
    pages = [decode_page(data[a:a + 64], i) for i, a in enumerate(range(0x9c00, 0xa000, 64))]
    return {'firmwareVersion': '4.3.0', 'format': 'EA9 startup probe v1',
            'nativeFlashManifestMatched': native, 'immutableApplicationMatches': True,
            'latestValidSlot': next((p['slot'] for p in reversed(pages) if p['state'] == 'valid'), None),
            'appendSpaceAvailable': pages[-1]['state'] == 'erased', 'pages': pages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup', type=Path, help='Existing .ea9backup directory or raw flash.bin')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        output = json.dumps(decode(args.backup), indent=2) + '\n'
        if args.output:
            with args.output.open('x') as handle:
                handle.write(output)
        else:
            print(output, end='')
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == '__main__':
    main()
