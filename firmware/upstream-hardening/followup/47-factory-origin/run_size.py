#!/usr/bin/env python3
"""Pin AF3.8, compare extracted production arithmetic, measure exact ARM delta."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
if not __debug__:raise SystemExit('Assertions required')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=ROOT/'artifacts/private/readiness38-repeat'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def function(s,name):
 lo=s.index(name+'\n{');lo=s.rfind('\n',0,lo)+1;return s[lo:s.index('\n}',lo)+2]+'\n'
def run(cmd,expected=0):
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True,timeout=60)
 if expected==0:assert r.returncode==0,(cmd,r.stdout,r.stderr)
 else:assert r.returncode and 'Assertion failed' in r.stderr,(cmd,r.stdout,r.stderr)
 return dict(exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();assert out.parent==ROOT/'artifacts/private' and out.name.startswith('astra47-');out.mkdir(exist_ok=False)
mp=ROOT/'firmware/candidates/3.8.0/contax-zeiss-50-f1-4.manifest.json';assert sha(mp)=='be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0';m=json.loads(mp.read_text());assert m==json.loads((BASE/'manifest.json').read_text())
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
shutil.copytree(BASE/'src',out/'src');runpy.run_path(str(HERE/'apply_size.py'))['apply'](out)
s=(BASE/'src/main.c').read_text();helper=function(s,'static uint8_t home_still_for(struct home_still *st, uint32_t ms)');changed=function((out/'src/main.c').read_text(),'static uint8_t home_still_for(struct home_still *st, uint32_t ms)')
tracker=(BASE/'src/abs_encoder.c').read_text();track=''.join(function(tracker,n) for n in ['void abs_encoder_track_reset(void)','int32_t abs_encoder_track(void)'])
template=(HERE/'test_stillness.inc').read_text().replace('/* EXTRACTED_TRACKER */',track)
def test(candidate,label,expected=0):
 text=template.replace('/* EXTRACTED_HELPERS */',helper.replace('home_still_for','baseline')+candidate.replace('home_still_for','proposal'));path=out/(label+'.c');path.write_text(text)
 flags=['clang','-std=gnu99','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(out/'src')]
 run([*flags,path,'-o',out/label]);return run([out/label],expected)
checks=test(changed,'equivalence');controls=[]
for name,old,new in [('narrow16','uint32_t d = now >= st->at','uint16_t d = now >= st->at'),('threshold','d > HOME_STILL_COUNTS','d >= HOME_STILL_COUNTS')]:
 assert old in changed;controls.append(dict(name=name,**test(changed.replace(old,new),name,1)))
arm=ROOT/'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-';deps=ROOT/'tools/firmware-deps'
for n in m['units']:shutil.copyfile(BASE/(n+'.o'),out/(n+'.o'))
flags=m['flags']+m['unitFlags']['main']+['-I'+str(out/'src'),'-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
run([str(arm)+'gcc',*flags,'-c',out/'src/main.c','-o',out/'main.o'])
run([str(arm)+'gcc',*[out/(n+'.o') for n in m['units']],'-mthumb','-mcpu=cortex-m0plus','-T'+str(out/'src/ea9.ld'),'-Wl,--gc-sections,-Map='+str(out/'measured.map'),'--specs=nano.specs','--specs=nosys.specs','-o',out/'measured.elf'])
symbols={}
for row in subprocess.check_output([str(arm)+'nm',out/'measured.elf'],text=True).splitlines():
 f=row.split()
 if len(f)==3:symbols[f[2]]=int(f[0],16)
end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate'];delta=end-m['codeAndDataEnd']
result=dict(status='full-domain-arithmetic-equivalence-pass-not-homing-remedy',baseManifestSHA256=sha(mp),sourcePins=m['sources'],checks=checks,negativeControls=controls,codeAndDataEndBefore=m['codeAndDataEnd'],codeAndDataEndAfter=end,deltaBytes=delta,marginAfter=0x9c00-end,staticRAMBytes=symbols['_ezero']-0x20000000,mainAfterSHA256=sha(out/'src/main.c'),applicatorSHA256=sha(HERE/'apply_size.py'),testSHA256=sha(HERE/'test_stillness.inc'),runnerSHA256=sha(Path(__file__)),hardwareOperations=0,limits='Unsigned magnitude preserves int64 threshold comparison for every int32 pair, including retained corrupted coordinates; exhaustive bounded anchors and deterministic full-domain samples test the algebra. No physical timing/acceptance claim.')
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['deltaBytes','marginAfter','staticRAMBytes','checks']}))
