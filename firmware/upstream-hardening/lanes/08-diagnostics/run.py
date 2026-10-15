#!/usr/bin/env python3
"""Offline sanitized storage regressions, frozen controls and source gate proof."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'firmware/upstream-diagnostic/build'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=False,exist_ok=False)
work=out/'proposed';shutil.copytree(BASE/'src',work/'src')
shutil.copytree(BASE/'tools/hosttest',work/'tools/hosttest')
# Compose the current accepted upstream proposals before adding lane08.
for name in ['apply_frame.py','apply_tx.py','lanes/02-shutdown/apply.py','lanes/01-capture/apply.py','lanes/03-homing/apply.py','lanes/05-transport/apply.py','lanes/06-motion/apply.py','lanes/07-aperture/apply.py']:
    runpy.run_path(str(ROOT/'firmware/upstream-hardening'/name))['apply'](work)
runpy.run_path(str(HERE/'apply.py'))['apply'](work)
manifest=json.loads((BASE/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['main.c','emount.c','startup_trace.c','startup_trace_flash.c']:
    assert sha(BASE/'src'/name)==manifest['sources']['src/'+name]
assert (work/'src/startup_trace_flash.c').read_bytes()==(BASE/'src/startup_trace_flash.c').read_bytes()
# Only post-UART-disable shutdown and disabled-IRQ fail-stop may call flush.
assert 'st_flush(' not in (work/'src/emount.c').read_text()
main=(work/'src/main.c').read_text();assert main.count('st_flush(')==1
assert main.index('em_uart_disable();')<main.index('st_flush(')<main.index('static void park_to_infinity(void)\n{')
results=[]
cases=['tail','summary-reserved','partial-budget','terminal-once','saturation','gated','cuts','read-error','full']
negatives=set(cases[:4])
for label,src in [('frozen32',BASE/'src'),('proposed',work/'src')]:
    exe=out/('test-'+label)
    subprocess.run(['clang','-std=gnu99','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),*(['-DPROPOSED'] if label=='proposed' else []),str(HERE/'test_storage.c'),str(src/'startup_trace.c'),'-o',str(exe)],check=True)
    for case in cases+(['budgets','inhibit-facts'] if label=='proposed' else []):
        r=subprocess.run([str(exe),case],capture_output=True,text=True)
        expected=1 if label=='frozen32' and case in negatives else 0
        assert r.returncode==expected,(label,case,r.returncode,r.stderr)
        results.append({'source':label,'case':case,'exitCode':r.returncode,'diagnostic':r.stderr.strip()})
    subprocess.run([str(exe),'fixture',str(out/(label+'-fixture.bin'))],check=True)
for label,src in [('frozen32',BASE/'src'),('proposed',work/'src')]:
    exe=out/('capability-'+label)
    extra=[src/'em_owner.c',src/'em_shutdown.c',src/'em_frame.c'] if label=='proposed' else []
    shim=(work if label=='proposed' else BASE)/'tools/hosttest/shim.c'
    subprocess.run(['clang','-std=gnu99','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-DST_HOST','-DEA9_NO_LOG','-I'+str(src),'-I'+str(BASE/'tools/hosttest'),str(HERE/'test_capability.c'),str(src/'startup_trace.c'),str(src/'emount.c'),str(src/'emount_packets.c'),str(shim),*[str(p) for p in extra],'-o',str(exe)],check=True)
    for n in [9,10,11]:
        r=subprocess.run([str(exe),str(n)],capture_output=True,text=True)
        expected=1 if label=='frozen32' and n<11 else 0
        assert r.returncode==expected,(label,n,r.returncode,r.stderr)
        results.append({'source':label,'case':'capability-'+str(n),'exitCode':r.returncode,'diagnostic':r.stderr.strip()})
subprocess.run(['python3',str(HERE/'test_decoder.py'),str(out)],check=True)
evidence={'status':'offline-proposal-tested','frozenImageSHA256':manifest['imageSHA256'],'cases':results,
          'frozenNegativeControls':len(negatives)+2,'compiledWriterSourceUnchanged':True,'liveBusFlushSitesRemoved':2,
          'hardwareReportsSent':0,'cameraQualified':False,'sanitizers':['address','undefined'],
          'sourceSHA256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(HERE.iterdir()) if p.is_file()},
          'limits':'Inert flash and scripted failure bytes; no physical endurance, voltage, timing, NVM/cache-coherence or asynchronous peripheral proof.'}
(out/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({k:v for k,v in evidence.items() if k not in ('cases','sourceSHA256')},indent=2))
