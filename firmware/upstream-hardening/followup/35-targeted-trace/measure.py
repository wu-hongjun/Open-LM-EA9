#!/usr/bin/env python3
"""Measure the three tracing lanes on exact3.6; emit ELF/map only, never an image."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'artifacts/private/handoff36-repeat'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);a=parser.parse_args();w=a.output.resolve()
    assert w.is_relative_to(ROOT/'artifacts/private');w.mkdir(exist_ok=False)
    m=json.loads((BASE/'manifest.json').read_text());assert m==json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    for name,digest in m['sources'].items():assert sha(BASE/name)==digest,name
    shutil.copytree(BASE/'src',w/'src')
    for lane in ('33-motion-tracing','34-capture-tracing'):runpy.run_path(str(HERE.parent/lane/'apply.py'))['apply'](w/'src')
    runpy.run_path(str(HERE/'apply.py'))['apply'](w)
    deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-');objects=[]
    flags=m['unitFlags'].copy();flags['motion_trace']=['-Os']
    for name in m['units']+['motion_trace']:
        obj=w/(name+'.o');objects.append(str(obj))
        subprocess.run([arm+'gcc',*m['flags'],*flags.get(name,[]),'-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/'+name+'.c','-o',str(obj)],cwd=w,check=True)
    elf=w/'measurement.elf'
    link=subprocess.run([arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(w/'measurement.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],cwd=w,text=True,capture_output=True)
    (w/'link.log').write_text(link.stdout+link.stderr)
    result={'status':'offline-composed-tracing-size-measurement','baseImageSHA256':m['imageSHA256'],'baseManifestSHA256':sha(BASE/'manifest.json'),'linkExitCode':link.returncode,'binaryGenerated':False,'cameraQualified':False,'hardwareOperations':0,'unitFlags':flags,'sources':{str(p.relative_to(w)):sha(p) for p in (w/'src').iterdir() if p.suffix in ('.c','.h','.ld')}}
    if link.returncode==0:
        symbols={}
        for line in subprocess.check_output([arm+'nm',str(elf)],text=True).splitlines():
            fields=line.split()
            if len(fields)==3:symbols[fields[2]]=int(fields[0],16)
        end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
        result.update(codeAndDataEnd=end,marginBeforeDiagnostics=0x9c00-end,meets256ByteMargin=0x9c00-end>=256,staticRAMBytes=symbols['_ezero']-0x20000000,reservedStackBytes=symbols['_estack']-symbols['_sstack'])
    (w/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('sources','unitFlags')},indent=2))
    assert link.returncode==0 and result['meets256ByteMargin'],'fixed layout/margin gate failed; see private link.log'
if __name__=='__main__':main()
