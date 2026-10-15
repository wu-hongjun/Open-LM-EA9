#!/usr/bin/env python3
"""Validate the exact frozen 3.3 composition offline; no device APIs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args();b=a.build.resolve();out=a.output.resolve();out.mkdir(exist_ok=False)
sha=lambda data:hashlib.sha256(data).hexdigest()
m=json.loads((b/'manifest.json').read_text())
image=(b/'contax-zeiss-50-f1-4.bin').read_bytes()
assert sha(image)==m['imageSHA256'] and len(image)==20480
assert image[0x4c00:]==b'\xff'*1024
assert m['codeMarginBeforeDiagnostics']>=256 and not m['cameraQualified']
assert image==(ROOT/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.bin').read_bytes()
assert image==(ROOT/'apps/macos/Sources/DeviceKit/Resources/ea9-af-upstream-hardened.bin').read_bytes()
for name,digest in m['sources'].items():assert sha((b/name).read_bytes())==digest,name
rows=[]
def run(name,cmd,expected=0):
    r=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,text=True,timeout=180)
    (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
    assert (r.returncode==0)==(expected==0),(name,r.returncode,r.stderr[-1200:])
    rows.append(dict(name=name,exitCode=r.returncode,expectedSuccess=expected==0))
    return r
lane=ROOT/'firmware/upstream-hardening/lanes/10-integration'
for name,script,extra in [('commits','run.py',['--already-applied']),('capture','regression.py',[]),('diagnostics','diagnostics.py',[])]:
    run(name,[sys.executable,lane/script,'--source',b,'--output',out/name,*extra])
run('arm-writer',[ROOT/'tools/rea-analysis/venv/bin/python',ROOT/'scripts/test-startup-flash-arm.py','--version','3.3.0','--build',b,'--output',out/'arm-writer.json'])
# Synthetic full-flash fixtures contain public application bytes only. This
# decoder check is separate from installation verification and native backup.
for version in ('3.2.0','3.3.0'):
    pristine=(ROOT/'firmware/candidates'/version/'contax-zeiss-50-f1-4.bin').read_bytes()
    flash=bytearray(b'\xff'*0x20000);flash[0x4000:0x4003]=bytes(map(int,version.split('.')));flash[0x5000:0xa000]=pristine
    path=out/('synthetic-'+version+'.bin');path.write_bytes(flash)
    result=out/('decoded-'+version+'.json')
    run('decode-'+version,[sys.executable,ROOT/'scripts/decode-startup-diagnostics.py',path,'--output',result])
    decoded=json.loads(result.read_text())
    assert decoded['immutableCodePrefixMatches'] and not decoded['installationVerificationPerformed']
    assert decoded['erasedPages']==16 and decoded['firmwareVersion']==version
    flash[0x6000]^=1;path=out/('bad-prefix-'+version+'.bin');path.write_bytes(flash)
    run('reject-prefix-'+version,[sys.executable,ROOT/'scripts/decode-startup-diagnostics.py',path],expected=1)
result=dict(status='passed-exact-frozen-offline-composition',imageSHA256=m['imageSHA256'],buildManifestSHA256=sha((b/'manifest.json').read_bytes()),
            sourceFilesMatched=len(m['sources']),checks=rows,hardwareReportsSent=0,cameraQualified=False,
            limits='Finite host IRQ cuts, simulated peripherals/NVM and compiled writer address bounds; physical timing, exposure and optical AF remain unqualified.')
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
