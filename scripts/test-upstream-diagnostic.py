#!/usr/bin/env python3
"""Host regressions and frozen 3.1 negative controls; no USB access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=False,exist_ok=False)
work=ROOT/'firmware/upstream-diagnostic/build'
tests=ROOT/'firmware/upstream-diagnostic/tests'
src=work/'src'
manifest=json.loads((work/'manifest.json').read_text())
for name,expected in manifest['sources'].items():
    assert hashlib.sha256((work/name).read_bytes()).hexdigest()==expected,name
run=lambda cmd,**kw:subprocess.run([str(x) for x in cmd],check=True,capture_output=True,text=True,**kw)
flags=['clang','-std=gnu99','-O2','-Wall','-Wextra','-Werror','-DST_HOST',
       '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(src)]
unit=out/'trace-test'
run([*flags,'-DST_WAIT_BUDGET=16',tests/'test_trace.c',src/'startup_trace.c','-o',unit])
result=run([unit,out/'trace-fixture.bin'])
(out/'trace.log').write_text(result.stdout)
shim=(work/'tools/hosttest/shim.c').read_text()
shim=shim.replace('static unsigned level_idx;',
 '''static unsigned level_idx;
static uint8_t early_buf[64];
static uint16_t early_len;
void host_early_payload(const uint8_t *p,uint16_t n) {
    memcpy(early_buf,p,n); early_len=n;
}''')
needle='int v = level_script[level_idx++];'
assert shim.count(needle)==1
shim=shim.replace(needle,needle+'\n\t\tif (v && early_len) host_preload_rx(early_buf,early_len);')
(out/'shim.c').write_text(shim)
cases=[]
for label,source in [('current',src),('frozen31',ROOT/'firmware/upstream-baseline/build/50f14/src')]:
    if label=='frozen31':
        record=json.loads((ROOT/'docs/evidence/upstream-baseline-build-2026-10-14.json').read_text())
        for name in ('emount.c','emount.h','emount_packets.c'):
            assert hashlib.sha256((source/name).read_bytes()).hexdigest()==record['results']['50f14']['sources']['src/'+name]
    binary=out/label
    run([*flags,'-DEA9_NO_LOG','-I'+str(source),'-I'+str(work/'tools/hosttest'),
         tests/'test_first_window.c',out/'shim.c',source/'emount.c',source/'emount_packets.c',
         src/'startup_trace.c',tests/'trace_host.c','-o',binary])
    for split in range(12):
        trial=subprocess.run([str(binary),str(split)],capture_output=True,text=True,timeout=10)
        assert not trial.stderr,trial.stderr
        expected=0 if label=='current' or split==0 else 1
        assert trial.returncode==expected,(label,split,trial.returncode,trial.stdout)
        cases.append({'source':label,'bytesBeforeObservedRise':split,'exitCode':trial.returncode,
                      'openerAnswered':trial.returncode==0})
# Retain all eight upstream host outcomes; add trace-only boundary implementations.
wrapper=out/'hostcc'
wrapper.write_text('#!/bin/sh\nexec clang -DST_HOST -I"'+str(src)+'" "$@" "'+str(src/'startup_trace.c')+'" "'+str(tests/'trace_host.c')+'"\n')
wrapper.chmod(0o700)
original=run(['make','hosttest','HOSTCC='+str(wrapper),'OUT='+str(out/'host-upstream')],cwd=work)
(out/'upstream-hosttests.log').write_text(original.stdout+original.stderr)
evidence={'status':'passed-offline-camera-unqualified','currentFirstWindowCasesPassed':12,
          'candidateImageSHA256':manifest['imageSHA256'],
          'currentSourceSHA256':{name:manifest['sources'][name] for name in
              ('src/emount.c','src/emount.h','src/startup_trace.c','src/startup_trace.h')},
          'frozen31EarlyPrefixFailuresDetected':11,'frozen31NoEarlyBytesControlPassed':True,
          'upstreamHostOutcomesPassed':8,'traceStorageAndGuardTestsPassed':True,
          'sanitizers':['AddressSanitizer','UndefinedBehaviorSanitizer'],
          'cases':cases,'hardwareReportsSent':0,
          'limits':'Scripted pins, RX arrival and immediate TX; main, MCU ISR timing, flash electrical programming and A7C II traffic are not executed.'}
(out/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps({k:v for k,v in evidence.items() if k!='cases'},indent=2))
