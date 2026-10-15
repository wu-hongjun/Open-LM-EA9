#!/usr/bin/env python3
"""Prove release-only legacy counter removal leaves VD timing/wire unchanged."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=ROOT/'artifacts/private/bounded34b'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((BASE/'manifest.json').read_text())
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
rows=[];wire={}
for logging in [False,True]:
 for proposal in [False,True]:
  label=('debug' if logging else 'release')+('-proposal' if proposal else '-frozen');work=out/label;shutil.copytree(BASE/'src',work/'src');shutil.copytree(BASE/'tools',work/'tools')
  if proposal:runpy.run_path(str(HERE/'apply_counter.py'))['apply'](work)
  flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work/'src'),'-I'+str(work/'tools/hosttest')]
  if not logging:flags+=['-DEA9_NO_LOG']
  exe=work/'probe';cmd=[*flags,HERE/'test_counter.c',work/'tools/hosttest/shim.c',ROOT/'firmware/upstream-diagnostic/tests/trace_host.c',*[work/'src'/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace']],'-o',exe]
  r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run([str(exe),str(int(proposal and not logging))],capture_output=True,text=True);assert r.returncode==0,(label,r.stderr)
  if not proposal:wire[logging]=r.stdout
  else:assert wire[logging]==r.stdout,(label,'wire/period output changed')
  rows.append(dict(source=label,exitCode=r.returncode,outputSHA256=hashlib.sha256(r.stdout.encode()).hexdigest(),expectedCounterOmitted=proposal and not logging))
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
(out/'result.json').write_text(json.dumps(dict(status='passed',cases=rows,periodSamplesPerCase=17,wireAndPeriodOutputsIdentical=True,hardwareReportsSent=0),indent=2)+'\n');print('4 release/debug counter cases pass; 17 VD samples each, wire and period outputs identical')
