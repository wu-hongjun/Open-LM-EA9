#!/usr/bin/env python3
"""Independent synthetic crash decoder acceptance, including actual C fixtures."""
import argparse,hashlib,json,struct,sys,zlib
from pathlib import Path
if not __debug__:raise SystemExit('Required assertions disabled')
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from startup_diagnostic_v4 import decode_pages
from startup_diagnostic_v3 import decode_pages as old_decode
p=argparse.ArgumentParser();p.add_argument('--fixture',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
assert a.output.resolve().is_relative_to(ROOT/'artifacts/private')
rows=[]
raw=a.fixture.read_bytes();assert len(raw)==1024
assert raw[:4]==b'E9S3' and raw[5]==5 and raw[10]==1 and raw[11]==32

def decode(data):
 d=decode_pages(data,version='4.1.0');assert d['installationVerificationPerformed']==d['cameraAcceptanceProven']==False
 return d

def patch(data,offset,value,recrc=True):
 b=bytearray(data);b[offset]=value
 if recrc:
  start=offset//64*64;struct.pack_into('<I',b,start+60,zlib.crc32(b[start:start+60]))
 return bytes(b)

def rejected(name,data):
 d=decode(data);page=d['pages'][0]
 assert page['state']!='valid' or page.get('semanticIssues'),(name,page)
 rows.append(name)

d=decode(raw);first=d['pages'][0]
assert d['validPages']==1 and d['semanticallyInconsistentPages']==0 and d['unassociatedPages']==0
assert first['recordTrust']=='writer-consistent' and 'summary' not in first
cp=first['checkpoint'];last=cp['lastForeground']
assert cp['resetCauseRaw']==32 and cp['resetCauses']==['watchdog'] and cp['crashResetObserved'] and cp['snapshotRecovered']
assert last['uptimeMS']==123456 and last['lastRxMS']==17 and last['rxFrames']==1 and last['faultID']==11 and last['stageID']==13
assert last['firstRxID']==last['lastRxID']==0x91
rows.append('actual-C-recovered-record-independent-of-ordinary-summary')
for version in ('3.7.0','3.8.0','3.9.0','4.0.0'):
 d=old_decode(raw,version=version);assert d['invalidPages']==1 and d['validPages']==0;rows.append('legacy-reject-'+version)
for version in ('3.9.0','4.0.0','4.2.0','99.0.0'):
 try:decode_pages(raw,version=version)
 except ValueError:rows.append('version-reject-'+version)
 else:raise AssertionError('wrong firmware version admitted: '+version)
for bit in range(512):rejected('bit-'+str(bit),patch(raw,bit//8,raw[bit//8]^(1<<(bit%8)),False))
for count in range(64):
 truncated=raw[:count]+b'\xff'*(1024-count)
 d=decode(truncated);assert d['validPages']==0;rows.append('torn-prefix-'+str(count))
for offset,value,label in ((4,4,'schema'),(5,6,'unknown-kind'),(6,2,'cohort'),(7,2,'count'),(8,1,'slot'),(9,1,'slot-high'),(10,2,'chunk'),(11,1,'cold-recovered'),(11,33,'mixed-cold-recovered'),(11,16,'external-recovered'),(11,0,'missing-cause-recovered'),(11,128,'unknown-cause')):
 rejected('CRC-valid-'+label,patch(raw,offset,value))
# CRC repair cannot authorize invalid retained summary fields.
for offset,value,label in ((24,15,'stage'),(25,2,'handshake'),(26,20,'fault'),(27,4,'pins'),(33,2,'capability-flag'),(34,2,'shutdown-flag'),(35,33,'retained-count'),(36,1,'planned-without-retained'),(37,1,'motion-count')):
 rejected('checkpoint-'+label,patch(raw,12+offset,value))
for offset in range(38,48):rejected('checkpoint-reserved-'+str(offset),patch(raw,12+offset,1))
for cause in (32,64):
 d=decode(patch(raw,11,cause));assert d['semanticallyInconsistentPages']==0 and d['pages'][0]['checkpoint']['snapshotRecovered'];rows.append('eligible-cause-'+str(cause))
# A baseline contains no retained summary, including old uptime or fault bytes.
b=bytearray(raw);b[10]=0;b[11]=1;b[12:60]=bytes(48);struct.pack_into('<I',b,60,zlib.crc32(b[:60]));baseline=bytes(b)
d=decode(baseline);assert d['validPages']==1 and d['semanticallyInconsistentPages']==0
assert not d['pages'][0]['checkpoint']['snapshotRecovered'] and 'lastForeground' not in d['pages'][0]['checkpoint']
rows.append('zero-baseline')
for offset in range(12,60):rejected('baseline-data-'+str(offset),patch(baseline,offset,1))
# A real boot record consumes slot0; ordinary summary starts its own cohort2.
combined=a.fixture.with_name('tail-998.bin').read_bytes();d=decode(combined)
assert d['semanticallyInconsistentPages']==0 and d['unassociatedPages']==0,d
assert d['pages'][1]['summary']['snapshotStatus']=='complete'
assert d['pages'][0]['boot']==1 and d['pages'][1]['boot']==2
rows.append('actual-C-baseline-plus-ordinary-complete-snapshot')
# CRC-valid child reparenting cannot assemble the other cohort's snapshot.
b=patch(combined,2*64+6,1)
d=decode(b);assert d['semanticallyInconsistentPages'] or d['unassociatedPages']
assert not d['pages'][1]['summary']['motionSnapshotComplete']
rows.append('cross-cohort-child-rejected')
# The41 writer halts on crash or corrupt occupied flash; later records cannot
# be trustworthy output of another permitted boot.
for label,barrier in [('crash',raw[:64]),('corruption',patch(combined,20,combined[20]^1,False)[:64])]:
 b=barrier+combined[64:];d=decode(b)
 assert d['semanticallyInconsistentPages']>0,(label,d)
 for e in d['pages'][1:]:
  if e['state']=='valid':assert e['recordTrust']!='writer-consistent',(label,e)
 rows.append('later-pages-after-'+label+'-untrusted')
# Actual scanner accepts later baseline after CRC-valid foreign headers. The
# decoder must not invent a CRC-storage latch from structural invalidity alone.
for i in range(9):
 fixture=a.fixture.with_name('tail-'+str(970+i)+'.bin').read_bytes();d=decode(fixture)
 assert d['pages'][1]['state']=='valid' and d['pages'][1]['recordTrust']=='writer-consistent',d
 rows.append('actual-C-foreign-CRC-valid-header-'+str(i))
# Occupied slots still determine append frontier; standalone boot at final slot.
b=bytearray(b'\xff'*1024);last=bytearray(baseline[:64]);last[6]=16;last[8]=15;struct.pack_into('<I',last,60,zlib.crc32(last[:60]));b[960:]=last
d=decode(bytes(b));assert d['appendExhausted'] and d['appendablePages']==0 and d['strandedErasedPages']==15
assert d['validPages']==1 and d['semanticallyInconsistentPages']==0
rows.append('last-slot-frontier')
report={'status':'passed-crash-decoder-synthetic-acceptance','checks':len(rows),'cases':rows,'fixtureSHA256':hashlib.sha256(raw).hexdigest(),'decoderSHA256':hashlib.sha256((ROOT/'scripts/startup_diagnostic_v4.py').read_bytes()).hexdigest(),'decoderCoreSHA256':hashlib.sha256((ROOT/'scripts/startup_diagnostic_v3.py').read_bytes()).hexdigest(),'hardwareReportsSent':0,'cameraQualified':False}
with a.output.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
