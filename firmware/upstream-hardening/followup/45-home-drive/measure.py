#!/usr/bin/env python3
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];base=ROOT/'artifacts/private/readiness38-repeat'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve()
assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra45-');out.mkdir(exist_ok=False)
m=json.loads((ROOT/'firmware/candidates/3.8.0/contax-zeiss-50-f1-4.manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in m['sources'].items():assert sha(base/n)==h,n
rows=[]
for variant in ['baseline','observation']:
 work=out/variant;shutil.copytree(base/'src',work/'src')
 if variant=='observation':runpy.run_path(str(HERE/'apply.py'))['apply'](work)
 deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
 inc=['-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')];objects=[]
 for n in m['units']:
  obj=work/(n+'.o');objects.append(str(obj));r=subprocess.run([arm+'gcc',*m['flags'],*m['unitFlags'].get(n,[]),*inc,'-c','src/'+n+'.c','-o',str(obj)],cwd=work,capture_output=True,text=True);assert r.returncode==0,r.stderr
 elf=work/'hardened.elf';r=subprocess.run([arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(work/'hardened.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],cwd=work,capture_output=True,text=True);assert r.returncode==0,r.stderr
 sym={}
 for l in subprocess.check_output([arm+'nm',str(elf)],text=True).splitlines():
  f=l.split()
  if len(f)==3:sym[f[2]]=int(f[0],16)
 end=sym['_etext']+sym['_erelocate']-sym['_srelocate'];ram=sym['_ezero']-0x20000000
 subprocess.run([arm+'objcopy','-O','binary','--gap-fill=0xff',str(elf),str(work/'raw.bin')],check=True)
 raw=(work/'raw.bin').read_bytes();image=raw+b'\xff'*(0x5000-len(raw));h=hashlib.sha256(image).hexdigest()
 if variant=='baseline':assert h==m['imageSHA256'] and end==m['codeAndDataEnd']
 rows.append(dict(variant=variant,end=end,margin=0x9c00-end,staticRAMBytes=ram,imageSHA256=h,mainSHA256=sha(work/'src/main.c')))
for n,h in m['sources'].items():assert sha(base/n)==h,n
r=dict(sourcePinsVerifiedBeforeAndAfter=49,measurement=rows,inputs={p.name:sha(p) for p in [HERE/'apply.py',HERE/'measure.py']});(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
