#!/usr/bin/env python3
"""Synthetic 3.9 failed-home ABI, old-version rejection and cohort controls."""
import argparse, hashlib, json, struct, sys, zlib
from pathlib import Path
if not __debug__:raise SystemExit('Required assertions disabled')
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from startup_diagnostic_v3 import decode_pages,decode_motion
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
assert a.output.resolve().is_relative_to(ROOT/'artifacts/private')
rows=[]
def page(slot,kind,payload,chunk=0):
 b=bytearray(64);b[:4]=b'E9S3';b[4:8]=bytes((3,kind,1,1));struct.pack_into('<H',b,8,slot);b[10]=chunk;b[12:60]=payload;struct.pack_into('<I',b,60,zlib.crc32(b[:60]));return bytes(b)
def cohort(raw,phase):
 s=bytearray(48);s[24:27]=bytes((14,1,phase));s[37]=3
 return page(0,1,s)+b''.join(page(i+1,3,raw[i*48:(i+1)*48],i) for i in range(3))+b'\xff'*(12*64)
def check(name,raw,valid=True):
 d=decode_pages(cohort(raw,raw[113]),version='3.9.0');s=d['pages'][0]['summary'];m=s['motion']
 assert not m['valid'] and bool(m['writerIssues'])!=valid,(name,m)
 assert (s['snapshotStatus']=='complete')==valid,(name,s)
 assert s['motionSnapshotComplete']==valid
 assert d['installationVerificationPerformed']==d['cameraAcceptanceProven']==False
 rows.append(name);return m
for phase,flag in ((17,0),(18,1),(19,0),(19,1)):
 for start,end,iteration in ((100,400,399),(0xfffffff0,0x20,0xffffffff)):
  for count in (0,1,254,255):
   b=bytearray(144);b[112:116]=bytes((0x39,phase,flag,count))
   struct.pack_into('<IIiiIII',b,116,start,end,-2147483648,2147483647,start,1000000 if phase==19 else 300,iteration)
   m=check(f'phase-{phase}-flag-{flag}-start-{start}-count-{count}',b)['homeDiagnostic']
   assert m['phaseID']==phase and m['driveQualified']==bool(flag)
   assert m['initialPosition']==-2147483648 and m['stillnessAnchorPosition']==2147483647
   assert m['requestCountIsLowerBound']==(count==255) and m['consumedNonStopRequestsSaturating']==count
   assert m['phaseElapsedTicksModulo32']==(end-start)&0xffffffff
   assert m['lastIterationToCutoffTicksModulo32']==(end-iteration)&0xffffffff
   for legacy in ('3.7.0','3.8.0'):
    old=decode_pages(cohort(b,phase),version=legacy)
    assert old['semanticallyInconsistentPages']>0 and not old['pages'][0]['summary']['motionSnapshotComplete']
    rows.append(f'legacy-{legacy}-reject-{phase}-{flag}-{start}-{count}')
# Recomputed CRC must not make impossible writer payloads trustworthy.
pristine=bytearray(144);pristine[112:116]=bytes((0x39,17,0,3));struct.pack_into('<IIiiIII',pristine,116,10,310,0,20,300,300,309)
for at,value,label in ((112,0,'tag'),(113,16,'phase'),(114,2,'reserved-flag'),(114,1,'drive-qualification'),(0,1,'mixed-servo')):
 b=pristine[:];b[at]=value;check('bad-'+label,b,False)
b=pristine[:];b[113]=18;check('settle-without-drive',b,False)
for phase,polls in ((17,1000000),(18,1000000),(19,999999),(19,1000001)):
 b=pristine[:];b[113]=phase;b[114]=int(phase==18);struct.pack_into('<I',b,136,polls)
 check(f'bad-poll-budget-{phase}-{polls}',b,False)
for version in ('3.7.0','3.8.0','3.9.0'):
 m=decode_motion(bytes(144),version=version);assert not m['valid'] and not m['writerIssues'] and 'homeDiagnostic' not in m
 rows.append('empty-'+version)
# Every missing/torn motion chunk prevents an assembled home diagnosis.
fixture=cohort(pristine,17)
for slot in (1,2,3):
 for at in range(64):
  b=bytearray(fixture);b[slot*64+at]^=1
  d=decode_pages(b,version='3.9.0');s=d['pages'][0]['summary']
  assert not s['motionSnapshotComplete'] and 'motion' not in s
  rows.append(f'crc-{slot}-{at}')
 b=bytearray(fixture);b[slot*64:(slot+1)*64]=b'\xff'*64
 s=decode_pages(b,version='3.9.0')['pages'][0]['summary'];assert not s['motionSnapshotComplete'] and 'motion' not in s
 rows.append('missing-'+str(slot))
# Cross-cohort data is never presented as a complete failed-home snapshot.
b=bytearray(fixture);b[64+6]=2;b[124:128]=zlib.crc32(b[64:124]).to_bytes(4,'little')
s=decode_pages(b,version='3.9.0')['pages'][0]['summary'];assert not s['motionSnapshotComplete'] and 'motion' not in s
rows.append('cross-cohort')
for f in (decode_motion,decode_pages):
 try:f(bytes(144 if f is decode_motion else 1024),version='3.10.0')
 except ValueError:rows.append('unknown-version-'+f.__name__)
 else:raise AssertionError('Unknown version admitted')
report=dict(status='passed-version-scoped-failed-home-decoder',checks=len(rows),cases=rows,syntheticDataOnly=True,decoderSHA256=hashlib.sha256((ROOT/'scripts/startup_diagnostic_v3.py').read_bytes()).hexdigest(),hardwareReportsSent=0,cameraQualified=False,physicalHomingFixEstablished=False,shutterFixEstablished=False)
with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
