#!/usr/bin/env python3
"""Reproduce corrected-gate sensitivity; source mutants are not firmware images."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if not __debug__:
        raise SystemExit('optimized Python forbidden')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,default=ROOT/'artifacts/private/crash41-final')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--receipt',type=Path,help='Optional sanitized receipt path')
    a=p.parse_args();candidate=a.candidate.resolve();out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private')
    out.mkdir(parents=True,exist_ok=False)
    expected_manifest='557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b'
    assert sha(candidate/'manifest.json')==expected_manifest
    manifest=json.loads((candidate/'manifest.json').read_text())
    for n,h in manifest['sources'].items():assert sha(candidate/n)==h,n
    assert sha(candidate/'contax-zeiss-50-f1-4.bin')==manifest['imageSHA256']
    results={}
    def replay(label,src):
        r=subprocess.run([sys.executable,str(HERE/'run.py'),'--candidate',str(src),'--output',str(out/('astra50-'+label))],capture_output=True,text=True,timeout=180)
        (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
        results[label]={'exitCode':r.returncode}
        return r
    baseline=replay('baseline',candidate)
    assert baseline.returncode==0,(baseline.stdout,baseline.stderr)
    mutant=out/'source-mutant'
    shutil.copytree(candidate/'src',mutant/'src');shutil.copytree(candidate/'tools',mutant/'tools')
    shutil.copy2(candidate/'contax-zeiss-50-f1-4.bin',mutant/'contax-zeiss-50-f1-4.bin')
    source=(mutant/'src/main.c').read_text();old='#define HOME_GATE_OPEN()    1'
    assert source.count(old)==1
    (mutant/'src/main.c').write_text(source.replace(old,'#define HOME_GATE_OPEN()    0'))
    # Local source-manifest plumbing for the existing lane. This surrogate's
    # binary is deliberately NOT rebuilt; it cannot pass the frozen master.
    changed=json.loads(json.dumps(manifest));changed['sources']['src/main.c']=sha(mutant/'src/main.c')
    (mutant/'manifest.json').write_text(json.dumps(changed,indent=2)+'\n')
    # Reproduce the false green as well as rejection by the corrected replay.
    # The exact historical source is run with its original gate substitution.
    config=runpy.run_path(str(HERE/'run.py'))
    for path,pin in config['PINS'].items():assert sha(path)==pin,path
    historical=out/'historical-replay.py'
    historical.write_text(
        'import runpy,sys\n'
        + 'sys.path.insert(0,'+repr(str(config['NEXT']))+')\n'
        + 'from compiler_compat import install\n'
        + 'install('+repr(str(config['NEXT']/'trace_compat.c'))+','+repr(str(mutant/'src'))+')\n'
        + 'sys.argv='+repr([str(config['RUNNER']),'--candidate',str(mutant),'--output',str(out/'astra50-historical-closed-gate')])+'\n'
        + 'runpy.run_path(sys.argv[0],run_name="__main__")\n')
    original_run=subprocess.run([sys.executable,str(historical)],capture_output=True,text=True,timeout=180)
    (out/'historical-closed-gate.stdout').write_text(original_run.stdout)
    (out/'historical-closed-gate.stderr').write_text(original_run.stderr)
    assert original_run.returncode==0,(original_run.stdout,original_run.stderr)
    results['historical-closed-gate']={'exitCode':0,'unexpectedPass':'historical fixture overrides the closed production gate'}
    rejected=replay('closed-gate',mutant)
    assert rejected.returncode!=0 and 'g_homed&&g_home_state==HOME_READY&&!inhibited' in rejected.stderr,rejected.stderr
    results['closed-gate']['expectedFailure']='production readiness assertion at test_composed.c:113'
    extract=runpy.run_path(str(HERE/'run.py'))['gate_constants']
    original=(candidate/'src/main.c').read_text()
    for delay in (0,25):
        s,n=re.subn(r'^#define HOME_DELAY_MS[^\n]+$',f'#define HOME_DELAY_MS {delay}',original,flags=re.M)
        assert n==1
        code='#include <assert.h>\n#include <stdint.h>\nstatic uint32_t now,em_t_handshake;\n#define millis() now\n'+extract(s)+'\nint main(void){em_t_handshake=100;now=100;assert(HOME_GATE_OPEN()=='+str(int(delay==0))+');now=124;assert(HOME_GATE_OPEN()=='+str(int(delay==0))+');now=125;assert(HOME_GATE_OPEN());em_t_handshake=UINT32_MAX-10;now=13;assert(HOME_GATE_OPEN()=='+str(int(delay==0))+');now=14;assert(HOME_GATE_OPEN());return 0;}\n'
        c=out/f'delay-{delay}.c';c.write_text(code);exe=out/f'delay-{delay}'
        r=subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],capture_output=True,text=True)
        assert r.returncode==0,r.stderr
        r=subprocess.run([str(exe)],capture_output=True,text=True);assert r.returncode==0,r.stderr
        pp=subprocess.run(['clang','-E','-dM',str(c)],capture_output=True,text=True,check=True)
        (out/f'delay-{delay}.macros').write_text(pp.stdout)
        macro=next(x for x in pp.stdout.splitlines() if x.startswith('#define HOME_GATE_OPEN()'))
        assert (macro.endswith(' 1'))==(delay==0),macro
        results[f'delay-{delay}']={'exitCode':r.returncode,'productionMacro':macro,'thresholdAndWraparoundChecked':True}
    for n,h in manifest['sources'].items():assert sha(candidate/n)==h,n
    assert sha(candidate/'manifest.json')==expected_manifest
    for path,pin in config['PINS'].items():assert sha(path)==pin,path
    receipt={'status':'passed-prospective-host-gate-regression','hardwareAccess':False,'frozenSourcesUnchanged':True,'candidateImageSHA256':manifest['imageSHA256'],'candidateManifestSHA256':expected_manifest,'scope':'host source replay only; no rebuilt mutant, master bypass, camera or timing qualification','results':results,'scripts':{str(f.relative_to(ROOT)):sha(f) for f in (HERE/'run.py',HERE/'test.py')},'historicalInputs':{str(f.relative_to(ROOT)):pin for f,pin in runpy.run_path(str(HERE/'run.py'))['PINS'].items()},'sourcePins':manifest['sources']}
    (out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if a.receipt:a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'results':results},indent=2))

if __name__=='__main__':main()
