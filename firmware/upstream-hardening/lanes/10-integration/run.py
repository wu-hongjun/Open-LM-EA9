#!/usr/bin/env python3
"""Offline explicit IRQ cuts through composed production dispatcher."""
import argparse,hashlib,json,subprocess,shutil,runpy
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--proposed',action='store_true');p.add_argument('--already-applied',action='store_true');a=p.parse_args()
out=a.output.resolve();out.mkdir(exist_ok=False)
shutil.copytree(a.source/'src',out/'src');shutil.copytree(a.source/'tools',out/'tools')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={p.name:sha(p) for p in sorted((out/'src').glob('*.[ch]'))}
assert not (a.proposed and a.already_applied)
if a.proposed:runpy.run_path(str(HERE/'apply.py'))['apply'](out)
p=out/'src/emount.c';s=p.read_text()
s=s.replace('#include "em_owner.h"','#include "em_owner.h"\nextern void integration_hook(int);')
# Explicit boundary immediately before length check, with all normal ownership guards already passed.
anchor='\t/* These handlers consume two payload bytes.'
assert s.count(anchor)==1;s=s.replace(anchor,'\tintegration_hook(1);\n'+anchor)
anchor='                        em_handshake_done = 1;'
assert s.count(anchor)==1;s=s.replace(anchor,'                        integration_hook(2);\n'+anchor)
anchor='\treturn em_transmit(frame, p->len);'
assert s.count(anchor)==1;s=s.replace(anchor,'\tintegration_hook(3);\n'+anchor)
anchor='        const struct em_owned_request *request = g_retry ? g_retry : em_owner_take(&g_owner);'
assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n        integration_hook(4);')
p.write_text(s)
trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text()
trace=trace.replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','')
(out/'trace_host.c').write_text(trace)
cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(out/'src'),'-I'+str(out/'tools/hosttest'),str(HERE/'test_commit.c'),str(out/'tools/hosttest/shim.c'),str(out/'trace_host.c')]+[str(out/'src'/f'{n}.c') for n in ['emount','emount_packets','startup_trace','em_frame','em_owner','em_shutdown']]+['-o',str(out/'probe')]
subprocess.run(cmd,check=True)
results=[]
for case in [(0,1),(1,25),(1,1),(2,1),(2,22),(3,1),(4,1)]:
 r=subprocess.run([str(out/'probe'),*map(str,case)],capture_output=True,text=True,timeout=10)
 results.append(dict(point=case[0],interruptID=case[1],exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr))
 print(results[-1])
 expected=0 if a.proposed or a.already_applied or case in [(0,1),(1,25)] else -6 if case==(1,1) else 1
 assert r.returncode==expected,(case,r.returncode,expected,r.stdout,r.stderr)
 if a.proposed or a.already_applied:assert not r.stderr,r.stderr
(out/'result.json').write_text(json.dumps(dict(inputs=inputs,proposed=a.proposed,alreadyApplied=a.already_applied,results=results),indent=2)+'\n')
