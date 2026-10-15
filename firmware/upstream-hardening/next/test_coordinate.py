#!/usr/bin/env python3
"""Source-level integer regression for a future overlay, no device boundary."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=ROOT/'firmware/upstream-hardening/build/final-33a'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--source',type=Path);a=p.parse_args();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
composed=a.source.resolve() if a.source else None
m=json.loads((ROOT/'firmware/candidates/3.3.0/contax-zeiss-50-f1-4.manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
if composed:
 cm=json.loads((composed/'manifest.json').read_text());assert cm['loaderVersion']==[3,4,0]
 for n,h in cm['sources'].items():assert sha(composed/n)==h,n
rows=[];normal={}
def function(s,name):
 start=s.index(name);start=s.rfind('\n',0,start)+1;i=s.index('{',start);depth=1;j=i+1
 while depth:
  depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[start:j]+'\n'
for label in ['frozen33','domain']:
 work=out/label;shutil.copytree((composed if composed and label=='domain' else BASE)/'src',work/'src')
 if label=='domain' and not composed:runpy.run_path(str(HERE/'apply_coordinate.py'))['apply'](work)
 src=work/'src';dest=work/'harness';dest.mkdir()
 for n in ['servo.h','emount.h','focus_map.h','focus_dist.h','focus_pred.h','delay.h','motor.h','abs_encoder.h','startup_trace.h']:shutil.copyfile(src/n,dest/n)
 shutil.copyfile(ROOT/'firmware/upstream-hardening/lanes/06-motion/board_host.h',dest/'board.h')
 encoder=(src/'abs_encoder.c').read_text();(dest/'tracker.inc').write_text(function(encoder,'int32_t abs_encoder_track(void)'))
 main=(src/'main.c').read_text();(dest/'target.inc').write_text(function(main,'static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)\n{'))
 start=main.index('static const struct servo_cfg STOCK =');end=main.index('\n};',start)+3
 (dest/'stock.inc').write_text(re.search(r'^#define MOVE_DUTY\s+.*$',main,re.M)[0]+'\n'+main[start:end]+'\n')
 fixture=(HERE/'test_coordinate.c').read_text()
 (dest/'test.c').write_text(fixture);(dest/'bridge.h').write_text('#include <stdint.h>\n#include "abs_encoder.h"\nint32_t tracked(void);\n')
 (dest/'servo.c').write_text((src/'servo.c').read_text().replace('abs_encoder_track()', 'tracked()'))
 exe=dest/'probe';flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(dest),'-include',str(dest/'bridge.h')]
 cmd=[*flags,dest/'test.c',dest/'servo.c',src/'focus_map.c',src/'focus_dist.c',src/'focus_pred.c','-o',exe]
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True);assert r.returncode==0,r.stderr
 for case in ['capacity','fault-history','normal','predictor','servo-normal']:
  r=subprocess.run([str(exe),case],text=True,capture_output=True,timeout=60)
  expected_ok=label=='domain' or case in ('normal','predictor','servo-normal')
  assert (r.returncode==0)==expected_ok,(label,case,r.returncode,r.stdout,r.stderr)
  if not expected_ok:assert 'Assertion' in r.stderr,(case,r.stderr)
  if case=='normal':normal[label]=r.stdout
  rows.append(dict(source=label,case=case,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:1800]))
assert normal['frozen33']==normal['domain']
result=dict(status='coordinate-contract-tested-no-candidate',baseImageSHA256=m['imageSHA256'],composedImageSHA256=cm['imageSHA256'] if composed else None,results=rows,normalOutputsIdentical=True,hardwareReportsSent=0,limits='Coordinate-domain admission under intact program state, fixed production scale/config and existing motor inhibit. Synthetic boundaries are not physical motion or timing qualification; arbitrary direct API inputs outside the contract excluded.')
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
