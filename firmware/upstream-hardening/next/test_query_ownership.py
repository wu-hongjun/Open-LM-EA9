#!/usr/bin/env python3
"""Local C query lifetime/worker-budget regression, no device APIs."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'firmware/upstream-hardening/followup/12-query'
BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--source',required=True,type=Path);a=p.parse_args();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
composed=a.source.resolve()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.manifest.json').read_text())
for name,digest in m['sources'].items():assert sha(BASE/name)==digest,name
cm=json.loads((composed/'manifest.json').read_text());assert cm['loaderVersion']==[3,4,0]
for name,digest in cm['sources'].items():assert sha(composed/name)==digest,name

cases=[(0,0),(1,1),(1,2),(2,1),(2,2),(3,1),(3,2),(4,1),(4,2),(5,0),(6,0)]
rows=[];wire={};observations=[]
for label in ['frozen33','proposal']:
 work=out/label;shutil.copytree((composed if label=='proposal' else BASE)/'src',work/'src');shutil.copytree(BASE/'tools',work/'tools')
 src=work/'src';main=(src/'main.c').read_text();start=main.index('static void focus_answer_queries(void)\n{');end=main.index('\n}\n',start)+3;worker=main[start:end]
 if label=='frozen33':worker=worker.replace('while (em_take_query(&tag, &operand)) {','while (em_take_query(&tag, &operand)) {\n        query_cut(1);')
 else:worker=worker.replace('if (!taken) return;','if (!taken) return;\n        query_cut(1);')
 needle='if (tag == EM_REC_Q_POS2D)';assert worker.count(needle)==1
 worker=worker.replace(needle,'query_compute_hook();\n        '+needle)
 (work/'worker.inc').write_text(worker+'\n')
 em=(src/'emount.c').read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n';(src/'emount.c').write_text(em)
 shim=(work/'tools/hosttest/shim.c').read_text();needle='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(needle)==1
 shim=shim.replace(needle,needle+'\n    extern void query_send_hook(const uint8_t *);query_send_hook(buf);');(work/'shim.c').write_text(shim)
 trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(work/'trace.c').write_text(trace)
 exe=work/'probe';flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(work),'-I'+str(work/'tools/hosttest')]
 cmd=[*flags,HERE/'test_query.c',work/'shim.c',work/'trace.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist']],'-o',exe]
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True);assert r.returncode==0,r.stderr
 for reverse in (0,1):
  for action,cut in cases:
   r=subprocess.run([str(exe),str(action),str(cut),'1',str(reverse)],text=True,capture_output=True,timeout=15)
   expected_ok=label=='proposal' or action in (0,6)
   assert (r.returncode==0)==expected_ok,(label,action,cut,reverse,r.returncode,r.stdout,r.stderr)
   if not expected_ok:assert 'Assertion failed' in r.stderr or 'Assertion' in r.stderr,r.stderr
   if action in (0,6):
    value=next(line for line in r.stdout.splitlines() if line.startswith('wire06='));key=(action,reverse)
    if label=='frozen33':wire[key]=value
    else:assert wire[key]==value,(key,wire[key],value)
   rows.append(dict(source=label,action=action,cut=cut,reverse=reverse,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:600]))
# Demonstrate the old-session bytes on the wire independently of the
# failing assertions above. The compatibility mode expects the old defect.
exe=out/'frozen33/probe'
for reverse in (0,1):
 for cut in (1,2):
  r=subprocess.run([str(exe),'1',str(cut),'0',str(reverse)],text=True,capture_output=True,timeout=15)
  assert r.returncode==0 and not r.stderr,(cut,reverse,r.stdout,r.stderr)
  wireline=next(line for line in r.stdout.splitlines() if line.startswith('wire06='))
  assert len(bytes.fromhex(wireline.split('=',1)[1]))==51
  observations.append(dict(cut=cut,reverse=reverse,stdout=r.stdout.strip()))
result=dict(status='tested-exact-offline-composition',composedImageSHA256=cm['imageSHA256'],composedManifestSHA256=sha(composed/'manifest.json'),baseImageSHA256=m['imageSHA256'],casesPerSource=22,frozenNegativeControls=18,proposedPasses=22,ordinaryAndCaptureWireUnchanged=True,oldSessionWireObservations=observations,results=rows,hardwareReportsSent=0,cameraQualified=False)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
