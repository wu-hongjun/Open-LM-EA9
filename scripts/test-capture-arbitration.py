#!/usr/bin/env python3
"""Finite real-responder ordering regressions, with exact frozen 2.9 controls."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
out=p.parse_args().output.resolve();out.mkdir(parents=True,exist_ok=False)
base=ROOT/'firmware/ea9'
record=json.loads((ROOT/'firmware/candidates/2.9.0/regression-inputs.json').read_text())
cases=['window-gap','capture-gap','shutdown-gap','shutdown-in-05','snapshot-deferred','new-session-in-final','fail-05','fail-06']
cases.append('capture-sequence')
cases += ['shutdown-length-'+str(n) for n in [9,11,16,19,27,32,48,64,65]]
negative={'window-gap':'status06 sent after receive interruption','capture-gap':'status06 sent after receive interruption',
          'shutdown-gap':'status06 sent after shutdown admission','shutdown-in-05':'status06 sent after shutdown admission',
          'snapshot-deferred':'control sent during receive window','new-session-in-final':'old final reply armed new session',
          'capture-sequence':'capture opener did not echo complete request'}
results=[]
for label in ['current','frozen29']:
    directory=out/label
    if label=='current':
        paths={str(x.relative_to(ROOT)) for x in base.rglob('*.h')}
        paths.update('firmware/ea9/'+s for s in ['src/emount.c','src/em_arbitration.c','src/emount_packets.c','src/lens_profile.c','src/lens_aperture.c','src/io_guard.c','hosttest/shim.c'])
    else: paths=record['files']
    for name in paths:
        data=(ROOT/name).read_bytes() if label=='current' else subprocess.run(['git','show',record['sourceGitCommit']+':'+name],cwd=ROOT,capture_output=True,check=True).stdout
        if label!='current':assert hashlib.sha256(data).hexdigest()==record['files'][name]
        destination=directory/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
    work=directory/'firmware/ea9'
    (work/'hosttest/test_capture_arbitration.c').write_bytes((base/'hosttest/test_capture_arbitration.c').read_bytes())
    shim=work/'hosttest/shim.c';text=shim.read_text()
    before='void delay_us(uint32_t us) { (void)us; }';assert text.count(before)==1
    text=text.replace(before,'void host_probe_delay_us(uint32_t us);\nvoid delay_us(uint32_t us) { host_probe_delay_us(us); }')
    before='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)';assert text.count(before)==1
    text=text.replace(before,'void host_probe_after_tx(uint8_t id);\n'+before)
    text=text.replace('\t\tsent_n++;','\t\tsent_n++;\n\t\thost_probe_after_tx(buf[5]);');shim.write_text(text)
    sources=['hosttest/test_capture_arbitration.c','hosttest/shim.c','src/emount_packets.c','src/lens_profile.c','src/lens_aperture.c','src/io_guard.c']
    if label=='current':sources.append('src/em_arbitration.c')
    exe=out/(label+'-probe')
    flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-Wno-over-aligned','-fsanitize=address,undefined','-fno-sanitize-recover=all',
           '-ffunction-sections','-fdata-sections','-Wl,-dead_strip','-DEA9_AF_BUILD','-DEA9_NO_LOG','-Ihosttest','-Isrc']
    subprocess.run(flags+sources+['-o',str(exe)],cwd=work,check=True)
    for case in cases if label=='current' else negative:
        run=subprocess.run([str(exe),case],capture_output=True,text=True)
        expected=0 if label=='current' else 1
        if run.returncode!=expected or (expected and negative[case] not in run.stderr):raise RuntimeError(f'{label}/{case}: {run.returncode}\n{run.stdout}{run.stderr}')
        results.append({'source':label,'case':case,'exitCode':run.returncode,'output':run.stdout.strip(),'diagnostic':run.stderr.strip()})
inputs={x for x in base.rglob('*.h')}|{base/s for s in sources}|{base/'src/emount.c',Path(__file__).resolve()}
e={'passingCurrentCases':len(cases),'detectedFrozen29Cases':len(negative),'cases':results,'hardwareReportsSent':0,'cameraQualified':False,
   'frozenSourceGitCommit':record['sourceGitCommit'],
   'contract':'Supplied CS/VD callbacks and immediate UART completion; delay and TX-boundary event injection only. No actual elapsed timing, concurrent hardware IRQs, full camera grammar or optical tests.',
   'sourceSHA256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(inputs)}}
(out/'results.json').write_text(json.dumps(e,indent=2)+'\n');print(json.dumps({k:e[k] for k in ['passingCurrentCases','detectedFrozen29Cases','hardwareReportsSent']},indent=2))
