#!/usr/bin/env python3
"""Focused composition tests using source-bound bodies and actual protocol modules."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.output.resolve()
assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
out.mkdir(exist_ok=False);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((source/'manifest.json').read_text())
for name,h in manifest['sources'].items():assert sha(source/name)==h,name
shutil.copytree(source/'src',out/'src');shutil.copytree(source/'tools',out/'tools')
def function(s,name):
 start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1;end=s.index('\n}',start)+2
 return s[start:end]+'\n'
s=(out/'src/main.c').read_text();encoder=(out/'src/abs_encoder.c').read_text()
worker=function(s,'static void focus_answer_queries(void)').replace('if (tag == EM_REC_Q_POS2D)','compute_hook();\n        if (tag == EM_REC_Q_POS2D)')
(out/'worker.inc').write_text(worker);(out/'pump.inc').write_text(function(s,'static void pump(int32_t pos)'))
(out/'abort.inc').write_text(function(s,'static uint8_t focus_invalid(void)')+function(s,'static uint8_t focus_abort(void)'))
board=(out/'src/board.h').read_text();tracker=re.search(r'^#define ENC_COUNTS\s+.*$',board,re.M).group(0)+'\n'+function(encoder,'int32_t abs_encoder_track(void)')
(out/'tracker.inc').write_text(tracker)
em=out/'src/emount.c';em.write_text(em.read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n')
(out/'servo.c').write_text((out/'src/servo.c').read_text())
trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(out/'trace.c').write_text(trace)
shim=(out/'tools/hosttest/shim.c').read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(old)==1
(out/'shim.c').write_text(shim.replace(old,old+'\n    extern void send_hook(const uint8_t *);send_hook(buf);'))
flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(out),'-I'+str(out/'tools/hosttest'),'-I'+str(out/'src')]
exe=out/'probe';cmd=[*flags,HERE/'test_composition.c',out/'shim.c',out/'trace.c',out/'servo.c',*[out/'src'/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred']],'-o',exe]
r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
rows=[]
for case in ['pump-homed-session','pump-unhomed-session','pump-homed-shutdown','pump-unhomed-shutdown','capture','servo-session','servo-shutdown','servo-coordinate-loop','servo-coordinate-final']:
 r=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=10);assert r.returncode==0,(case,r.stdout,r.stderr)
 rows.append(dict(case=case,stdout=r.stdout.strip()))
for name,h in manifest['sources'].items():assert sha(source/name)==h,name
(out/'result.json').write_text(json.dumps(dict(source=str(source),sourceHashes=manifest['sources'],results=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
