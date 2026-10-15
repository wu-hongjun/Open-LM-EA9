#!/usr/bin/env python3
"""Exact 3.5 vs its sole counter restoration: release/debug wire and live trace."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from run import ROOT,HERE,IMAGE,MANIFEST,function,run,sha
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
src=a.source.resolve();out=a.output.resolve();assert src.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
m=json.loads((src/'manifest.json').read_text());assert m['imageSHA256']==IMAGE
digest=sha(src/'manifest.json');assert digest==MANIFEST;assert sha(src/'contax-zeiss-50-f1-4.bin')==IMAGE
for n,h in m['sources'].items():assert sha(src/n)==h,n
rows=[]
for logging in [False,True]:
 baseline=None
 for restored in [False,True]:
  label=('debug' if logging else 'release')+('-restored' if restored else '-final');work=out/label
  shutil.copytree(src/'src',work/'src');shutil.copytree(src/'tools',work/'tools')
  if restored:
   path=work/'src/emount.c';s=path.read_text();old='#ifndef EA9_NO_LOG\n\t\t\tem_frame_period_n++;\n#endif';assert s.count(old)==1;path.write_text(s.replace(old,'\t\t\tem_frame_period_n++;'))
  (work/'report.inc').write_text(function((work/'src/main.c').read_text(),'static void focus_report_at(int32_t counts)'))
  flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'src'),'-I'+str(work/'tools/hosttest')]
  if not logging:flags+=['-DEA9_NO_LOG']
  modules=['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred']
  run([*flags,HERE/'test_counter.c',work/'tools/hosttest/shim.c',*[work/'src'/(n+'.c') for n in modules],'-o',work/'probe'])
  output=run([work/'probe',str(int(not logging and not restored))]);(work/'output.txt').write_text(output+'\n')
  if baseline is None:baseline=output
  else:assert output==baseline
  rows.append(dict(variant=label,outputSHA256=hashlib.sha256(output.encode()).hexdigest(),counterOmitted=not logging and not restored))
assert sha(src/'manifest.json')==digest
for n,h in m['sources'].items():assert sha(src/n)==h,n
(out/'result.json').write_text(json.dumps(dict(source=str(src),manifestSHA256=digest,imageSHA256=IMAGE,sourceHashes=m['sources'],cases=rows,periodWireGPIOAndLiveTraceParity=True,samplesPerCase=17,counterWrapExercised=True,hardwareAccess=False,inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.c']}),indent=2)+'\n')
print('PASS four exact-final counter cases; VD/forecast/wire/GPIO/live-trace parity; private in-memory flash only')
