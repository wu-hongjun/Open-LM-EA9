#!/usr/bin/env python3
"""Offline extracted-production homing regressions; requires a new output dir."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from apply import apply

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'firmware/upstream-diagnostic/build'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args(); out=a.output.resolve(); out.mkdir(parents=False,exist_ok=False)
manifest=json.loads((ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.manifest.json').read_text())
assert sha(BASE/'src/main.c')==manifest['sources']['src/main.c']
source=(BASE/'src/main.c').read_text()
work=out/'overlay'; (work/'src').mkdir(parents=True)
(work/'src/main.c').write_text(source); apply(work)
cases=['stationary-control','travel-control','wrap-control','move-control',
       'pre-stop','burst-stop','stop','settle-stop','shutdown','settle-shutdown',
       'pre-shutdown','session','settle-session','commit-stop','commit-session',
       'drive-timeout','settle-timeout','frozen-clock','retry','budget',
       'shutdown-park','inhibited-park']
rows=[]
for label,s in [('frozen32',source),('overlay',(work/'src/main.c').read_text())]:
    dest=out/(label+'-fixture'); dest.mkdir()
    constants='\n'.join(re.findall(r'^#define HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|TRACE_MS)\s+.*$',s,re.M))
    begin=s.index('/* Has the mechanism stopped?') if label=='frozen32' else s.index('/* Included in main.c after pump;')
    end=s.index('\n/* Park to infinity,',begin)
    park_begin=s.index('static void park_to_infinity(void)\n{')
    park_end=s.index('\n/* Focus: drive',park_begin)
    (dest/'extracted.inc').write_text(constants+'\n'+s[begin:end]+'\n'+s[park_begin:park_end])
    exe=dest/'home'
    cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable',
         '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(dest),str(HERE/'test_home.c'),'-o',str(exe)]
    if label=='frozen32': cmd.append('-DFROZEN')
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    for case in cases:
        result=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=20)
        expected=1 if label=='frozen32' and 'control' not in case else 0
        assert result.returncode==expected,(label,case,result.returncode,result.stdout,result.stderr)
        assert not result.stderr,(label,case,result.stderr)
        rows.append({'source':label,'case':case,'expectedExit':expected,'exit':result.returncode,'output':result.stdout.strip()})
report={'status':'offline-proposal-not-released','sourceMainSHA256':sha(BASE/'src/main.c'),
        'overlayMainSHA256':sha(work/'src/main.c'),'frozenImageSHA256':manifest['imageSHA256'],
        'checks':len(rows),'negativeControls':18,'positiveControlsPerSource':4,'cases':rows,
        'cuts':['protocol command/session/shutdown admission','encoder and mechanical response','voltage sampling','PWM and GPIO','NVM writes','millisecond clock'],
        'limits':['No real IRQ timing or motor electrical bound','Stationary sensor does not prove physical infinity','Driver inhibit and session/shutdown modules required'],
        'inputs':{p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ['.py','.c','.inc']}}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['cases','inputs']},indent=2))
