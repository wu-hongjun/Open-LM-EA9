#!/usr/bin/env python3
"""Measure future source overlays in private scratch; never produce an image."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();w=a.output.resolve();assert w.is_relative_to(ROOT/'artifacts/private');w.mkdir(exist_ok=False)
m=json.loads((ROOT/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
shutil.copytree(BASE/'src',w/'src')
runpy.run_path(str(HERE/'apply_coordinate.py'))['apply'](w)
runpy.run_path(str(HERE.parent/'followup/12-query/apply.py'))['apply'](w)
runpy.run_path(str(HERE.parent/'followup/16-query-flow/apply.py'))['apply'](w)
deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
objects=[]
for unit in m['units']:
 obj=w/(unit+'.o');objects.append(str(obj))
 subprocess.run([arm+'gcc',*m['flags'],*m['unitFlags'].get(unit,[]),'-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/'+unit+'.c','-o',str(obj)],cwd=w,check=True)
cmd=[arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(w/'analysis-only.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(w/'analysis-only.elf')]
r=subprocess.run(cmd,cwd=w,text=True,capture_output=True);(w/'link.log').write_text(r.stdout+r.stderr)
result={'status':'coordinate-domain-and-query-size-not-candidate','baseImageSHA256':m['imageSHA256'],'linkExitCode':r.returncode,'binaryGenerated':False,'hardwareReportsSent':0,'cameraQualified':False,'sources':{p.name:sha(p) for p in (w/'src').glob('*.[ch]')}}
if r.returncode==0:
 symbols={}
 for line in subprocess.check_output([arm+'nm',str(w/'analysis-only.elf')],text=True).splitlines():
  v=line.split()
  if len(v)==3:symbols[v[2]]=int(v[0],16)
 end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
 result.update(codeAndDataEnd=end,marginBeforeDiagnostics=0x9c00-end,meets256ByteMargin=0x9c00-end>=256,staticRAMBytes=symbols['_ezero']-0x20000000)
(w/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
