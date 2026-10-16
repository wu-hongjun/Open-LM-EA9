#!/usr/bin/env python3
"""Reproduce ARM object size/stack and exact 0/1 trace-packing equivalence."""
import argparse, hashlib, itertools, json, re, shutil, subprocess
from pathlib import Path
from apply import apply
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.source.resolve();out=a.output.resolve()
    assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
    manifest=json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    for n,h in manifest['sources'].items():assert sha(source/n)==h,n
    # These are all assignments, including declarations. Their RHS is exactly0/1.
    servo=(source/'src/servo.c').read_text()
    writes=re.findall(r'\b(holding|rebase)\s*=\s*([^;]+);',servo)
    assert writes==[('holding','0'),('rebase','0'),('rebase','1'),('holding','1'),('holding','0'),('rebase','0')],writes
    comparisons=0
    for rebase,holding,sign,count in itertools.product((0,1),(0,1),(-1,1),range(256)):
        old=(count<<8)|(1 if rebase else 0)|(2 if holding else 0)|(4 if sign<0 else 0)
        new=(count<<8)|rebase|(holding<<1)|(int(sign<0)<<2)
        assert old==new;comparisons+=1
    deps=ROOT/'tools/firmware-deps';prefix=deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-'
    includes=['-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
    out.mkdir(exist_ok=False);rows={}
    for variant in ('frozen','ternary-observation','packed-observation'):
        w=out/variant;shutil.copytree(source/'src',w/'src')
        if variant!='frozen':apply(w/'src')
        if variant=='ternary-observation':
            p=w/'src/servo.c';s=p.read_text();old='(unsigned)rebase | ((unsigned)holding << 1)\n\t\t    | ((unsigned)(leg_sign < 0) << 2)';assert s.count(old)==1
            p.write_text(s.replace(old,'(rebase ? ST_MS_REBASE : 0) | (holding ? ST_MS_HOLDING : 0)\n\t\t    | (leg_sign < 0 ? ST_MS_NEGATIVE : 0)'))
        units=['servo','main']+(['motion_trace'] if variant!='frozen' else []);rows[variant]={}
        for unit in units:
            flags=manifest['flags']+manifest['unitFlags'].get(unit,[])+(['-Os'] if unit=='motion_trace' else [])
            cmd=[str(prefix)+'gcc',*flags,*includes,'-Isrc','-c','src/'+unit+'.c','-o',unit+'.o']
            subprocess.run(cmd,cwd=w,check=True,capture_output=True)
            size=subprocess.check_output([str(prefix)+'size',unit+'.o'],cwd=w,text=True).splitlines()[1].split()
            rows[variant][unit]=dict(textBytes=int(size[0]),dataBytes=int(size[1]),bssBytes=int(size[2]),stackUsage=(w/(unit+'.su')).read_text().splitlines(),objectSHA256=sha(w/(unit+'.o')),sourceSHA256=sha(w/'src'/(unit+'.c')))
        if variant!='frozen':
            undefined=subprocess.check_output([str(prefix)+'nm','-u','motion_trace.o'],cwd=w,text=True).split()
            assert undefined==['U','memset','U','millis'],undefined
            rows[variant]['motionUndefinedSymbols']=['memset','millis']
    result=dict(compiler=subprocess.check_output([str(prefix)+'gcc','--version'],text=True).splitlines()[0],baseManifestSHA256=sha(ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json'),booleanWriteInventory=writes,packingEquivalenceCases=comparisons,units=rows,wholeImageFit='Owned by lane35/root; these are relocatable object sizes, not a link-layout gate.',hardwareTimingMeasured=False)
    (out/'measurement.json').write_text(json.dumps(result,indent=2)+'\n');(HERE/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{u:r['textBytes'] for u,r in v.items() if isinstance(r,dict)} for k,v in rows.items()},indent=2))
if __name__=='__main__':main()
