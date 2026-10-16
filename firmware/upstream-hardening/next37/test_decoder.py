#!/usr/bin/env python3
"""Check source-produced v3 records and hostile/missing page interpretations offline."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'scripts'))
from startup_diagnostic_v3 import decode_pages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--fixture', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
out = a.output.resolve()
assert out.is_relative_to(ROOT/'artifacts/private')
out.mkdir(exist_ok=False)
data = a.fixture.read_bytes()
assert len(data) == 1024
rows = []


def check(name, payload, condition):
    result = decode_pages(bytes(payload))
    assert condition(result), (name, result)
    assert not result['installationVerificationPerformed'] and not result['cameraAcceptanceProven']
    rows.append(name)
    return result


def edit(slot, at, value):
    b = bytearray(data)
    b[slot*64+at:slot*64+at+len(value)] = value
    b[slot*64+60:slot*64+64] = zlib.crc32(b[slot*64:slot*64+60]).to_bytes(4, 'little')
    return b


pristine = check('actual-compiled-writer-fixture', data,
    lambda r: r['validPages'] >= 8 and not r['invalidPages'] and not r['semanticallyInconsistentPages'])
summary = next(e for e in pristine['pages'] if e.get('type') == 'summary')
start = summary['slot']
snapshot = summary['summary']
assert snapshot['eventSnapshotComplete'] and snapshot['motionSnapshotComplete']
assert snapshot['motion']['writerIssues'] == []
assert snapshot['terminalFooters'][-1]['kind'] == 'terminal-st-fail'
(out/'decoded-synthetic.json').write_text(json.dumps(pristine, indent=2)+'\n')

occupied = [e['slot'] for e in pristine['pages'] if e['state'] == 'valid']
for slot in occupied:
    for byte in range(64):
        b = bytearray(data); b[slot*64+byte] ^= 1
        check(f'crc-byte-{slot}-{byte}', b,
            lambda r, slot=slot: r['pages'][slot]['state'] == 'invalid-or-torn')
    for cut in range(65):
        b = data[:slot*64+cut] + b'\xff'*(1024-slot*64-cut)
        result = decode_pages(b)
        assert result['validPages'] <= len(occupied)
        assert not result['installationVerificationPerformed']
        # No terminal marker may be fabricated from an absent/torn page.
        actual_footers = [e for e in result['pages'] if e.get('type') == 'terminal-footer']
        assert len(actual_footers) <= sum(e.get('type') == 'terminal-footer'
            for e in pristine['pages'] if e['slot'] <= slot)
        rows.append(f'power-cut-{slot}-{cut}')
for at, value in [(11, b'\x01'), (4, b'\x02'), (8, b'\x0f\x00'), (7, b'\x00')]:
    check('structural-header-'+str(at), edit(start, at, value),
        lambda r: r['pages'][start]['state'] == 'invalid-or-torn')
for at, value in [(12+25,b'\x02'), (12+38,b'\x01'), (12+35,b'\x21'),
        (12+36,b'\x21'), (12+37,b'\x02'), (6,b'\x02')]:
    check('writer-summary-'+str(at), edit(start, at, value),
        lambda r: bool(r['pages'][start].get('semanticIssues')))
for child in pristine['pages']:
    if child.get('type') not in ('events', 'motion', 'terminal-footer'):
        continue
    slot = child['slot']
    changed = edit(slot, 6, b'\x10')
    check('cross-cohort-'+str(slot), changed,
        lambda r, slot=slot: bool(r['pages'][slot].get('semanticIssues')
            or r['pages'][slot].get('associationIssues')))
    if child['type'] in ('events','motion'):
        check('wrong-chunk-'+str(slot), edit(slot,10,bytes([(child['chunk']+1)%3])),
            lambda r, slot=slot: bool(r['pages'][slot].get('semanticIssues')))
    else:
        check('wrong-footer-ordinal-'+str(slot), edit(slot,15,b'\x04'),
            lambda r, slot=slot: bool(r['pages'][slot].get('semanticIssues')) if child['footer']['ordinal'] != 4 else True)

# A fresh boot at a slot where the old writer lost power after zero bytes must
# remain a separate summary, never counted as the first boot's planned motion.
b = bytearray(data)
second = bytearray(data[:64]); second[6] = 2; second[8:10] = (1).to_bytes(2,'little')
second[12+36] = min(second[12+35], 4*(10-3))
second[60:64] = zlib.crc32(second[:60]).to_bytes(4,'little')
b[64:128] = second
check('zero-byte-failed-write-followed-by-new-cohort', b,
    lambda r: not r['pages'][0]['summary']['motionSnapshotComplete'])
check('all-erased-proves-no-outcome', b'\xff'*1024,
    lambda r: r['erasedPages'] == 16 and r['validPages'] == 0)
for length in (0, 1, 1023, 1025):
    try:
        decode_pages(b'\xff'*length)
    except ValueError:
        rows.append(f'reject-size-{length}')
    else:
        raise AssertionError(length)

report = {'status':'passed-v3-decoder-synthetic-boundaries', 'checks':len(rows),
    'fixtureSHA256':hashlib.sha256(data).hexdigest(),
    'decoderSHA256':hashlib.sha256((ROOT/'scripts/startup_diagnostic_v3.py').read_bytes()).hexdigest(),
    'syntheticDataOnly':True, 'hardwareReportsSent':0, 'cameraQualified':False,
    'cases':rows}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k != 'cases'}))
