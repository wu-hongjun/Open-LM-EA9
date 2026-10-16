#!/usr/bin/env python3
"""Exact 3.7 offline acceptance; synthetic inputs, no adapter or app access."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
NEXT=ROOT/'firmware/upstream-hardening/next37'
FOLLOW=ROOT/'firmware/upstream-hardening/followup'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args();build=a.build.resolve();out=a.output.resolve()
assert build.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
out.mkdir(exist_ok=False)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
m=json.loads((build/'manifest.json').read_text())
published=ROOT/'firmware/candidates/3.7.0'
assert m['loaderVersion']==[3,7,0] and m['imageSHA256']=='6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5'
assert sha(build/'manifest.json')=='15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b'
assert (build/'manifest.json').read_bytes()==(published/'contax-zeiss-50-f1-4.manifest.json').read_bytes()
image=(build/'contax-zeiss-50-f1-4.bin').read_bytes()
assert sha(build/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
assert image==(published/'contax-zeiss-50-f1-4.bin').read_bytes()
assert image==(ROOT/'apps/macos/Sources/DeviceKit/Resources/ea9-af-targeted-trace.bin').read_bytes()
assert len(image)==20480 and image[0x4c00:]==b'\xff'*1024
assert m['codeAndDataEnd']==0x9ab8 and m['codeMarginBeforeDiagnostics']==328
assert m['staticRAMBytes']==3044 and m['reservedStackBytes']==8192 and not m['cameraQualified']
for n,h in m['sources'].items():assert sha(build/n)==h,n
rows=[]
def run(name,cmd):
    r=subprocess.run(list(map(str,cmd)),cwd=ROOT,capture_output=True,text=True,timeout=240)
    (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
    assert r.returncode==0,(name,r.returncode,r.stdout[-800:],r.stderr[-1800:])
    rows.append({'name':name,'exitCode':r.returncode})

for case in json.loads((NEXT/'test-inputs.json').read_text())['templates']:
    run(case,[sys.executable,NEXT/'replay.py','--case',case,'--build',build,'--output',out/case])
run('trace-core',[sys.executable,FOLLOW/'35-targeted-trace/run.py','--source',build,'--output',out/'trace-core'])
run('capture-compaction',[sys.executable,FOLLOW/'36-trace-footprint/run.py','--source',build,'--output',out/'capture-compaction'])
python=ROOT/'tools/rea-analysis/venv/bin/python'
run('packet-reset',[python,FOLLOW/'37-packet-initializer/run.py','--source',build,'--output',out/'packet-reset'])
run('compiled-writer',[python,ROOT/'scripts/test-startup-flash-arm.py','--version','3.7.0','--build',build,'--output',out/'compiled-writer.json'])
run('decoder-v3',[sys.executable,NEXT/'test_decoder.py','--fixture',out/'trace-core/synthetic.bin','--output',out/'decoder-v3'])
run('decoder-adversarial',[sys.executable,FOLLOW/'39-decoder-host-review/test_adversarial.py','--fixture',out/'trace-core/synthetic.bin','--output',out/'decoder-adversarial.json'])
run('decoder-registry',[sys.executable,FOLLOW/'39-decoder-host-review/test_registry.py','--output',out/'decoder-registry.json'])
run('decoder-legacy',[sys.executable,ROOT/'firmware/upstream-hardening/next36/test_decoder.py','--output',out/'decoder-legacy'])

# Rebind only path-dependent ELF/map containers after identical image, raw,
# manifest and normalized instructions/symbols/program headers are established.
# Reviewed callback, library, vector, source/compiled ordering and caveats stay.
stack=FOLLOW/'38-exact37-review'
policy=json.loads((stack/'policy.json').read_text())
reference=json.loads((NEXT/'stack-reproduction.json').read_text())
assert reference['reviewedPolicySHA256']==sha(stack/'policy.json')
tool=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-objdump'
assert sha(tool)==reference['objdumpSHA256']
for name in ('contax-zeiss-50-f1-4.bin','manifest.json','raw.bin'):
    assert sha(build/name)==policy['pins'][name],name
for mode,digest in reference['normalizedOutputSHA256'].items():
    text=subprocess.check_output([tool,mode,build/'hardened.elf'],text=True)
    header=str(build/'hardened.elf')+':     file format elf32-littlearm'
    assert text.count(header)==1
    assert hashlib.sha256(text.replace(header,'<ELF>:     file format elf32-littlearm').encode()).hexdigest()==digest,mode
rebound={}
for name in ('hardened.elf','hardened.map'):
    actual=sha(build/name)
    if actual!=policy['pins'][name]:
        rebound[name]={'reviewed':policy['pins'][name],'reproduced':actual};policy['pins'][name]=actual
policy_path=out/'stack-policy.json';policy_path.write_text(json.dumps(policy,indent=2)+'\n')
run('compiled-composition',[sys.executable,stack/'run.py','--build',build,'--policy',policy_path,'--output',out/'stack.json','--guards-output',out/'stack-guards.json'])
stack_result=json.loads((out/'stack.json').read_text())
assert stack_result['maximumAllVectorPriorityBytes']==1516 and not stack_result['recursiveComponents']
for n,h in m['sources'].items():assert sha(build/n)==h,n
report={'status':'passed-exact-37-offline-tracing','imageSHA256':m['imageSHA256'],
    'manifestSHA256':sha(build/'manifest.json'),'sourceFilesVerified':len(m['sources']),
    'checks':rows,'stackContainerPinsRebound':rebound,'hardwareReportsSent':0,
    'cameraQualified':False,'shutterFreezeFixEstablished':False,
    'limits':'Finite supplied inputs, instruction execution and software contracts do not establish physical timing, encoder polarity, optical AF, capture/shutdown reliability or factory parity.'}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2))
