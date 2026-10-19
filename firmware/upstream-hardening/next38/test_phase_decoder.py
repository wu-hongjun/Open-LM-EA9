#!/usr/bin/env python3
"""Synthetic version-scoped phase records; no hardware or user dump reads."""
import argparse
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
from startup_diagnostic_v3 import decode_pages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
assert a.output.resolve().is_relative_to(ROOT/'artifacts/private')

def page(slot, kind, payload, chunk=0):
    b = bytearray(64)
    b[:4] = b'E9S3'
    b[4:8] = bytes((3,kind,1,1))
    struct.pack_into('<H',b,8,slot)
    b[10] = chunk
    b[12:60] = payload
    struct.pack_into('<I',b,60,zlib.crc32(b[:60]))
    return bytes(b)

rows = []
for fault, label in ((17,'home-drive-unsettled'),(18,'home-settle-unsettled'),(19,'home-poll-budget')):
    s = bytearray(48)
    s[24:27] = bytes((14,1,fault))
    s[37] = 3
    terminal = bytearray(48)
    terminal[:4] = bytes((5,fault,fault,1))
    fixture = page(0,1,s) + b''.join(page(i+1,3,bytes(48),i) for i in range(3)) + page(4,4,terminal) + b'\xff'*(11*64)
    new = decode_pages(fixture,version='3.8.0')
    old = decode_pages(fixture,version='3.7.0')
    assert new['validPages'] == 5 and new['semanticallyInconsistentPages'] == new['unassociatedPages'] == 0
    assert new['pages'][0]['summary']['fault'] == label
    assert new['pages'][0]['summary']['terminalFooters'][0]['fault'] == label
    assert old['semanticallyInconsistentPages'] > 0
    assert not old['pages'][0]['summary']['terminalFooters']
    rows.append(dict(faultID=fault,label=label,newVersionAccepted=True,legacyTerminalRejected=True))
try:
    decode_pages(bytes(1024),version='4.0.0')
except ValueError:
    pass
else:
    raise AssertionError('Unknown diagnostic version accepted')
with a.output.open('x') as f:
    json.dump(dict(status='passed-version-scoped-home-phase-decoder',cases=rows,unknownVersionRejected=True,hardwareReportsSent=0,cameraQualified=False),f,indent=2)
    f.write('\n')
print('Three new phase records accepted; legacy and unknown-version controls rejected.')
