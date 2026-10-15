#!/usr/bin/env python3
"""Offline production-path injection, no device access or released-file edits."""
import argparse,hashlib,importlib.util,json,shutil,subprocess
from pathlib import Path
from apply import apply
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3];BASE=ROOT/'firmware/upstream-diagnostic/build'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--shutdown',action='store_true');a=p.parse_args()
out=a.output.resolve();out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((BASE/'manifest.json').read_text())
assert m==json.loads((ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.manifest.json').read_text())
assert m['imageSHA256']=='e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df'
assert sha(ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin')==m['imageSHA256']
for n,d in m['sources'].items():assert sha(BASE/n)==d,n
work=out/'owned';(work/'src').mkdir(parents=True)
for f in (BASE/'src').iterdir():
    if f.is_file():shutil.copyfile(f,work/'src'/f.name)
s=(work/'src/emount.c').read_text().replace('#include "startup_trace.h"','#include "startup_trace.h"\n#include "em_frame.h"')
s=s.replace('if (n < EM_HEADER_LEN || rx[0] != EM_FRAME_START)', 'struct em_frame_view view;\n\tif (em_frame_open(rx,n,&view) != EM_FRAME_OK)')
for f in ('em_frame.c','em_frame.h'):shutil.copyfile(ROOT/'firmware/upstream-hardening/src'/f,work/'src'/f)
(work/'src/emount.c').write_text(s)
if a.shutdown:
    spec=importlib.util.spec_from_file_location('shutdown_apply',HERE.parent/'02-shutdown/apply.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.apply(work)
apply(work)
# Only the transport declaration/shim changes for both host controls.
control=out/'frozen-src';shutil.copytree(BASE/'src',control)
for src in (control,work/'src'):
    h=src/'em_uart.h';h.write_text(h.read_text().replace('void     em_uart_send(', 'uint8_t  em_uart_send('))
shim=(BASE/'tools/hosttest/shim.c').read_text()
shim=shim.replace('void delay_us(uint32_t us) { (void)us; }','void host_probe_delay(uint32_t);\nvoid delay_us(uint32_t us) { host_probe_delay(us); }')
shim=shim.replace('void em_uart_send(const uint8_t *buf, uint16_t len)\n{','void host_probe_send(const uint8_t *,uint16_t);\nextern int host_tx_fail;\nextern int host_tx_fail_id;\nuint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{\n\tif (host_tx_fail || buf[5]==host_tx_fail_id) return 0;\n\thost_probe_send(buf,len);')
shim=shim.replace('\nint host_cs_released(void)', '\nint host_cs_released(void)')
start=shim.index('uint8_t em_uart_send(');end=shim.index('\nint host_cs_released',start)
part=shim[start:end];i=part.rfind('}');part=part[:i]+'\treturn 1;\n'+part[i:];shim=shim[:start]+part+shim[end:]
(out/'shim.c').write_text(shim)
trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text()
trace=trace.replace('uint32_t st_lock(void) { return 0; }', 'extern int host_irq_mask; void host_irq_replay(void);\nuint32_t st_lock(void) { uint32_t prior=host_irq_mask;host_irq_mask=1;return prior; }')
trace=trace.replace('void st_unlock(uint32_t k) { (void)k; }', 'void st_unlock(uint32_t k) { host_irq_mask=k;host_irq_replay(); }')
(out/'trace_host.c').write_text(trace)
# The only production instrumentation adds an IRQ attempt before focus-copy.
# Frozen code takes it immediately; masked code defers it until st_unlock.
for src in (control,work/'src'):
    p=src/'emount.c';s=p.read_text()
    old='\tfor (k = 0; k < sizeof(*out); k++) {'
    assert s.count(old)==1
    s=s.replace(old,'\textern void host_copy_interrupt(void);\n\thost_copy_interrupt();\n'+old)
    p.write_text(s)

cases=[['focus-copy'],['session-queues'],['failed-init'],['failed-tail'],['failed-raw'],['baseline'],['immutable'],['first-wins'],['sequence'],['active'],['session']]
for cut in range(1,7):
    for id in (0x0a,0x0b,0x1b,0x28,0x19,0x34):cases.append(['capture',str(cut),str(id),'11'])
    cases.append(['normal',str(cut),'3','16'])
for n in (9,17,64,255,256):cases.append(['capture','4','52',str(n)])
if a.shutdown:cases.append(['failed-shutdown'])
results=[]
for label,src in [('frozen32',control),('owned',work/'src')]:
    flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(BASE/'tools/hosttest')]
    extra=[]
    if label=='owned':
        flags+=['-DOWNED'];extra=[src/'em_frame.c',src/'em_owner.c']
        if a.shutdown:extra+=[src/'em_shutdown.c']
    exe=out/label if label=='frozen32' else out/'owned-probe'
    cmd=[*flags,HERE/'test_capture.c',out/'shim.c',src/'emount.c',src/'emount_packets.c',src/'startup_trace.c',out/'trace_host.c',*extra,'-o',exe]
    r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
    for case in cases:
        r=subprocess.run([str(exe),*case],capture_output=True,text=True,timeout=10)
        expected=0 if label=='owned' or case[0] in ('baseline','session','sequence','active') or (case[0]=='normal' and int(case[1])>=5) else 1
        assert r.returncode==expected,(label,case,r.returncode,r.stdout,r.stderr)
        assert not r.stderr,r.stderr
        results.append(dict(source=label,case=case,exitCode=r.returncode,result=r.stdout.strip()))
report={'frozenImageSHA256':m['imageSHA256'],'shutdownComposition':a.shutdown,'casesPerSource':len(cases),'frozenFailingControls':sum(r['exitCode']==1 for r in results),'results':results,'inputs':{str(f.relative_to(ROOT)):sha(f) for f in HERE.iterdir() if f.is_file()},'patchedSHA256':sha(work/'src/emount.c'),'hardwareAccess':False,'cameraQualified':False}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('results','inputs')},indent=2))
