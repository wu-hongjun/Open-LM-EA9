#!/usr/bin/env python3
"""Manifest-bound synthetic grammar/capacity controls on exact 3.4 source."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'firmware/candidates/3.4.0/contax-zeiss-50-f1-4.manifest.json').read_text())
def verify():
 for name,digest in m['sources'].items():assert sha(source/name)==digest,name
verify();shutil.copytree(source/'src',out/'src');shutil.copytree(source/'tools',out/'tools')
flow=ROOT/'firmware/upstream-hardening/followup/16-query-flow/test_flow.c'
(out/'flow_helpers.inc').write_text(flow.read_text())
src=out/'src';s=(src/'main.c').read_text()
def function(s,name):
 a=s.index(name+'\n{');a=s.rfind('\n',0,a)+1;b=s.index('\n}',a)+2;return s[a:b]+'\n'
worker=function(s,'static void focus_answer_queries(void)').replace('if (tag == EM_REC_Q_POS2D)','compute_hook();\n        if (tag == EM_REC_Q_POS2D)')
(out/'worker.inc').write_text(worker)
pump=function(s,'static void pump(int32_t pos)').replace('{\n','{\n    pumps++;pump_depth++;if(pump_depth>max_depth)max_depth=pump_depth;\n',1).replace('\tvdd_track_sample();','\tvdd_track_sample();\n    pump_depth--;')
(out/'pump.inc').write_text(pump)
(src/'emount.c').write_text((src/'emount.c').read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n')
(out/'servo.c').write_text((src/'servo.c').read_text())
trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','')
(out/'trace.c').write_text(trace)
flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(out),'-I'+str(out/'tools/hosttest'),'-I'+str(src)]
cmd=[*flags,HERE/'test_batches.c',out/'tools/hosttest/shim.c',out/'trace.c',out/'servo.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred']],'-o',out/'probe']
r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True);assert not r.returncode,r.stderr
rows=[]
for n,cycles in [(n,1) for n in range(6)]+[(4,8)]:
 for header in [0,1]:
  for drive in [0,1]:
   args=list(map(str,[n,header,drive,cycles]));r=subprocess.run([str(out/'probe'),*args],text=True,capture_output=True,timeout=15)
   (out/('-'.join(args)+'.txt')).write_text(r.stdout+r.stderr)
   assert not r.returncode,(args,r.stdout,r.stderr)
   line=next(l for l in r.stdout.splitlines() if l.startswith('SUMMARY '))
   values={k:int(v) for k,v in (x.split('=') for x in line.split()[1:])}
   rows.append(dict(recordsPerFrame=n,cycles=cycles,publicStateHeader=bool(header),drivePerCycle=bool(drive),**values))
verify()
report=dict(status='exact-3.4-synthetic-capacity-controls',imageSHA256=m['imageSHA256'],manifestSourcesVerified=len(m['sources']),cases=len(rows),sanitizers=['address','undefined'],results=rows,hardwareReportsSent=0,cameraQualified=False,inputs={p.name:sha(p) for p in [HERE/'test_batches.c',HERE/'run_batches.py',flow]})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
