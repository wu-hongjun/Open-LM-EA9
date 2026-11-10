#!/usr/bin/env python3
"""Decode 4.8.1 motion snapshots from a local, private backup."""
import argparse
import json
from pathlib import Path
import struct
import zlib

TRACE_START, TRACE_END = 0x14000, 0x16000
SLOT_BYTES = 4096
PAGE = 64
EVENT = struct.Struct('<IBBHii')
HOME_CAP, AF_CAP = 48, 192
AF_OFFSET = PAGE + HOME_CAP * EVENT.size
PHASES = ('', 'drive-start', 'drive-still', 'drive-cap', 'settle-start',
          'settle-still', 'settle-cap', 'origin')
OPS = ('none', 'move', 'distance', 'relative', 'defocus', 'stop', 'scan', 'drive')
OUTCOMES = ('ok', 'stall', 'timeout', 'runaway', 'wrong-way', 'aborted')


def decode_event(row):
    ms, kind, detail, aux, a, b = row
    event = {'ms': ms}
    if kind in (1, 2) and 0 < detail < len(PHASES) and aux < 16384:
        event.update(event='home-phase' if kind == 1 else 'home-sample',
                     phase=PHASES[detail], raw=aux)
        if kind == 1:
            event['trackedCounts'] = a
    elif kind == 3 and 0 < detail < len(OPS):
        event.update(event='command', op=OPS[detail])
        if detail in (1, 2):
            event['operand'] = a
        elif detail in (3, 4):
            event['delta'] = b
        elif detail == 6:
            event.update(scanA=a, scanB=b & 0xffff, centre=(b >> 16) & 0xffff,
                         flags=aux >> 8, speed=aux & 255)
        elif detail == 7:
            event.update(velocity=b, parameter=aux)
    elif kind in (4, 8) and 0 < detail < len(OPS):
        event.update(event='leg-start' if kind == 4 else 'deadband-skip',
                     op=OPS[detail], actualCounts=a, targetCounts=b)
        if kind == 4:
            event['requestedPositionUnits'] = aux
    elif kind in (5, 6) and detail in (0, 1):
        event.update(event='servo-sample' if kind == 5 else 'retarget',
                     actualCounts=a, targetCounts=b, reversal=bool(detail))
        if kind == 5:
            event['duty'] = aux if aux < 32768 else aux - 65536
    elif kind == 7 and detail < len(OUTCOMES):
        event.update(event='leg-end', outcome=OUTCOMES[detail],
                     actualCounts=a, targetCounts=b, peakDuty=aux)
    else:
        raise ValueError('Invalid event encoding.')
    return event


def decode(area):
    if len(area) != SLOT_BYTES:
        raise ValueError('Wrong trace area size.')
    if area == b'\xff' * len(area):
        return {'status': 'empty'}
    if area[:PAGE] == b'\xff' * PAGE:
        return {'status': 'incomplete', 'reason': 'Commit header is erased.'}
    if area[:8] != b'OLAMOT1!' or area[28:60] != bytes(32):
        raise ValueError('Unrecognized or damaged trace header.')
    home_count, af_count, af_total, home_crc, af_crc = struct.unpack_from('<5I', area, 8)
    header_crc, = struct.unpack_from('<I', area, 60)
    if header_crc != zlib.crc32(area[:60]):
        raise ValueError('Trace header CRC failed.')
    if not 1 <= home_count <= HOME_CAP or af_count != min(af_total, AF_CAP):
        raise ValueError('Trace record counts are invalid.')
    home = area[PAGE:PAGE + home_count * EVENT.size]
    af = area[AF_OFFSET:AF_OFFSET + af_count * EVENT.size]
    if zlib.crc32(home) != home_crc or zlib.crc32(af) != af_crc:
        raise ValueError('Trace payload CRC failed.')
    home_rows, af_rows = [list(EVENT.iter_unpack(payload)) for payload in (home, af)]
    if any(r[1] not in (1, 2) for r in home_rows) or any(r[1] in (1, 2) for r in af_rows):
        raise ValueError('Trace events are in the wrong stream.')
    if af_total > AF_CAP:
        head = af_total % AF_CAP
        af_rows = af_rows[head:] + af_rows[:head]
    return {'status': 'complete', 'schema': 'OLAMOT1!',
            'afEventsDropped': af_total - af_count,
            'homing': [decode_event(row) for row in home_rows],
            'autofocus': [decode_event(row) for row in af_rows]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('backup', type=Path, help='Native .ea9backup directory or its flash.bin')
    args = p.parse_args()
    path = args.backup / 'flash.bin' if args.backup.is_dir() else args.backup
    flash = path.read_bytes()
    if len(flash) != 0x20000:
        p.error('Expected a full 128 KiB flash backup.')
    sessions = []
    for slot, start in enumerate(range(TRACE_START, TRACE_END, SLOT_BYTES)):
        try:
            result = decode(flash[start:start + SLOT_BYTES])
        except ValueError as error:
            result = {'status': 'invalid', 'reason': str(error)}
        sessions.append({'slot': slot, **result})
    print(json.dumps(sessions, indent=2))


if __name__ == '__main__':
    main()
