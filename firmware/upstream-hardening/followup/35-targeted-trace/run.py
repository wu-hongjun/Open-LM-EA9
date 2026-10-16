#!/usr/bin/env python3
"""Offline compiled production writer and extracted shutdown-tail tests."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'artifacts/private/handoff36-repeat'
def run(cmd,**kw):return subprocess.run(cmd,text=True,capture_output=True,**kw)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--source',type=Path);a=parser.parse_args();w=a.output.resolve()
    assert w.is_relative_to(ROOT/'artifacts/private');w.mkdir(exist_ok=False)
    pins=json.loads((BASE/'manifest.json').read_text());frozen=json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text());assert pins==frozen
    for n,h in pins['sources'].items():assert hashlib.sha256((BASE/n).read_bytes()).hexdigest()==h,n
    exact_manifest=None
    if a.source:
        source=a.source.resolve();assert source.is_relative_to(ROOT/'artifacts/private')
        exact_manifest=json.loads((source/'manifest.json').read_text())
        for n,h in exact_manifest['sources'].items():assert hashlib.sha256((source/n).read_bytes()).hexdigest()==h,n
        shutil.copytree(source/'src',w/'src')
    else:
        shutil.copytree(BASE/'src',w/'src');runpy.run_path(str(HERE/'apply.py'))['apply'](w)
        shutil.copyfile(HERE.parent/'33-motion-tracing/motion_trace.h',w/'src/motion_trace.h')
    core=w/'src/startup_trace.c';test=w/'test_core.c';shutil.copyfile(HERE/'test_core.c',test)

    cflags=['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-g','-I'+str(w/'src')]
    r=run([*cflags,str(core),str(test),'-o',str(w/'core')]);assert r.returncode==0,r.stderr
    r=run([str(w/'core'),str(w/'synthetic.bin')]);assert r.returncode==0,r.stderr;print(r.stdout.strip())
    source=(w/'src/main.c').read_text();lo=source.index('static void powerdown_signal(void)');hi=source.index('\n}\n',lo)+3
    tail=(HERE/'test_tail.inc').read_text().replace('/* EXTRACTED_PRODUCTION_FUNCTION */',source[lo:hi]);(w/'tail.c').write_text(tail)
    r=run([*cflags,str(w/'tail.c'),'-o',str(w/'tail')]);assert r.returncode==0,r.stderr
    r=run([str(w/'tail')]);assert r.returncode==0,r.stderr;print(r.stdout.strip())
    # Frozen behavior helper byte-exact, hardware writer altered only at fail-stop tail.
    helper=(BASE/'src/startup_trace.c').read_text();helper=helper[helper.index('int st_preserve_first_window'):helper.index('/* First nonterminal')]
    assert helper in core.read_text()
    flash=(w/'src/startup_trace_flash.c').read_text().replace('    st_terminal(ST_TERMINAL_FAULT,fault,millis());\n','')
    assert flash==(BASE/'src/startup_trace_flash.c').read_text()
    controls={
      'sealed-footer-regression':('if (!r_sealed) return;','if (r_sealed) return;'),
      'wrong-retained-order':('(r_tail+32-s.planned+i++)&31u','(r_tail+32-s.planned+--i)&31u'),
      'retry-after-write-failure':('if (!st_write_page(address,(const uint8_t *)p)) { r_failed=1; return 0; }','if (!st_write_page(address,(const uint8_t *)p)) { return 0; }'),
      'crc-corruption':('p->crc=st_crc32((const uint8_t *)p,60);','p->crc=st_crc32((const uint8_t *)p,60)^1;'),
    }
    results={}
    for name,(old,new) in controls.items():
        text=core.read_text();assert text.count(old)==1,name
        mutant=w/(name+'.c');mutant.write_text(text.replace(old,new))
        r=run([*cflags,str(mutant),str(test),'-o',str(w/name)]);assert r.returncode==0,r.stderr
        r=run([str(w/name)]);assert r.returncode!=0,name;results[name]='failed-as-required'
    print('Four failing controls rejected')
    result={'status':'offline-trace-v3-core-tests-pass','baseImageSHA256':pins['imageSHA256'],'testedImageSHA256':exact_manifest.get('imageSHA256') if exact_manifest else None,'exactSourceManifestSHA256':hashlib.sha256((a.source/'manifest.json').read_bytes()).hexdigest() if a.source else None,'testedSources':{str(p.relative_to(w)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (w/'src').iterdir() if p.suffix in ('.c','.h','.ld')},'pageCutCases':1040,'occupancyCases':17,'tailCases':6,'controls':results,'hardwareOperations':0,'cameraQualified':False,'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.suffix in ('.c','.h','.py','.inc','.json') and p.name not in ('result.json','results.json','measurement.json')}}
    (w/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
