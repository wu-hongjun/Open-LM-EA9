#!/usr/bin/env python3
"""Extend pinned original-instruction factory tests with capture/VD/re-arm cycles.

All seeds are synthetic. No raw camera frames or device interfaces are used.
"""
import argparse,hashlib,json,runpy
from pathlib import Path
if not __debug__:raise RuntimeError('Assertions required')
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
assert args.output.resolve().is_relative_to(ROOT/'artifacts/private')
PINS={
 'firmware/upstream-hardening/lanes/04-factory/test_factory_contracts.py':'d87ce8a7aab8f888c90cc5542b998efc8c978d12258befa0c359e90c5be7c5df',
 'research/stock-1.8/oracle.py':'ea53452f711c84d156e5bc665156fe2a48211014bcc6a59baa595811e2258d1e',
 'research/stock-1.8/config.py':'07e8ec5648d7cd53a1ee03c1d1c540a8545c2f179b58910cb8d27eab6f2cc597'}
for name,digest in PINS.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
# The pinned runner consumes --output, requires a new directory, executes its
# prior contracts and returns only a host oracle with the documented cuts.
d=runpy.run_path(str(ROOT/next(iter(PINS))))
B=d['BASE']; rows=[]
for cycles in (1,2,4):
    m=d['machine']()
    for cycle in range(cycles):
        m.set(B+0x520,3,1)
        d['receive'](m,d['frame']())
        m.run(0x5120)
        assert m.get(B+0x51f,1)==5
        before=len(m.sent);m.run(0x5260)
        assert len(m.sent)==before+1
        m.run(0x5188);m.run(0x5280)
        assert m.get(B+0x51f,1)==1
        after=len(m.sent);schedules=len(m.scheduled)
        for _ in range(8):m.run(0x5120)
        assert len(m.sent)==after and len(m.scheduled)==schedules
        assert m.get(B+0x51f,1)==1
        # Original dispatcher with ordinary readiness frame returns to mode4.
        d['receive'](m,d['frame'](0x0a))
        m.run(0x58a4)
        assert m.get(B+0x51f,1)==4
        assert len(m.sent)==after+1
        m.run(0x5120);m.run(0x5120)
        assert m.get(B+0x520,1)==13
    rows.append({'captureRearmCycles':cycles,'silentVDPulsesPerCycle':8,'rearmsConnectedMode':True})
assert hashlib.sha256(d['cfg'].firmware.read_bytes()).hexdigest()==d['FIRMWARE_SHA256']
result={'runnerSHA256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'status':'pass-bounded-stock-capture-rearm','stockApplicationSHA256':d['FIRMWARE_SHA256'],'pinnedDependencies':PINS,'cases':rows,'cuts':'Inherited pinned lane04 oracle; explicit callbacks, UART/DMA/timer stubs and synthetic RAM. No actual ISR timing.','wrongModelRejected':'Raw echo alone resumes periodic status','hardwareAccess':False}
(d['cfg'].output/'capture-status-results.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'factory-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'captureRearmCases':len(rows),'cycles':sum(x['captureRearmCycles'] for x in rows),'passed':True}))
