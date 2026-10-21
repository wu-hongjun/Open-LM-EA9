#!/usr/bin/env python3
"""Independent synthetic power-loss schedules against actual trace C."""
import argparse, hashlib, json, runpy, shutil, subprocess, zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(p):
    m=json.loads((p/'manifest.json').read_text())
    assert sha(p/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
    for name,digest in m['sources'].items(): assert sha(p/name)==digest,name
    return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--candidate',type=Path);a=ap.parse_args()
    assert __debug__, 'optimized Python forbidden'
    base=ROOT/'artifacts/private/reference40-repeat';bm=verify(base)
    assert sha(base/'manifest.json')=='8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc'
    assert bm['imageSHA256']=='06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae'
    source=a.candidate.resolve() if a.candidate else base; m=verify(source);pin=sha(source/'manifest.json')
    out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra54-');out.mkdir(exist_ok=False)
    shutil.copytree(source/'src',out/'src')
    if not a.candidate:runpy.run_path(str(HERE.parent/'52-durable-crash/apply.py'))['apply'](out/'src')
    trace=out/'src/startup_trace.c';text=trace.read_text()
    # Only the retained checkpoint mutation boundaries are instrumented.
    begin=text.index('void st_checkpoint(');end=text.index('int st_boot_record(',begin)
    prefix,body,suffix=text[:begin],text[begin:end],text[end:]
    for line in ['retained.magic=0;', 'retained.summary=s;', 'retained.summary.ms=ms;', 'retained.crc=st_crc32((const uint8_t *)&retained.summary,48);', 'retained.magic=ST_RETAINED_MAGIC;']:
        assert body.count(line)==1,line
        body=body.replace(line,line+' checkpoint_step();')
    text=prefix+body+suffix
    controls={
        'proposal':None,
        'mutant-checksum':('&& retained.crc==st_crc32((const uint8_t *)&retained.summary,48)','&& 1'),
        'mutant-reset-mask':('(reset_cause==32 || reset_cause==64)','(reset_cause & 96)'),
        'mutant-consume':('retained.magic=0;\n    __asm__ volatile ("" ::: "memory");','/* omit consume */'),
        'mutant-latch':('if (crash_latched) {','if (0) {'),
        'mutant-invalidate':('retained.magic=0; checkpoint_step();','/* omit invalidate */ checkpoint_step();'),
        'mutant-retry':('if (r_failed || r_next_page>=16) return 0;','if (r_next_page>=16) return 0;'),
    }
    executions={}
    for name,change in controls.items():
        modified=text
        if change:
            old,new=change;assert modified.count(old)==1,(name,modified.count(old));modified=modified.replace(old,new)
        trace.write_text(modified);dest=out/name;dest.mkdir()
        command=['clang','-DST_HOST','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(out/'src'),str(HERE/'test_powerloss.c'),'-o',str(dest/'test')]
        build=subprocess.run(command,capture_output=True,text=True,timeout=40);assert build.returncode==0,build.stderr
        r=subprocess.run([str(dest/'test'),str(dest)],capture_output=True,text=True,timeout=20)
        assert (r.returncode==0)==(name=='proposal'),(name,r.stdout,r.stderr)
        expected={'mutant-checksum':'flash[10]==0','mutant-reset-mask':'flash[10]==(cause==32 || cause==64)','mutant-consume':'retained.magic==0','mutant-latch':'halt==(n!=0)','mutant-invalidate':'flash[10]==(step==5)','mutant-retry':'writes==(n==64?2:1)'}
        if change:assert 'Assertion failed' in r.stderr and expected[name] in r.stderr,(name,r.stderr)
        executions[name]={'exitCode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()}
    trace.write_text(text)
    fixture=out/'proposal'
    full=(fixture/'tail-999.bin').read_bytes()[:64]
    assert zlib.crc32(full[:60])==int.from_bytes(full[60:],'little')
    old=runpy.run_path(str(ROOT/'scripts/startup_diagnostic_v3.py'))['decode_pages']
    old_result=old(full+b'\xff'*960,version='4.0.0')
    assert old_result['validPages']==0 and old_result['invalidPages']==1
    checks=0
    for n in range(65):
        page=(fixture/f'tail-{n:03}.bin').read_bytes()[:64]
        assert page==full[:n]+b'\xff'*(64-n)
        valid=page[:4]==b'E9S3' and zlib.crc32(page[:60])==int.from_bytes(page[60:],'little')
        assert valid==(page==full),(n,page.hex());checks+=1
    for bit in range(512):
        page=bytearray(full);page[bit//8]^=1<<(bit%8)
        assert zlib.crc32(page[:60])!=int.from_bytes(page[60:],'little');checks+=1
    verify(base);verify(source);assert sha(source/'manifest.json')==pin
    result={'status':'PASS','hardwareAccess':False,'candidateManifestSHA256':pin,'overlay52':not bool(a.candidate),'host':executions['proposal']['stdout'],'executions':executions,'independentCRCChecks':checks,'sourcePins':{p.name:sha(p) for p in (out/'src').iterdir() if p.is_file()},'testPins':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.c','.py')}}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':str(out),'host':result['host'],'independentCRCChecks':checks}))
if __name__=='__main__':main()
