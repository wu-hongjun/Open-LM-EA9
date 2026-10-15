#!/usr/bin/env python3
"""Offline exact-source cohort properties and CRC-recomputed failing controls."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import runpy
import shutil
import subprocess
import sys
import zlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PINS={
 '3.2.0':('e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df','677d1f19c82acc9a79281882f1c0b70b2b33ddae189048538e71c18fe2abd6b2'),
 '3.3.0':('adc4b5de9a717b1a573425006ef565962bf5c56ab2233a4eca9192feb7ad11cd','302b5538ffd47ff72912b550073105f5dfec147db7fc27ec979be15f0a256d05'),
 '3.4.0':('fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9','8e358720a959a79a4636e1a9310fc23c08af9fa50539396d6946be6194c25a9a'),
 '3.5.0':('04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632','a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de')}
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',required=True,type=Path)
 parser.add_argument('--build',type=Path,default=ROOT/'artifacts/private/absolute35a')
 args=parser.parse_args();out=args.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(parents=True,exist_ok=False)
 decoder=ROOT/'scripts/decode-startup-diagnostics.py'
 assert sha(decoder.read_bytes())=='86357d857408608bb6e6a24cf568d0f67207ddf42109861f58af7d5a88ce5586'
 assert sha((HERE/'frozen_registry.py').read_bytes())=='e01c4b210577a22eec7cacd535a29ef31a272214247780e4432f7c958895ede8'
 legacy=runpy.run_path(str(decoder))['decode_pages']
 frozen=load('frozen_registry',HERE/'frozen_registry.py')
 evidence={'pins':{},'productionHistories':0,'versionDecodes':0,'controls':[], 'hardwareReportsSent':0,
 'installationVerificationPerformed':False,'cameraAcceptanceProven':False}
 for version,(image_sha,manifest_sha) in PINS.items():
  p=ROOT/'firmware/candidates'/version/'contax-zeiss-50-f1-4.bin'
  assert sha(p.read_bytes())==image_sha
  assert sha(p.with_suffix('.manifest.json').read_bytes())==manifest_sha
  frozen.resolve_candidate(ROOT,version)
  evidence['pins'][version]={'imageSHA256':image_sha,'manifestSHA256':manifest_sha,
   'traceSourceSHA256':json.loads(p.with_suffix('.manifest.json').read_text())['sources']['src/startup_trace.c']}
 for label in ('frozen','proposed'):
  work=out/label;(work/'scripts').mkdir(parents=True)
  shutil.copyfile(decoder,work/'scripts/decode-startup-diagnostics.py')
  shutil.copyfile(HERE/'frozen_registry.py',work/'scripts/startup_diagnostic_registry.py')
  (work/'firmware').mkdir();shutil.copytree(ROOT/'firmware/candidates',work/'firmware/candidates')
  if label=='proposed':
   for relative in ('firmware/upstream-hardening/next/test_decoder.py','firmware/upstream-hardening/next35/test_decoder.py'):
    target=work/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,target)
   runpy.run_path(str(HERE/'apply.py'))['apply'](work)
 sys.path.insert(0,str(out/'proposed/scripts'))
 proposed=load('proposed_registry',out/'proposed/scripts/startup_diagnostic_registry.py')
 evidence['proposedRegistrySHA256']=sha((out/'proposed/scripts/startup_diagnostic_registry.py').read_bytes())
 exes={}
 for version,src in [('3.2.0',ROOT/'firmware/upstream-diagnostic/build/src'),('3.5.0',args.build/'src')]:
  manifest=json.loads((ROOT/'firmware/candidates'/version/'contax-zeiss-50-f1-4.manifest.json').read_text())
  for name in ('startup_trace.c','startup_trace.h'):
   assert sha((src/name).read_bytes())==manifest['sources']['src/'+name]
  exe=out/('fixture-'+version)
  subprocess.run(['clang','-std=gnu99','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),str(HERE/'fixture.c'),str(src/'startup_trace.c'),'-o',str(exe)],check=True)
  exes[version]=exe
 def fixture(history,used=0,version='3.5.0',repeat=False):
  data=subprocess.check_output([str(exes[version]),*(['--repeat'] if repeat else []),str(used),*[str(x) for b in history for x in b]])
  assert len(data)==1024
  return data
 def decode(data,version='3.5.0',module=proposed):return module.decode_extended_pages(data,legacy,version)
 # Real serializer histories, with reboot following complete, zero-byte, and
 # torn snapshots. These test decoding/cohort semantics, not NVM hardware.
 histories=[[(a,0,64),(b,0,64),(c,0,64)] for a in (0,1,4,5,48,80) for b in (0,1,5,48) for c in (0,4)]
 histories += [[(12,page,cut),(5,0,64),(1,0,64)] for page in (1,2,3,4) for cut in (0,1,32,63)]
 rng=random.Random(250035)
 histories += [[(rng.randrange(100),rng.randrange(1,8),rng.choice((0,1,63,64))) for _ in range(rng.randrange(1,6))] for _ in range(160)]
 for version in ('3.2.0','3.5.0'):
  for idx,history in enumerate(histories):
   data=fixture(history,idx%17 if idx>=len(histories)-160 else 0,version)
   evidence['productionHistories']+=1
   for target in (('3.2.0',) if version=='3.2.0' else ('3.3.0','3.4.0','3.5.0')):
    d=decode(data,target);old=decode(data,target,frozen)
    assert d['semanticallyInconsistentPages']==0,(version,history,d)
    assert d['validPages']==old['validPages'] and d['appendFrontierSlot']==old['appendFrontierSlot']
    frontier=max((i+1 for i in range(16) if data[64*i:64*(i+1)]!=b'\xff'*64),default=0)
    assert d['appendFrontierSlot']==frontier and d['appendablePages']==16-frontier
    assert d['installationVerificationPerformed'] is False
    for p in d['pages']:
     if 'summary' in p and p.get('recordVersion')==2:
      assert p['summary']['eventSnapshotComplete']==old['pages'][p['slot']]['summary']['eventSnapshotComplete']
    evidence['versionDecodes']+=1
 repeated=fixture([(1,0,64),(2,0,64)],version='3.2.0',repeat=True)
 d=decode(repeated,'3.2.0');assert d['semanticallyInconsistentPages']==0
 assert sum(p.get('type')=='summary' for p in d['pages'])==6
 old=decode(repeated,'3.2.0',frozen)
 for a,b in zip(old['pages'],d['pages']):
  for key,value in a.items():assert b[key]==value
 evidence['legacyRepeatedFlushSummaries']=6
 full=fixture([(8,0,64)]);multi=fixture([(4,0,64),(4,0,64)])
 def mutate(data,slot,offset,value):
  d=bytearray(data);d[slot*64+offset]=value
  d[slot*64+60:slot*64+64]=zlib.crc32(d[slot*64:slot*64+60]).to_bytes(4,'little');return bytes(d)
 def relocate(data,origin,destination):
  d=bytearray(data);d[destination*64:(destination+1)*64]=d[origin*64:(origin+1)*64]
  d[origin*64:(origin+1)*64]=b'\xff'*64
  return mutate(d,destination,8,destination)
 controls={
 'summary-boot-after-slot':mutate(full,0,6,2),
 'event-boot-after-slot':mutate(full,1,6,16),
 'event-at-required-summary-slot':mutate(full,1,6,2),
 'event-beyond-maximum-span':relocate(full,2,15),
 'summary-planned-under-budget':mutate(full,0,47,4),
 'summary-dropped-without-eviction':mutate(full,0,42,1),
 'summary-nonboolean-handshake':mutate(full,0,13,2),
 'summary-nonboolean-capability':mutate(full,0,44,2),
 'summary-reserved-byte':mutate(full,0,59,1),
 'summary-rx-count-below-surviving-events':mutate(full,0,20,0),
 'summary-tx-count-below-surviving-events':mutate(full,0,22,0),
 'events-relocated-past-plan':relocate(full,2,5),
 'event-count-balanced-wrong-slots':mutate(mutate(full,1,7,3),2,7,4),
 'foreign-boot-events-relabeled':mutate(multi,3,6,1),
 'v1-record-in-v2-image':mutate(full,1,4,1),
 'duplicate-summary-cohort':mutate(multi,2,6,1),
 'unused-event-padding':mutate(fixture([(1,0,64)]),1,59,1),
 }
 # Equal aggregate count but impossible event-page ordering: 3+4+1 vs 4+4.
 d=bytearray(full);d[3*64:4*64]=d[2*64:3*64]
 d=mutate(d,3,8,3);d=mutate(d,1,7,3);d=mutate(d,3,7,1)
 controls['equal-total-wrong-layout']=d
 d=bytearray(mutate(multi,3,6,1));d[64:128]=b'\xff'*64
 controls['borrow-events-across-other-cohort']=bytes(d)
 for name,data in controls.items():
  old=decode(data,module=frozen);new=decode(data)
  assert new['semanticallyInconsistentPages']>0,(name,new)
  assert old['invalidPages']==0,(name,old)
  evidence['controls'].append({'case':name,'syntheticOnly':True,'fixtureSHA256':sha(data),
   'frozenInvalidPages':old['invalidPages'],'proposalInconsistentPages':new['semanticallyInconsistentPages'],
   'frozenComplete':[p['slot'] for p in old['pages'] if p.get('summary',{}).get('eventSnapshotComplete')],
   'proposalComplete':[p['slot'] for p in new['pages'] if p.get('summary',{}).get('eventSnapshotComplete')]})
  (out/(name+'.bin')).write_bytes(data)
 # Corruption of an earlier page must not erase surviving later CRC-valid facts.
 torn=bytearray(full);torn[64+20]^=1
 d=decode(torn);assert d['semanticallyInconsistentPages']==0
 assert d['pages'][0]['summary']['persistedEvents']==4
 assert d['pages'][0]['summary']['eventSnapshotStatus']=='partial'
 # A damaged summary does not make independently intact event pages impossible.
 orphan=bytearray(full);orphan[20]^=1
 d=decode(orphan);assert d['semanticallyInconsistentPages']==0 and d['unassociatedPages']==2
 assert all(p['recordTrust']=='unassociated' for p in d['pages'] if p.get('type')=='events')
 # Enumerate source-impossible field mutations, always recomputing CRC.
 mutations=[]
 for slot in (0,1,2):
  for value in range(slot+2,17):mutations.append(mutate(full,slot,6,value))
 for value in range(49):
  if value!=8:mutations.append(mutate(full,0,47,value))
 for offset in (13,44):
  for value in range(2,256):mutations.append(mutate(full,0,offset,value))
 for offset in range(49,60):mutations.append(mutate(full,0,offset,1))
 for version in ('3.3.0','3.4.0','3.5.0'):
  for data in mutations:
   d=decode(data,version)
   assert d['invalidPages'] or d['semanticallyInconsistentPages']
   assert not any(p.get('summary',{}).get('eventSnapshotComplete') for p in d['pages'])
 evidence['mutationDecodes']=3*len(mutations)
 # Actual public CLI: exact published prefix/version, synthetic log tail only.
 data=controls['events-relocated-past-plan']
 for version in PINS:
  flash=bytearray(b'\xff'*0x20000);flash[0x4000:0x4003]=bytes(map(int,version.split('.')))
  flash[0x5000:0xa000]=(ROOT/'firmware/candidates'/version/'contax-zeiss-50-f1-4.bin').read_bytes()
  flash[0x9c00:0xa000]=fixture([(5,0,64),(4,0,64)],version='3.2.0') if version=='3.2.0' else data
  path=out/('synthetic-'+version+'.flash.bin');path.write_bytes(flash)
  for label in ('frozen','proposed'):
   r=subprocess.run([sys.executable,str(out/label/'scripts/decode-startup-diagnostics.py'),str(path)],check=True,capture_output=True,text=True)
   decoded=json.loads(r.stdout);assert decoded['installationVerificationPerformed'] is False
   assert decoded['cameraAcceptanceProven'] is False and decoded['hardwareReportsSent']==0
   if version!='3.2.0':assert decoded['pages'][0]['summary']['eventSnapshotComplete']==(label=='frozen')
   (out/(label+'-'+version+'.json')).write_text(r.stdout)
 # Runner-level source controls: a changed C/header must fail before decoding.
 evidence['sourcePinFailingControls']=[]
 for name in ('startup_trace.c','startup_trace.h'):
  bad=out/('wrong-source-'+name);(bad/'src').mkdir(parents=True)
  for source_name in ('startup_trace.c','startup_trace.h'):
   raw=(args.build/'src'/source_name).read_bytes()
   (bad/'src'/source_name).write_bytes(raw+(b'\n' if name==source_name else b''))
  r=subprocess.run([sys.executable,str(HERE/'run.py'),'--build',str(bad),'--output',str(out/('rejected-'+name))],capture_output=True,text=True)
  assert r.returncode!=0 and 'AssertionError' in r.stderr,(name,r.returncode,r.stderr)
  evidence['sourcePinFailingControls'].append(name)
 for version,(image_sha,manifest_sha) in PINS.items():
  p=ROOT/'firmware/candidates'/version/'contax-zeiss-50-f1-4.bin'
  assert sha(p.read_bytes())==image_sha and sha(p.with_suffix('.manifest.json').read_bytes())==manifest_sha
 evidence['existingDecoderChecks']=[]
 for directory in ('next','next35'):
  work=out/'proposed';test_output=work/'artifacts/private'/directory;test_output.parent.mkdir(parents=True,exist_ok=True)
  r=subprocess.run([sys.executable,str(work/'firmware/upstream-hardening'/directory/'test_decoder.py'),'--output',str(test_output)],check=True,capture_output=True,text=True)
  evidence['existingDecoderChecks'].append(r.stdout.strip())
 evidence['sourceSHA256']={p.name:sha(p.read_bytes()) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.c')}
 evidence['status']='host-only-proposal-tested-offline'
 evidence['limits']='Synthetic bytes and inert host flash; CRC consistency is not authenticity. No unit corruption observed, installation verification, hardware behavior, camera acceptance or firmware modification.'
 (out/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
 print(json.dumps({k:v for k,v in evidence.items() if k not in ('sourceSHA256','pins','controls')},indent=2))
 print('frozen semantic failing controls:',len(evidence['controls']))
if __name__=='__main__':main()
