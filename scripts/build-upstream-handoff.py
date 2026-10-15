#!/usr/bin/env python3
"""Build the reviewed next-version C composition offline; never publish or flash.

Use a new output directory under an existing parent. Published 3.5 sources and
images are immutable. A published 3.6 image, when present, must reproduce exactly.
Root freezes the accepted lane hashes only after review; a partial composition
is a workbench build, not release evidence.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'firmware/upstream-hardening'
BASE=ROOT/'artifacts/private/absolute35a'
DEPS=ROOT/'tools/firmware-deps'
ARM=str(DEPS/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args(); work=args.output.resolve()
plan_path=LANE/'next36/accepted-lanes.json'; plan=json.loads(plan_path.read_text())
frozen_path=ROOT/'firmware/candidates/3.5.0/contax-zeiss-50-f1-4.manifest.json'
frozen=json.loads(frozen_path.read_text())
assert plan['baseVersion']=='3.5.0' and plan['nextVersion']=='3.6.0'
assert plan['baseImageSHA256']==frozen['imageSHA256']=='04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632'
assert sha(frozen_path)=='a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de'
assert frozen==json.loads((BASE/'manifest.json').read_text()), 'Reproduce frozen 3.5 build inputs first'
for name,digest in frozen['sources'].items(): assert sha(BASE/name)==digest,name
assert sha(ROOT/'firmware/candidates/3.5.0/contax-zeiss-50-f1-4.bin')==frozen['imageSHA256']
assert sha(BASE/'from-34.patch')==frozen['from34PatchSHA256']
assert work.is_relative_to(ROOT/'artifacts/private'), 'Private build scratch required'
work.mkdir(parents=False,exist_ok=False)
shutil.copytree(BASE/'src',work/'src')
shutil.copytree(BASE/'tools/hosttest',work/'tools/hosttest')
lane_inputs={}
for name,digest in plan['inputs'].items():
    path=(ROOT/name).resolve()
    assert path.is_relative_to(LANE) and sha(path)==digest,name
    lane_inputs[name]=digest
assert plan['applicators']==[{'path': 'firmware/upstream-hardening/followup/26-compiled-irq/apply.py', 'entry': 'scoped', 'argument': 'work'}, {'path': 'firmware/upstream-hardening/followup/26-compiled-irq/apply.py', 'entry': 'omit_legacy_snapshot', 'argument': 'work'}, {'path': 'firmware/upstream-hardening/followup/26-compiled-irq/apply.py', 'entry': 'omit_legacy_close_snapshot', 'argument': 'work'}, {'path': 'firmware/upstream-hardening/followup/26-compiled-irq/apply.py', 'entry': 'host_api', 'argument': 'work'}]
for entry in plan['applicators']:
    assert entry['path'] in lane_inputs
    runpy.run_path(str(ROOT/entry['path']))[entry['entry']](work/'src' if entry['argument']=='src' else work)
path=work/'src/emount.h'; text=path.read_text()
assert text.count('#define EM_FW_VERSION_BCD   0x35u')==1
path.write_text(text.replace('#define EM_FW_VERSION_BCD   0x35u','#define EM_FW_VERSION_BCD   0x36u'))

units=frozen['units']
assert len(units)==len(set(units))
flags=frozen['flags']; unit_flags=frozen['unitFlags']
assert '-fstack-usage' in flags and all(value==['-Os'] for value in unit_flags.values())
includes=['-Isrc','-I'+str(DEPS/'samd21-dfp-2/samd21a/include'),
          '-I'+str(DEPS/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
objects=[]
for name in units:
    obj=work/(name+'.o'); objects.append(str(obj))
    subprocess.run([ARM+'gcc',*flags,*unit_flags.get(name,[]),*includes,'-c','src/'+name+'.c','-o',str(obj)],cwd=work,check=True)
elf=work/'hardened.elf'
subprocess.run([ARM+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld',
               '-Wl,--gc-sections,-Map='+str(work/'hardened.map'),
               '--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],cwd=work,check=True)
symbols={}
for line in subprocess.check_output([ARM+'nm',str(elf)],text=True).splitlines():
    fields=line.split()
    if len(fields)==3: symbols[fields[2]]=int(fields[0],16)
end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
assert end<=0x9c00 and symbols['_estack']<=0x20004000
assert 0x9c00-end>=256, 'Require at least 256 bytes of code/data margin before diagnostics'
subprocess.run([ARM+'objcopy','-O','binary','--gap-fill=0xff',str(elf),str(work/'raw.bin')],check=True)
raw=(work/'raw.bin').read_bytes(); assert len(raw)<=0x4c00
data=raw+b'\xff'*(0x5000-len(raw)); image=work/'contax-zeiss-50-f1-4.bin'; image.write_bytes(data)
assert data[0x4c00:]==b'\xff'*1024
assert int.from_bytes(data[:4],'little')==symbols['_estack']
assert int.from_bytes(data[4:8],'little')==symbols['Reset_Handler']|1
published=ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.bin'
if published.exists() and published.read_bytes()!=data:
    raise SystemExit('Build differs from frozen 3.6.0; prepare a separately versioned candidate.')
patch=[]
for path in sorted((work/'src').glob('*')):
    before=BASE/'src'/path.name
    if path.suffix not in ('.c','.h','.ld'): continue
    old=before.read_text() if before.is_file() else ''
    if old!=path.read_text():
        patch.extend(difflib.unified_diff(old.splitlines(True),path.read_text().splitlines(True),
                     fromfile='frozen35/src/'+path.name if before.is_file() else '/dev/null',
                     tofile='handoff36/src/'+path.name,n=0))
(work/'from-35.patch').write_text(''.join(patch))
result={
    'status':plan['status'],'baseImageSHA256':frozen['imageSHA256'],
    'upstreamCommit':frozen['upstreamCommit'],'loaderVersion':[3,6,0],
    'imageSHA256':sha(image),'imageBytes':len(data),'rawBytes':len(raw),
    'codeAndDataEnd':end,'codeMarginBeforeDiagnostics':0x9c00-end,
    'staticRAMBytes':symbols['_ezero']-0x20000000,
    'reservedStackBytes':symbols['_estack']-symbols['_sstack'],
    'diagnosticRange':[0x9c00,0xa000],'diagnosticPageBytes':64,'diagnosticPages':16,
    'lensID':234,'nominalApertureAV':4352,'runtimeLensProfilesSupported':False,
    'cameraQualified':False,'hardwareReportsSent':0,'publishedFirmwareChanged':False,
    'acceptedPlanSHA256':sha(plan_path),'baseManifestSHA256':sha(frozen_path),
    'buildScriptSHA256':sha(Path(__file__).resolve()),
    'laneInputs':lane_inputs,'units':units,'flags':flags,'unitFlags':unit_flags,
    'sources':{str(p.relative_to(work)):sha(p) for p in sorted((work/'src').iterdir()) if p.suffix in ('.c','.h','.ld')},
    'from35PatchSHA256':sha(work/'from-35.patch'),
    'hostTestShimSHA256':sha(work/'tools/hosttest/shim.c'),
    'stackHighWaterMeasured':False,
}
stack=[]
for path in sorted(work.glob('*.su')):
    for line in path.read_text().splitlines():
        fields=line.split('\t')
        if len(fields)==3:
            stack.append({'function':fields[0].rsplit(':',1)[-1],
                          'bytes':int(fields[1]),'kind':fields[2]})
result['compilerStackUsage']=stack
(work/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in
                 ('sources','laneInputs','units','flags','compilerStackUsage')},indent=2))
