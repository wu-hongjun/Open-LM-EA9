#!/usr/bin/env python3
"""Offline composed reference admission checks and frozen 2.9 cancellation control."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
base=ROOT/'firmware/ea9';record=json.loads((ROOT/'firmware/candidates/2.9.0/regression-inputs.json').read_text())
sources=['hosttest/test_home_readiness.c','hosttest/sim_motor.c','hosttest/shim.c','src/emount.c','src/emount_packets.c','src/lens_profile.c','src/lens_aperture.c',
         'src/factory_servo.c','src/factory_af.c','src/af_control.c','src/af_reference.c','src/af_completion.c','src/io_guard.c','src/focus_map.c','src/focus_dist.c','src/focus_motion.c']
flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-Wno-over-aligned','-fsanitize=address,undefined','-fno-sanitize-recover=all',
       '-ffunction-sections','-fdata-sections','-Wl,-dead_strip','-DEA9_SIM_MOTOR','-DEA9_NO_LOG','-DEA9_FACTORY_AF','-DEA9_AF_BUILD','-Ihosttest','-Isrc']
rows=[]
for label in ['current','frozen29']:
    work=base
    if label=='frozen29':
        work=out/'frozen29/firmware/ea9'
        for name,h in record['files'].items():
            data=subprocess.run(['git','show',record['sourceGitCommit']+':'+name],cwd=ROOT,capture_output=True,check=True).stdout;assert hashlib.sha256(data).hexdigest()==h
            dest=out/'frozen29'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        (work/'hosttest/test_home_readiness.c').write_bytes((base/'hosttest/test_home_readiness.c').read_bytes())
    exe=out/(label+'-probe')
    subprocess.run(flags+(['src/em_arbitration.c'] if label=='current' else ['-DEA9_FROZEN29'])+sources+['-o',str(exe)],cwd=work,check=True)
    for case in ['resume','budget','fault','shutdown','capture','stop-before-home','session-reset'] if label=='current' else ['resume']:
        run=subprocess.run([str(exe),case,str(ROOT/'firmware/candidates/2.9.0/contax-zeiss-50-f1-4.bin')],capture_output=True,text=True)
        expected=0 if label=='current' else 1
        if run.returncode!=expected or (expected and 'cancelled reference stayed permanently unready' not in run.stderr):raise RuntimeError(f'{label}/{case}: {run.returncode}\n{run.stdout}{run.stderr}')
        rows.append({'source':label,'case':case,'exitCode':run.returncode,'output':run.stdout.strip(),'diagnostic':run.stderr.strip()})
inputs={base/s for s in sources}|set(base.rglob('*.h'))|{base/'src/main.c',base/'src/em_arbitration.c',Path(__file__).resolve()}
e={'passingCurrentCases':7,'detectedFrozen29Cases':1,'cases':rows,'hardwareReportsSent':0,'cameraQualified':False,
   'frozenSourceGitCommit':record['sourceGitCommit'],'maximumHomeAttemptsPerBoot':2,
   'contract':'Actual foreground home/reference/command/shutdown routines, synthetic initialization and parsed commands, inherited mechanical sensor/clock model and UART/voltage shims. No real MCU reset, camera, IRQ latency, optics or physical end-stop proof.',
   'profileSHA256':hashlib.sha256((ROOT/'firmware/candidates/2.9.0/contax-zeiss-50-f1-4.bin').read_bytes()[-256:]).hexdigest(),
   'sourceSHA256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(inputs)}}
(out/'results.json').write_text(json.dumps(e,indent=2)+'\n');print(json.dumps({k:e[k] for k in ['passingCurrentCases','detectedFrozen29Cases','hardwareReportsSent']},indent=2))
