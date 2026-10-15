#!/usr/bin/env python3
"""Source-level integer regression for a future overlay, no device boundary."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();out.mkdir(exist_ok=False)
m=json.loads((ROOT/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
rows=[];normal={}
def function(s,name):
 start=s.index(name);start=s.rfind('\n',0,start)+1;i=s.index('{',start);depth=1;j=i+1
 while depth:
  depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[start:j]+'\n'
for label in ['frozen33','proposal']:
 work=out/label;shutil.copytree(BASE/'src',work/'src')
 if label=='proposal':runpy.run_path(str(HERE/'apply.py'))['apply'](work)
 src=work/'src';dest=work/'harness';dest.mkdir()
 for n in ['servo.h','emount.h','focus_map.h','focus_dist.h','focus_pred.h','delay.h','motor.h','abs_encoder.h','startup_trace.h']:shutil.copyfile(src/n,dest/n)
 shutil.copyfile(ROOT/'firmware/upstream-hardening/lanes/06-motion/board_host.h',dest/'board.h')
 encoder=(src/'abs_encoder.c').read_text();(dest/'tracker.inc').write_text(function(encoder,'int32_t abs_encoder_track(void)'))
 main=(src/'main.c').read_text();(dest/'target.inc').write_text(function(main,'static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)\n{'))
 start=main.index('static const struct servo_cfg STOCK =');end=main.index('\n};',start)+3
 (dest/'stock.inc').write_text(re.search(r'^#define MOVE_DUTY\s+.*$',main,re.M)[0]+'\n'+main[start:end]+'\n')
 fixture=(HERE/'test.c').read_text().replace('#include "servo.h"','#include "startup_trace.h"\n#include "servo.h"').replace('static int32_t tracked(void)','int32_t tracked(void)')
 (dest/'test.c').write_text(fixture);(dest/'bridge.h').write_text('#include <stdint.h>\nint32_t tracked(void);\n')
 (dest/'servo.c').write_text((src/'servo.c').read_text().replace('abs_encoder_track()', 'tracked()'))
 exe=dest/'probe';flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(dest),'-include',str(dest/'bridge.h')]
 cmd=[*flags,dest/'test.c',dest/'servo.c',src/'focus_map.c',src/'focus_dist.c',src/'focus_pred.c','-o',exe]
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True);assert r.returncode==0,r.stderr
 for case in ['servo-positive','servo-negative','relative-positive','relative-negative','normal','predictor-arbitrary']:
  r=subprocess.run([str(exe),case],text=True,capture_output=True,timeout=60)
  expected_ok=case=='normal' or (label=='proposal' and case!='predictor-arbitrary')
  assert (r.returncode==0)==expected_ok,(label,case,r.returncode,r.stdout,r.stderr)
  if not expected_ok:assert 'runtime error: signed integer overflow' in r.stderr,(case,r.stderr)
  if case=='normal':normal[label]=r.stdout
  rows.append(dict(source=label,case=case,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:1800]))
assert normal['frozen33']==normal['proposal']
result=dict(status='partial-future-overlay-not-a-candidate',baseImageSHA256=m['imageSHA256'],results=rows,normalOutputsIdentical=True,hardwareReportsSent=0,limits='Responsive inconsistent raw encoder history is a synthetic fault path; arbitrary predictor INT32 input is separately unproven reachable. No full range closure, physical test, release build or image change.')
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
