#!/usr/bin/env python3
"""Run final-source storage tests and verify terminal-only flush source gates."""
import argparse,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];EIGHT=HERE.parent/'08-diagnostics'
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(exist_ok=False);src=a.source.resolve()/'src'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((a.source/'manifest.json').read_text())
for name,digest in manifest['sources'].items():assert sha(a.source/name)==digest,name
main=(src/'main.c').read_text();em=(src/'emount.c').read_text();trace=(src/'startup_trace.c').read_text();flash=(src/'startup_trace_flash.c').read_text()
assert 'st_flush(' not in em
assert main.count('st_flush(')==1
powerdown=main[main.index('static void powerdown_signal(void)\n{'):main.index('static void park_to_infinity(void)\n{')]
assert powerdown.index('em_uart_disable();')<powerdown.index('st_flush(')
assert flash.count('st_flush(')==1
failure=flash[flash.index('void st_fail('):]
assert failure.index('__disable_irq();')<failure.index('DIRCLR.reg')<failure.index('st_flush(')<failure.index('for (;;) __WFI();')
assert trace[trace.index('void st_inhibit_fault('):].strip()=='void st_inhibit_fault(uint8_t reason) {\n    uint32_t key=st_lock(); if (!fault) fault=reason; st_unlock(key);\n}'
base=ROOT/'firmware/upstream-diagnostic/build'
assert (src/'startup_trace_flash.c').read_bytes()==(base/'src/startup_trace_flash.c').read_bytes()
results=[]
flags=['clang','-std=gnu99','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src)]
exe=out/'storage'
subprocess.run([*flags,'-DPROPOSED',str(EIGHT/'test_storage.c'),str(src/'startup_trace.c'),'-o',str(exe)],check=True)
for case in ['tail','summary-reserved','partial-budget','terminal-once','saturation','gated','cuts','read-error','full','budgets','inhibit-facts']:
 r=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=20);assert r.returncode==0 and not r.stderr,(case,r.returncode,r.stderr)
 results.append(dict(case=case,exitCode=r.returncode))
exe=out/'capability'
subprocess.run([*flags,'-Wno-unused-function','-DST_HOST','-DEA9_NO_LOG','-I'+str(base/'tools/hosttest'),str(EIGHT/'test_capability.c'),str(a.source/'tools/hosttest/shim.c'),*[str(src/(n+'.c')) for n in ['startup_trace','emount','emount_packets','em_owner','em_shutdown','em_frame']],'-o',str(exe)],check=True)
for n in [9,10,11]:
 r=subprocess.run([str(exe),str(n)],capture_output=True,text=True,timeout=10);assert r.returncode==0 and not r.stderr,(n,r.returncode,r.stderr)
 results.append(dict(case='capability-'+str(n),exitCode=r.returncode))
(out/'result.json').write_text(json.dumps(dict(sourceManifestSHA256=sha(a.source/'manifest.json'),sourceImageSHA256=manifest['imageSHA256'],sourceGatesPassed=True,writerSourceUnchanged=True,results=results),indent=2)+'\n')
print(f'{len(results)} final-source diagnostic cases pass; terminal flush and RAM-only fault source gates pass')
