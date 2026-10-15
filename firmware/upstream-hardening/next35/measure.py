#!/usr/bin/env python3
"""Measure staged post-3.4 proposals offline; no binary image or publication."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=ROOT/'artifacts/private/bounded34b'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--predictor',action='store_true');p.add_argument('--release-counter',action='store_true');a=p.parse_args();w=a.output.resolve();assert w.is_relative_to(ROOT/'artifacts/private');w.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((BASE/'manifest.json').read_text());assert sha(BASE/'manifest.json')=='8e358720a959a79a4636e1a9310fc23c08af9fa50539396d6946be6194c25a9a'
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
shutil.copytree(BASE/'src',w/'src')
runpy.run_path(str(HERE.parent/'followup/19-absolute-target/apply.py'))['apply'](w/'src')
time=runpy.run_path(str(HERE.parent/'followup/20-time-contract/apply.py'));time['home'](w)
if a.predictor:time['predictor'](w)
if a.release_counter:runpy.run_path(str(HERE/'apply_counter.py'))['apply'](w)
deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-');objects=[]
for unit in m['units']:
 obj=w/(unit+'.o');objects.append(str(obj));subprocess.run([arm+'gcc',*m['flags'],*m['unitFlags'].get(unit,[]),'-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/'+unit+'.c','-o',str(obj)],cwd=w,check=True)
r=subprocess.run([arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(w/'analysis-only.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(w/'analysis-only.elf')],cwd=w,text=True,capture_output=True);(w/'link.log').write_text(r.stdout+r.stderr)
result={'status':'post34-size-measurement-not-candidate','baseImageSHA256':m['imageSHA256'],'predictorProposalIncluded':a.predictor,'releaseCounterOmitted':a.release_counter,'linkExitCode':r.returncode,'binaryGenerated':False,'hardwareReportsSent':0,'cameraQualified':False,'sources':{p.name:sha(p) for p in (w/'src').glob('*.[ch]')}}
if r.returncode==0:
 symbols={}
 for line in subprocess.check_output([arm+'nm',str(w/'analysis-only.elf')],text=True).splitlines():
  fields=line.split()
  if len(fields)==3:symbols[fields[2]]=int(fields[0],16)
 end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate'];result.update(codeAndDataEnd=end,marginBeforeDiagnostics=0x9c00-end,meets256ByteMargin=0x9c00-end>=256,staticRAMBytes=symbols['_ezero']-0x20000000)
(w/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
