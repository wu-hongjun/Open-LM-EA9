#!/usr/bin/env python3
"""Independent negative controls for the exact v3 writer; synthetic fixture only.

Expected invariants come from append's fail latch, retention filters, and the
motion writer's sample_count/sample_next update; not decoder implementation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[4]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--decoder', type=Path, default=ROOT/'scripts/startup_diagnostic_v3.py')
p.add_argument('--fixture', type=Path, default=ROOT/'artifacts/private/trace35-suite8/synthetic.bin')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
spec = importlib.util.spec_from_file_location('reviewed_decoder', a.decoder)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
base = a.fixture.read_bytes()
assert len(base) == 1024 and base[:4] == b'E9S3'
rows = []

def crc(b, slot):
    at = slot*64
    b[at+60:at+64] = zlib.crc32(b[at:at+60]).to_bytes(4,'little')

def edit(b, slot, offset, value):
    b = bytearray(b)
    b[slot*64+offset:slot*64+offset+len(value)] = value
    crc(b, slot)
    return b

def run(name, b, condition):
    try:
        r = module.decode_pages(bytes(b))
        assert not r['cameraAcceptanceProven'] and not r['installationVerificationPerformed']
        ok = bool(condition(r))
        detail = None if ok else {k:r['pages'][0]['summary'].get(k) for k in
            ('snapshotStatus','eventSnapshotComplete','motionSnapshotComplete','terminalFooters')}
    except Exception as e:
        ok,detail = False, repr(e)
    rows.append(dict(case=name,passed=ok,detail=detail))

def untrusted(r, slot):
    return r['pages'][slot].get('recordTrust') != 'writer-consistent'

run('compiled-writer-positive',base,lambda r:r['pages'][0]['summary']['snapshotStatus']=='complete' and len(r['pages'][0]['summary']['terminalFooters'])==4)
# A later CRC-valid terminal payload is locally inspectable after corruption,
# but cannot be associated through a gap in this fail-stop append writer.
for slot in (0,1,4,11):
    for damage in ('erased','crc'):
        b=bytearray(base)
        if damage=='erased': b[slot*64:(slot+1)*64]=b'\xff'*64
        else: b[slot*64+20]^=1
        run(f'snapshot-{slot}-{damage}-terminal-association',b,
            lambda r:all(untrusted(r,x) for x in range(12,16)))
for slot in (12,13,14):
    for damage in ('erased','crc','semantic'):
        b=bytearray(base)
        if damage=='erased': b[slot*64:(slot+1)*64]=b'\xff'*64
        elif damage=='crc': b[slot*64+20]^=1
        else: b=edit(b,slot,20,b'\x01') # footer reserved byte, CRC repaired
        run(f'footer-{slot}-{damage}-must-not-recover-trust',b,
            lambda r,slot=slot:all(untrusted(r,x) for x in range(slot+1,16))
                and len(r['pages'][0]['summary']['terminalFooters'])==slot-12)
# Valid new boot cannot fill an earlier boot's planned slot, nor allow its later footers.
b=bytearray(base)
second=bytearray(base[:64]);second[6]=2;second[8:10]=(1).to_bytes(2,'little')
second[48]=28;second[60:64]=zlib.crc32(second[:60]).to_bytes(4,'little');b[64:128]=second
run('new-cohort-breaks-previous-terminal-chain',b,lambda r:all(untrusted(r,x) for x in range(12,16)))
# Valid short snapshot plus an extra same-cohort event cannot be called complete.
b=bytearray(base)
for at,value in ((32,b'\0\0'),(47,b'\0\0')): b=edit(b,0,at,value)
b[4*64:]=b'\xff'*(12*64)
extra=bytearray(base[4*64:5*64]);b[4*64:5*64]=extra
run('extra-child-outside-plan-is-not-complete',b,lambda r:r['pages'][0]['summary']['snapshotStatus']!='complete')
# The pinned writer filters these before the RAM ring.
for kind,flags in ((11,0),(18,0),(14,0),(15,0),(14,1),(15,1)):
    b=edit(base,4,16,bytes((kind,0,flags)))
    run(f'filtered-kind-{kind}-flags-{flags}',b,lambda r:untrusted(r,4) and not r['pages'][0]['summary']['eventSnapshotComplete'])
# Build a legal unfrozen ring from the existing structure. Unsaturated cursor
# equals count modulo four; saturation makes total writes unknowable.
raw=bytearray(b''.join(base[x*64+12:x*64+60] for x in (1,2,3)))
raw[2]=0;raw[24:32]=b'\0'*8;raw[43]=0;raw[47]=0
for slot in range(1,4): raw[64+12*slot:76+12*slot]=raw[64:76]

def motion(b,raw):
    for i in range(3): b=edit(b,i+1,12,raw[48*i:48*(i+1)])
    return b
for count in (4,5,6,65534):
    for cursor in range(4):
        m=bytearray(raw);m[44:46]=count.to_bytes(2,'little');m[46]=cursor
        correct=cursor==count%4
        run(f'unsaturated-count-{count}-cursor-{cursor}',motion(base,m),
            lambda r,correct=correct:(not r['pages'][0]['summary']['motion']['writerIssues'])==correct)
for cursor in range(4):
    m=bytearray(raw);m[44:46]=b'\xff\xff';m[46]=cursor
    order=[(cursor+i)%4 for i in range(4)]
    times=[0xfffffffe,0xffffffff,0,1]
    for i,slot in enumerate(order): struct.pack_into('<IihBB',m,64+slot*12,times[i],100+i,64,0,0)
    m[56:60]=(1).to_bytes(4,'little')
    run(f'saturated-count-wrap-cursor-{cursor}',motion(base,m),
        lambda r:r['pages'][0]['summary']['motion']['writerIssues']==[]
            and [x['position'] for x in r['pages'][0]['summary']['motion']['samplesOldestFirst']]==[100,101,102,103])
original_motion=bytearray(b''.join(base[x*64+12:x*64+60] for x in (1,2,3)))
for name,at,value in (('sample-invalid-state',74,128),('unused-sample-nonzero',76,1),('last-sample-ms-disagrees',56,21)):
    m=bytearray(original_motion);m[at]=value
    run(name,motion(base,m),lambda r:bool(r['pages'][0]['summary']['motion']['writerIssues'])
        and not r['pages'][0]['summary']['motionSnapshotComplete'])
# Labels must distinguish ownership sequence from the emitted wire sequence,
# and COMPLETE's session-validity bit from ordinary control context.
for kind,flags,meaning in ((14,2,'owning-request-sequence'),(15,2,'owning-request-sequence'),(14,4,'transmitted-frame-sequence'),(15,4,'transmitted-frame-sequence')):
    b=edit(base,4,16,bytes((kind,0x29,flags,0xfe)))
    run(f'sequence-label-{kind}-{flags}',b,lambda r,meaning=meaning:r['pages'][4]['events'][0].get('sequenceMeaning')==meaning)
for flags in (0,2,128,130):
    b=edit(base,4,16,bytes((17,0x29,flags,0xfe)))
    run(f'complete-session-label-{flags}',b,lambda r,flags=flags:
        r['pages'][4]['events'][0].get('captureFlags',{}).get('sessionStillValid')==bool(flags&2)
        and r['pages'][4]['events'][0].get('captureFlags',{}).get('sendReturnedSuccess')==bool(flags&128))
for kind,flags,label in ((12,0,'offerAccepted'),(12,128,'offerAccepted'),(16,132,'shutdownAdmitted')):
    b=edit(base,4,16,bytes((kind,0x29,flags,0xfe)))
    run(f'admission-label-{kind}-{flags}',b,lambda r,flags=flags,label=label:
        r['pages'][4]['events'][0].get('captureFlags',{}).get(label)==bool(flags&128))
report=dict(checks=len(rows),passed=sum(x['passed'] for x in rows),failed=[x['case'] for x in rows if not x['passed']],
    decoderSHA256=hashlib.sha256(a.decoder.read_bytes()).hexdigest(),fixtureSHA256=hashlib.sha256(base).hexdigest(),
    syntheticDataOnly=True,hardwareReportsSent=0,cameraQualified=False,cases=rows)
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
raise SystemExit(bool(report['failed']))
