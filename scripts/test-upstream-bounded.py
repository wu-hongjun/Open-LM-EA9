#!/usr/bin/env python3
"""Validate the exact frozen 3.4 composition offline; no device APIs."""
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
a=p.parse_args();b=a.build.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
sha=lambda data:hashlib.sha256(data).hexdigest()
m=json.loads((b/'manifest.json').read_text())
image=(b/'contax-zeiss-50-f1-4.bin').read_bytes()
assert sha(image)==m['imageSHA256'] and len(image)==20480
assert (b/'manifest.json').read_bytes()==(ROOT/'firmware/candidates/3.4.0/contax-zeiss-50-f1-4.manifest.json').read_bytes()
assert image[0x4c00:]==b'\xff'*1024
assert m['codeMarginBeforeDiagnostics']>=256 and not m['cameraQualified']
assert image==(ROOT/'firmware/candidates/3.4.0/contax-zeiss-50-f1-4.bin').read_bytes()
assert image==(ROOT/'apps/macos/Sources/DeviceKit/Resources/ea9-af-bounded-upstream.bin').read_bytes()
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
next_tests=ROOT/'firmware/upstream-hardening/next'
for name,script in [('coordinate','test_coordinate.py'),('query-ownership','test_query_ownership.py'),('query-flow','test_query_flow.py')]:
    run(name,[sys.executable,next_tests/script,'--source',b,'--output',out/name])
composition=ROOT/'firmware/upstream-hardening/followup/17-composition'
for name,script in [('home-inhibit','run_home.py'),('new-composition','run_composition.py')]:
    run(name,[sys.executable,composition/script,'--source',b,'--output',out/name])
stack_dir=ROOT/'firmware/upstream-hardening/followup/18-stack34'
stack_policy=json.loads((stack_dir/'policy.json').read_text())
# ELF DWARF and link-map path strings vary by fresh build directory. The
# published image, raw bytes, manifest and source inventory must stay exact.
# Rebind only those non-executable artifact containers for the fresh build;
# retain all reviewed addresses, callbacks, library frames and entry caveats.
assert stack_policy['pins']['contax-zeiss-50-f1-4.bin']==sha(image)
assert stack_policy['pins']['manifest.json']==sha((b/'manifest.json').read_bytes())
assert stack_policy['pins']['raw.bin']==sha((b/'raw.bin').read_bytes())
reference=json.loads((next_tests/'stack-reproduction.json').read_text())
assert reference['referenceELFSHA256']==stack_policy['pins']['hardened.elf']
assert reference['reviewedPolicySHA256']==sha((stack_dir/'policy.json').read_bytes())
objdump=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-objdump'
assert reference['objdumpSHA256']==sha(objdump.read_bytes())
for mode,expected_hash in reference['normalizedOutputSHA256'].items():
    rendered=subprocess.check_output([str(objdump),mode,str(b/'hardened.elf')],text=True)
    header=str(b/'hardened.elf')+':     file format elf32-littlearm'
    assert rendered.count(header)==1
    normalized=rendered.replace(header,'<ELF>:     file format elf32-littlearm')
    assert sha(normalized.encode())==expected_hash, 'Compiled metadata/disassembly changed: '+mode
rebound={}
for name in ['hardened.elf','hardened.map']:
    actual=sha((b/name).read_bytes())
    if actual!=stack_policy['pins'][name]:
        rebound[name]={'reviewed':stack_policy['pins'][name],'reproduced':actual}
        stack_policy['pins'][name]=actual
policy_path=out/'stack-reproduction-policy.json';policy_path.write_text(json.dumps(stack_policy,indent=2)+'\n')
run('stack',[sys.executable,stack_dir/'run.py','--build',b,'--policy',policy_path,'--output',out/'stack.json','--guards-output',out/'stack-guards.json'])
stack_result=json.loads((out/'stack.json').read_text())
assert stack_result['maximumAllVectorPriorityBytes']==1560 and not stack_result['recursiveComponents']

run('decoder-boundaries',[sys.executable,next_tests/'test_decoder.py','--output',out/'decoder-boundaries'])
run('arm-writer',[ROOT/'tools/rea-analysis/venv/bin/python',ROOT/'scripts/test-startup-flash-arm.py','--version','3.4.0','--build',b,'--output',out/'arm-writer.json'])
# Synthetic full-flash fixtures contain public application bytes only. This
# decoder check is separate from installation verification and native backup.
for version in ('3.2.0','3.3.0','3.4.0'):
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
            sourceFilesMatched=len(m['sources']),checks=rows,stackContainerPinsRebound=rebound,hardwareReportsSent=0,cameraQualified=False,
            limits='Finite host IRQ cuts, simulated peripherals/NVM and compiled writer address bounds; physical timing, exposure and optical AF remain unqualified.')
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
