#!/usr/bin/env python3
"""Re-run existing capture production-path cases against the supplied composition."""
import argparse,json,subprocess,shutil,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(exist_ok=False);src=out/'src';shutil.copytree(a.source/'src',src)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs={p.name:sha(p) for p in src.glob('*.[ch]')}
base=ROOT/'firmware/upstream-diagnostic/build'
shim=(a.source/'tools/hosttest/shim.c').read_text()
shim=shim.replace('void delay_us(uint32_t us) { (void)us; }','void host_probe_delay(uint32_t);\nvoid delay_us(uint32_t us) { host_probe_delay(us); }')
anchor='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{'
assert shim.count(anchor)==1
shim=shim.replace(anchor,'void host_probe_send(const uint8_t *,uint16_t);\nextern int host_tx_fail, host_tx_fail_id;\n'+anchor+'\n\tif (host_tx_fail || buf[5]==host_tx_fail_id) return 0;\n\thost_probe_send(buf,len);')
(out/'shim.c').write_text(shim)
trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text()
trace=trace.replace('uint32_t st_lock(void) { return 0; }','extern int host_irq_mask; void host_irq_replay(void);\nuint32_t st_lock(void) { uint32_t prior=host_irq_mask;host_irq_mask=1;return prior; }').replace('void st_unlock(uint32_t k) { (void)k; }','void st_unlock(uint32_t k) { host_irq_mask=k;host_irq_replay(); }')
(out/'trace_host.c').write_text(trace)
p=src/'emount.c';s=p.read_text();anchor='\tfor (k = 0; k < sizeof(*out); k++) {';assert s.count(anchor)==1;s=s.replace(anchor,'\textern void host_copy_interrupt(void);\n\thost_copy_interrupt();\n'+anchor);p.write_text(s)
fixture=HERE.parent/'01-capture/test_capture.c'
cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DOWNED','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(base/'tools/hosttest'),str(fixture),str(out/'shim.c'),str(out/'trace_host.c')]+[str(src/(n+'.c')) for n in ['emount','emount_packets','startup_trace','em_frame','em_owner','em_shutdown']]+['-o',str(out/'probe')]
subprocess.run(cmd,check=True)
cases=[[s] for s in ['focus-copy','session-queues','failed-init','failed-tail','failed-raw','baseline','immutable','first-wins','sequence','active','session','failed-shutdown']]
for cut in range(1,7):
 for i in (1,0x0a,0x0b,0x1b,0x28,0x19,0x34):cases.append(['capture',str(cut),str(i),'11'])
 cases.append(['normal',str(cut),'3','16'])
for n in (9,17,64,255,256):cases.append(['capture','4','52',str(n)])
results=[]
for c in cases:
 r=subprocess.run([str(out/'probe'),*c],capture_output=True,text=True,timeout=10)
 results.append(dict(case=c,exitCode=r.returncode,stdout=r.stdout,stderr=r.stderr))
 assert r.returncode==0 and not r.stderr,results[-1]
(out/'result.json').write_text(json.dumps(dict(inputs=inputs,fixtureSHA256=sha(fixture),results=results),indent=2)+'\n')
print(f'{len(results)} capture/session/transport publication regressions pass')
