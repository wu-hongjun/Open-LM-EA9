#!/usr/bin/env python3
"""Execute production capture instrumentation and compare complete synthetic bytes."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
from apply import apply,BASE_SHA
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];L34=HERE.parent/'34-capture-tracing'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,**kwargs):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=60,**kwargs)
 assert r.returncode==0,(args,r.returncode,r.stdout,r.stderr)
 return r.stdout
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.output.resolve();base=ROOT/'artifacts/private/handoff36-repeat'
assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
shim=(base/'tools/hosttest/shim.c').read_text().replace('uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{','void host_probe_send(const uint8_t *,uint16_t);\nextern int host_tx_fail;\nuint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{\n if(host_tx_fail)return 0;\n host_probe_send(buf,len);')
(out/'shim.c').write_text(shim)
reference=out/'reference';shutil.copytree(source/'src',reference/'src')
source_is_compact=sha(source/'src/emount.c')!=BASE_SHA
if source_is_compact:
 (reference/'src/emount.c').write_bytes((base/'src/emount.c').read_bytes())
 runpy.run_path(str(L34/'apply.py'))['apply'](reference/'src')
assert sha(reference/'src/emount.c')==BASE_SHA
harness=(L34/'test_capture.c').read_text().replace('#include "startup_trace.h"','#include "startup_trace.h"\n#undef st_note')
harness=harness.replace('uint32_t session; };','uint32_t session,ms; };').replace('(void)ms; if (!enabled)','if (!enabled)').replace('(uint32_t)lo|((uint32_t)hi<<16)};','(uint32_t)lo|((uint32_t)hi<<16),ms};')
needle='void st_motion_completion(uint8_t state,uint16_t event) {'
wrappers='''void st_summary(uint8_t kind,uint8_t id,uint32_t ms) { st_note(kind,id,0,0,0,0,ms); }
void st_record(uint32_t ms,uint32_t identity,uint32_t payload) { st_note(identity,identity>>8,identity>>16,identity>>24,payload,payload>>16,ms); }
'''
assert harness.count(needle)==1;harness=harness.replace(needle,wrappers+needle)
needle='    return 0;\n}'
extra='''    for (int i=0;i<sent_n;i++) { printf("WIRE %u %d ",sent_len[i],sent_cs_asserted[i]);for(unsigned j=0;j<sent_len[i];j++)printf("%02x",sent[i][j]);puts(""); }
    for (unsigned i=0;i<log_n;i++) { struct event *e=&log_events[i];printf("TRACE %u %u %u %u %08x %08x\\n",e->kind,e->id,e->flags,e->seq,e->session,e->ms); }
    for (unsigned i=0;i<completion_n;i++) printf("COMPLETION %u %u\\n",completion_state[i],completion_event[i]);
'''
assert harness.count(needle)==1;harness=harness.replace(needle,extra+needle)
packet_reset_init='void ea9_packets_init(void);' in (source/'src/emount_packets.h').read_text()
if packet_reset_init:
 assert (source/'src/startup_samd21.c').read_text().count('ea9_packets_init();')==1
 harness=harness.replace('#include "emount.h"','#include "emount.h"\n#include "emount_packets.h"')
 harness=harness.replace('uint8_t p[32];em_init();','uint8_t p[32];ea9_packets_init();em_init();')
(out/'test.c').write_text(harness)
cases=['ordinary','raw','session-irq','shutdown-irq','pending','session-high','failed-tx','shutdown','queue','phase'];outputs={};results={}
for variant in ['before','compact','identity-mutant','live-return-mutant']:
 work=out/variant;shutil.copytree(reference/'src',work/'src');src=work/'src'
 if variant!='before':apply(src)
 if variant=='compact' and source_is_compact:assert sha(src/'emount.c')==sha(source/'src/emount.c'),'final candidate differs from tested applicator'
 q=src/'emount.c';production=q.read_text()
 if variant=='identity-mutant':production=production.replace('((uint32_t)(uint8_t)identity << 24)','((uint32_t)(uint8_t)identity << 16)')
 if variant=='live-return-mutant':production=production.replace('em_trace(ST_TX_RETURN, trace_identity, trace_flags, trace_session);','em_trace(ST_TX_RETURN, trace_identity, trace_flags, g_session_generation);')
 q.write_text(production+'\nvoid test_set_session(uint32_t value){g_session_generation=value;}\n')
 flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(base/'tools/hosttest')]
 command([*flags,out/'test.c',out/'shim.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown']],'-o',work/'probe'])
 q.write_text(production)
 outputs[variant]={};results[variant]={}
 for case in cases if variant in ('before','compact') else ['ordinary'] if variant=='identity-mutant' else ['session-irq']:
  r=subprocess.run([str(work/'probe'),case,'1','1'],capture_output=True,text=True,timeout=15)
  assert r.returncode==(0 if variant in ('before','compact') else 1),(variant,case,r.returncode,r.stderr)
  assert 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr
  outputs[variant][case]=r.stdout
  results[variant][case]={'exit':r.returncode,'syntheticOutputSHA256':hashlib.sha256(r.stdout.encode()).hexdigest(),'assertion':r.stderr.strip()}
  (work/(case+'.txt')).write_text(r.stdout)
assert outputs['before']==outputs['compact']
report={'status':'offline-proposal','sourceIsCompact':source_is_compact,'hostCallsProductionPacketResetInitializer':packet_reset_init,'sourceHashes':{str(p.relative_to(ROOT)):sha(p) for p in [source/'src/emount.c',source/'src/startup_trace.c',source/'src/startup_trace.h',L34/'test_capture.c',HERE/'apply.py',HERE/'run.py']},'cases':results,'completeWireTraceAndCompletionOutputEqual':True,'hardwareAccess':False,'hardwareTimingMeasured':False}
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':len(cases),'byteParity':True,'failingControls':2},indent=2))
