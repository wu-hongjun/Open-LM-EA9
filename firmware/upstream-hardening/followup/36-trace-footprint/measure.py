#!/usr/bin/env python3
"""Measure before/after loaded ARM extent with unchanged candidate compiler flags."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
from apply import apply,BASE_SHA
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.output.resolve();assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
m=json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text())
deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
reference=out/'reference';shutil.copytree(source/'src',reference/'src')
source_is_compact=sha(source/'src/emount.c')!=BASE_SHA
if source_is_compact:
 (reference/'src/emount.c').write_bytes((ROOT/'artifacts/private/handoff36-repeat/src/emount.c').read_bytes())
 runpy.run_path(str(HERE.parent/'34-capture-tracing/apply.py'))['apply'](reference/'src')
assert sha(reference/'src/emount.c')==BASE_SHA
rows={}
for variant in ['before','compact']:
 w=out/variant;shutil.copytree(reference/'src',w/'src')
 if variant=='compact':
  apply(w/'src')
  if source_is_compact:assert sha(w/'src/emount.c')==sha(source/'src/emount.c')
 objects=[];sizes={}
 for unit in m['units']+['motion_trace']:
  cmd=[arm+'gcc',*m['flags'],*m['unitFlags'].get(unit,[]),*(['-Os'] if unit=='motion_trace' else []),'-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/'+unit+'.c','-o',unit+'.o']
  subprocess.run(cmd,cwd=w,check=True,capture_output=True);objects.append(unit+'.o')
  fields=subprocess.check_output([arm+'size',unit+'.o'],cwd=w,text=True).splitlines()[1].split()
  sizes[unit]={'text':int(fields[0]),'data':int(fields[1]),'bss':int(fields[2])}
 subprocess.run([arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map=hardened.map','--specs=nano.specs','--specs=nosys.specs','-o','hardened.elf'],cwd=w,check=True,capture_output=True)
 symbols={}
 for line in subprocess.check_output([arm+'nm','hardened.elf'],cwd=w,text=True).splitlines():
  fields=line.split()
  if len(fields)==3:symbols[fields[2]]=int(fields[0],16)
 end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
 rows[variant]={'loadedEnd':end,'margin':0x9c00-end,'marginAtLeast256':0x9c00-end>=256,'sizes':sizes,'sourceSHA256':sha(w/'src/emount.c'),'stackUsage':(w/'emount.su').read_text().splitlines(),'st_noteBridgePresent':'st_note' in symbols}
 print(variant,end,0x9c00-end,flush=True)
report={'sourceHashes':{str(p.relative_to(source)):sha(p) for p in sorted((source/'src').iterdir()) if p.suffix in ('.c','.h','.ld')},'compiler':subprocess.check_output([arm+'gcc','--version'],text=True).splitlines()[0],'baseFlags':m['flags'],'baseUnitFlags':m['unitFlags'],'addedUnitFlags':{'motion_trace':['-Os']},'variants':rows,'loadedBytesSaved':rows['before']['loadedEnd']-rows['compact']['loadedEnd'],'hardwareAccess':False,'stackHighWaterMeasured':False}
(out/'measurement.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'measurement.json').write_text(json.dumps(report,indent=2)+'\n')
