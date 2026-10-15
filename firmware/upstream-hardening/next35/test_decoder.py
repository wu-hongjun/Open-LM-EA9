#!/usr/bin/env python3
"""Exact published decoder pins and synthetic v2 pages; offline only."""
import argparse,copy,hashlib,json,shutil,subprocess,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
repo=out/'repository';(repo/'scripts').mkdir(parents=True)
for n in ['decode-startup-diagnostics.py','startup_diagnostic_registry.py']:shutil.copyfile(ROOT/'scripts'/n,repo/'scripts'/n)
for v in ['3.2.0','3.3.0','3.4.0','3.5.0']:
 d=repo/'firmware/candidates'/v;d.mkdir(parents=True)
 for n in ['contax-zeiss-50-f1-4.bin','contax-zeiss-50-f1-4.manifest.json']:shutil.copyfile(ROOT/'firmware/candidates'/v/n,d/n)
reg=repo/'firmware/candidates/diagnostic-registry.json';shutil.copyfile(ROOT/'firmware/candidates/diagnostic-registry.json',reg)
registry=json.loads(reg.read_text());rows=[]
def flash(version):
 b=bytearray(b'\xff'*0x20000);b[0x4000:0x4003]=bytes(map(int,version.split('.')));b[0x5000:0xa000]=(repo/'firmware/candidates'/version/'contax-zeiss-50-f1-4.bin').read_bytes();return b
def page():
 b=bytearray(64);b[:4]=b'E9S2';b[4:8]=bytes([2,1,1,1]);b[14:16]=(16).to_bytes(2,'little');b[45]=1;b[48]=1;b[60:64]=zlib.crc32(b[:60]).to_bytes(4,'little');return b
def check(name,b,ok,expected=None,native=False):
 path=out/'synthetic-flash.bin';path.write_bytes(b)
 if native:
  path=out/'synthetic.ea9backup';path.mkdir(exist_ok=True);(path/'flash.bin').write_bytes(b)
  m={'flashReadPasses':2,'auxiliaryReadPasses':2,'files':{'flash.bin':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}}}
  if native=='bad':m['files']['flash.bin']['sha256']='0'*64
  (path/'manifest.json').write_text(json.dumps(m))
 r=subprocess.run([sys.executable,repo/'scripts/decode-startup-diagnostics.py',path],capture_output=True,text=True,timeout=20)
 assert (r.returncode==0)==ok,(name,r.stderr)
 if expected:
  j=json.loads(r.stdout);assert j['validPages']==1 and j['pages'][0]['summary']['fault']==expected,(name,j)
 if ok:assert json.loads(r.stdout)['installationVerificationPerformed'] is False
 rows.append(dict(case=name,expectedSuccess=ok,exitCode=r.returncode))
for version,meaning in [('3.3.0','encoder-overflow'),('3.4.0','encoder-coordinate-capacity'),('3.5.0','encoder-coordinate-capacity')]:
 b=flash(version);b[0x9c00:0x9c40]=page();check(version+'-v2-fault',b,True,meaning)
 check(version+'-native',b,True,meaning,native=True);check(version+'-native-hash',b,False,native='bad')
 for key in ['imageSHA256','manifestSHA256','immutablePrefixSHA256']:
  j=copy.deepcopy(registry);j['versions'][version][key]='0'*64;reg.write_text(json.dumps(j));check(version+'-'+key,b,False);reg.write_text(json.dumps(registry))
 for field in [4,47,48]:
  bad=bytearray(b);bad[0x9c00+field]=3 if field==4 else (49 if field==47 else 2);bad[0x9c3c:0x9c40]=zlib.crc32(bad[0x9c00:0x9c3c]).to_bytes(4,'little')
  check(version+'-invalid-page-'+str(field),bad,True)
  # Invalid records remain visible as invalid; they never become valid summaries.
  j=subprocess.run([sys.executable,repo/'scripts/decode-startup-diagnostics.py',out/'synthetic-flash.bin'],capture_output=True,text=True,check=True)
  assert json.loads(j.stdout)['invalidPages']==1 and json.loads(j.stdout)['validPages']==0
 for offset in [0x5000,0x9bff]:
  bad=bytearray(b);bad[offset]^=1;check(version+'-prefix-'+str(offset),bad,False)
 legacy=flash('3.2.0');legacy[0x9c00:0x9c40]=page();check('legacy-v2-reject-'+version,legacy,True)
 j=subprocess.run([sys.executable,repo/'scripts/decode-startup-diagnostics.py',out/'synthetic-flash.bin'],capture_output=True,text=True,check=True);assert json.loads(j.stdout)['validPages']==0
b=flash('3.4.0');b[0x4001]=6;check('unknown-version',b,False)
(out/'result.json').write_text(json.dumps(dict(status='passed',checks=rows,hardwareReportsSent=0,syntheticFramesOnly=True),indent=2)+'\n');print(f'{len(rows)} decoder pin/page/native checks pass')
