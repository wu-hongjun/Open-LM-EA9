#!/usr/bin/env python3
"""Source-bound synthetic I/O tests. Never opens a device or publishes an image."""
import argparse, hashlib, json, runpy, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
out=args.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.manifest.json').read_text())
for name,digest in m['sources'].items():assert sha(BASE/name)==digest,name

def function(s,name):
 a=s.index(name+'\n{');a=s.rfind('\n',0,a)+1;b=s.index('\n}',a)+2
 return s[a:b]+'\n'

cases=['capacity','refill','event','pump-homed','pump-unhomed','servo','session','shutdown','inhibited','aborted','unready','lock','ordinary','lock-full','pump-backlog','homing-stream','servo-backlog']
rows=[];observations=[];normal_wire=None
for label in ['prior12','capacity-only','proposal','mutant-home-gate']:
 work=out/label;shutil.copytree(BASE/'src',work/'src');shutil.copytree(BASE/'tools',work/'tools')
 runpy.run_path(str(HERE.parent/'12-query/apply.py'))['apply'](work)
 if label!='prior12':runpy.run_path(str(HERE/'apply.py'))['apply'](work,pump_service=label!='capacity-only')
 src=work/'src';s=(src/'main.c').read_text()
 if label=='mutant-home-gate':s=s.replace('\tfocus_answer_queries();\n\tem_poll();','\tif (g_homed) focus_answer_queries();\n\tem_poll();')
 worker=function(s,'static void focus_answer_queries(void)')
 worker=worker.replace('if (tag == EM_REC_Q_POS2D)', 'compute_hook();\n        if (tag == EM_REC_Q_POS2D)')
 (work/'worker.inc').write_text(worker)
 pump=function(s,'static void pump(int32_t pos)')
 pump=pump.replace('{\n','{\n    pumps++;pump_depth++;if(pump_depth>max_depth)max_depth=pump_depth;\n',1)
 pump=pump.replace('\tvdd_track_sample();','\tvdd_track_sample();\n    pump_depth--;')
 (work/'pump.inc').write_text(pump)
 (src/'emount.c').write_text((src/'emount.c').read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n')
 # Servo has quoted board include, so a private copy uses the existing host shim header.
 (work/'servo.c').write_text((src/'servo.c').read_text())
 trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','')
 (work/'trace.c').write_text(trace)
 flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(src)]
 exe=work/'probe';cmd=[*flags,HERE/'test_flow.c',work/'tools/hosttest/shim.c',work/'trace.c',work/'servo.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred']],'-o',exe]
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True);assert r.returncode==0,r.stderr
 for case in cases:
  expected_ok=not ((label=='prior12' and case in cases[:6]+['lock-full','pump-backlog','homing-stream','servo-backlog']) or (label=='capacity-only' and case in cases[3:6]+['pump-backlog','homing-stream','servo-backlog']) or (label=='mutant-home-gate' and case in ['pump-unhomed','homing-stream']))
  r=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=15)
  assert (r.returncode==0)==expected_ok,(label,case,r.returncode,r.stdout,r.stderr)
  if not expected_ok:assert 'Assertion' in r.stderr,r.stderr
  if case=='ordinary':
   line=next(line for line in r.stdout.splitlines() if line.startswith('wire06='))
   if normal_wire is None:normal_wire=line
   else:assert line==normal_wire
  rows.append(dict(source=label,case=case,expectedPass=expected_ok,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:700]))
 for case in (['capacity','refill','event'] if label=='prior12' else []):
  r=subprocess.run([str(exe),case,'observe'],capture_output=True,text=True,timeout=15)
  assert r.returncode==0,(case,r.stdout,r.stderr)
  observations.append(dict(case=case,stdout=r.stdout.strip()))
# Compile the entire production units; extraction tests do not prove build completeness.
deps=ROOT/'tools/firmware-deps';arm=deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-gcc'
work=out/'proposal';src=work/'src'
flags=['-mthumb','-mcpu=cortex-m0plus','-Os','-DNDEBUG','-DEA9_NO_LOG','-D__SAMD21E17A__','-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-Werror','-std=gnu99','-fstack-usage','-I'+str(src),'-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
for unit in ['main','emount']:
 r=subprocess.run([str(arm),*flags,'-c',str(src/(unit+'.c')),'-o',str(out/(unit+'.o'))],capture_output=True,text=True);assert r.returncode==0,r.stderr
for name,digest in m['sources'].items():assert sha(BASE/name)==digest,name
report=dict(status='tested-future-overlay-not-published',baseImageSHA256=m['imageSHA256'],casesPerSource=len(cases),negativeControls=sum(not r['expectedPass'] for r in rows),proposalPasses=sum(r['source']=='proposal' and r['exitCode']==0 for r in rows),results=rows,oldBehaviorWireObservations=observations,ordinaryWireUnchanged=True,hardwareReportsSent=0,cameraQualified=False,fullArmUnitsCompiled=['main','emount'],inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.c']})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['results','oldBehaviorWireObservations']},indent=2))
