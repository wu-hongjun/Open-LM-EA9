#!/usr/bin/env python3
"""Recompile/relink all AF3.8 ARM units with only lane46, offline."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
base=ROOT/'artifacts/private/readiness38-repeat';m=json.loads((base/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'manifest.json')=='be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0'
for n,d in m['sources'].items():assert sha(base/n)==d,n
out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra46-');out.mkdir(exist_ok=False)
shutil.copytree(base/'src',out/'src');runpy.run_path(str(HERE/'apply.py'))['apply'](out)
deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
inc=['-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
objects=[]
for unit in m['units']:
 obj=out/(unit+'.o');objects.append(str(obj));subprocess.run([arm+'gcc',*m['flags'],*m['unitFlags'].get(unit,[]),*inc,'-c','src/'+unit+'.c','-o',str(obj)],cwd=out,check=True,capture_output=True)
subprocess.run([arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(out/'hardened.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(out/'hardened.elf')],cwd=out,check=True,capture_output=True)
def symbols(elf):
 d={}
 for line in subprocess.check_output([arm+'nm',str(elf)],text=True).splitlines():
  f=line.split()
  if len(f)==3:d[f[2]]=int(f[0],16)
 return d
s=symbols(out/'hardened.elf');b=symbols(base/'hardened.elf');end=lambda d:d['_etext']+d['_erelocate']-d['_srelocate']
r={'baseImageSHA256':m['imageSHA256'],'bytesAdded':end(s)-end(b),'marginBytes':0x9c00-end(s),'mainSHA256':sha(out/'src/main.c'),'elfSHA256':sha(out/'hardened.elf'),'scope':'lane46 only; source tail initialization is lane45'}
(out/'size.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
