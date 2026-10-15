#!/usr/bin/env python3
"""Offline frame gate/capture replay and actual dispatcher negative controls.

The published 3.2 image and its build sources are immutable inputs. A temporary
source overlay adds the gate to emount.c for these host tests only. No candidate
is published, no device API is used, and this does not validate camera timing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT=Path(__file__).resolve().parents[1]
LANE=ROOT/'firmware/upstream-hardening'
BASE=ROOT/'firmware/upstream-diagnostic/build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
out=args.output.resolve(); out.mkdir(parents=False,exist_ok=False)
manifest=json.loads((BASE/'manifest.json').read_text())
committed_manifest=ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.manifest.json'
assert manifest==json.loads(committed_manifest.read_text()), 'Materialized build differs from the committed release manifest'
assert manifest['imageSHA256']=='e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df'
for name,digest in manifest['sources'].items():
    assert sha(BASE/name)==digest,name
assert sha(ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin')==manifest['imageSHA256']
reference_prefix='upstream/weiziqian/E-mount-impl-on-Techart-EA9/'
catalog=dict(line.split(maxsplit=1)[::-1] for line in
             (ROOT/'references/checksums.sha256').read_text().splitlines())
for name in ('tools/hosttest/shim.c',):
    assert sha(BASE/name)==catalog[reference_prefix+name],name
corpus=ROOT/'references/analysis/entropy512-frames.jsonl'
frames=[]
for line in corpus.read_text().splitlines():
    record=json.loads(line)
    if record.get('checksum_valid') and record.get('terminator_valid') and 'hex' in record:
        window=bytes.fromhex(record['hex'])
        assert 9<=len(window)<=256
        frames.append(struct.pack('<H',len(window))+window)
fixture=out/'capture-windows.bin'; fixture.write_bytes(b''.join(frames))
assert len(frames)==3456

flags=['clang','-std=gnu99','-O2','-Wall','-Wextra','-Werror',
       '-fsanitize=address,undefined','-fno-omit-frame-pointer']
def run(command):
    return subprocess.run([str(x) for x in command],capture_output=True,text=True,check=True,timeout=60)
exe=out/'frames'
run([*flags,'-I'+str(LANE/'src'),LANE/'tests/test_frames.c',LANE/'src/em_frame.c','-o',exe])
capture_result=json.loads(run([exe,fixture]).stdout)

# The sole admission overlay is reviewable. Other dispatcher/servo behavior is
# exactly 3.2. Keep actual window length for captures; semantic guards use only
# the validated frame length so checksum and padding never become operands.
source=(BASE/'src/emount.c').read_text()
source=source.replace('#include "startup_trace.h"','#include "startup_trace.h"\n#include "em_frame.h"',1)
before='\tif (n < EM_HEADER_LEN || rx[0] != EM_FRAME_START) {'
assert source.count(before)==1
source=source.replace(before,
    '\tstruct em_frame_view view;\n'
    '\tif (em_frame_open(rx,n,&view) != EM_FRAME_OK) {')
before='g_req[i] = (i < n) ? rx[i] : 0;'
assert source.count(before)==1
source=source.replace(before,'g_req[i] = (i < view.length) ? rx[i] : 0;')
for before,after in [
    ('rx[5] == 0x08u && n >= 8','rx[5] == 0x08u && view.length >= 11'),
    ('rx[5] == EM_ID_APERTURE && n >= 11','rx[5] == EM_ID_APERTURE && view.length >= 11'),
    ('rx[5] == 0x04u && n >= 20','rx[5] == 0x04u && view.length >= 20'),
    ('rx[5] == 0x03u && n >= 16','rx[5] == 0x03u && view.length >= 16'),
    ('rx[5] == EM_ID_SESSION && n >= 17','rx[5] == EM_ID_SESSION && view.length >= 17'),
]:
    assert source.count(before)==1,before
    source=source.replace(before,after)
patched=out/'emount-gated.c'; patched.write_text(source)
cases=['valid-init','valid-padding','valid-move','checksum','terminator',
       'length-zero','length-high','truncated','header-only','bad-move','truncated-move',
       'short-capability','short-offer','short-mode','short-aperture']
controls=cases[:3]
results=[]
for label,src,extra in [
    ('frozen32',BASE/'src/emount.c',[]),
    ('gated-overlay',patched,[LANE/'src/em_frame.c'])
]:
    exe=out/label
    run([*flags,'-DST_HOST','-DEA9_NO_LOG','-I'+str(LANE/'src'),
         '-I'+str(BASE/'src'),'-I'+str(BASE/'tools/hosttest'),
         LANE/'tests/test_dispatch.c',BASE/'tools/hosttest/shim.c',src,
         BASE/'src/emount_packets.c',BASE/'src/startup_trace.c',
         ROOT/'firmware/upstream-diagnostic/tests/trace_host.c',*extra,'-o',exe])
    for case in cases:
        result=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=10)
        expected=1 if label=='frozen32' and case not in controls else 0
        assert result.returncode==expected,(label,case,result.returncode,result.stdout,result.stderr)
        assert not result.stderr,result.stderr
        results.append({'source':label,'case':case,'exitCode':result.returncode,
                        'outcome':result.stdout.strip()})
inputs=[Path(__file__).resolve(),corpus,committed_manifest,BASE/'manifest.json',BASE/'src/emount.c',
        BASE/'src/emount.h',BASE/'src/emount_packets.c',BASE/'src/startup_trace.c',
        BASE/'tools/hosttest/shim.c',ROOT/'firmware/upstream-diagnostic/tests/trace_host.c',
        *sorted((LANE/'src').glob('*')), *sorted((LANE/'tests').glob('*'))]
report={
    'status':'passed-offline-overlay-not-released',
    'frozenCandidateVersion':'3.2.0','frozenImageSHA256':manifest['imageSHA256'],
    'captures':capture_result,'productionDispatcherCases':results,
    'frozenMalformedAdmissionsDetected':8,'frozenPaddingOperandDefectsDetected':4,
    'validProductionControlsPerSource':3,
    'gatedProductionCasesPassed':15,'hardwareReportsSent':0,
    'publishedFirmwareChanged':False,'cameraQualified':False,
    'sourceSHA256':{str(p.relative_to(ROOT)):sha(p) for p in inputs},
    'overlaySHA256':sha(patched),
    'limits':'Scripted chip-select and immediate transmit; no real UART/IRQ/NVM/camera timing or optical AF. Valid framing does not establish valid message operands or capture/shutdown arbitration.'
}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('sourceSHA256','productionDispatcherCases')},indent=2))
