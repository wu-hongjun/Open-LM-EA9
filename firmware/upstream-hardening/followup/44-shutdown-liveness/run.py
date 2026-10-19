#!/usr/bin/env python3
"""Offline source-bound production capture/shutdown liveness audit; no patch."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,expected=0):
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=45)
 if expected==0:assert r.returncode==0,(cmd,r.stdout,r.stderr)
 else:assert r.returncode!=0 and 'Assertion failed' in r.stderr,(cmd,r.stdout,r.stderr)
 return dict(exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip())
def function(s,name):
 lo=s.index(name+'\n{');lo=s.rfind('\n',0,lo)+1;return s[lo:s.index('\n}',lo)+2]+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'artifacts/private/targeted37-repeat');p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest',type=Path,help='Independent manifest pin for a final candidate source');a=p.parse_args()
 src=a.source.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra44-');out.mkdir(exist_ok=False)
 baseline=ROOT/'firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json';base=json.loads(baseline.read_text());base_source=ROOT/'artifacts/private/targeted37-repeat'
 assert json.loads((base_source/'manifest.json').read_text())==base
 for n,h in base['sources'].items():assert sha(base_source/n)==h,n
 manifest=a.manifest.resolve() if a.manifest else baseline
 assert manifest!=(src/'manifest.json').resolve(),'independent manifest required'
 m=json.loads(manifest.read_text());assert json.loads((src/'manifest.json').read_text())==m
 assert m['loaderVersion'] in [[3,7,0],[3,8,0]] and m['cameraQualified'] is False
 assert sha(src/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
 for n,h in m['sources'].items():assert sha(src/n)==h,n
 # The production boundary contracts remain applicable; candidate main is extracted anew.
 for name in ['emount.c','em_uart.c','delay.c','em_frame.c','em_owner.c','em_shutdown.c']:
  assert m['sources']['src/'+name]==base['sources']['src/'+name],name
 shutil.copytree(src/'src',out/'src');shutil.copytree(src/'tools/hosttest',out/'hosttest')
 em=out/'src/emount.c';original=em.read_text();em.write_text(original+'\nunsigned probe_status(void){return g_owner.status_enabled;}\nunsigned probe_retry(void){return g_retry!=0;}\nunsigned probe_pending(void){return g_owner.pending;}\n')
 shim=out/'hosttest/shim.c';s=shim.read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert s.count(old)==1;shim.write_text(s.replace(old,old+'\n extern void send_hook(const uint8_t *);send_hook(buf);'))
 trace_source=ROOT/'firmware/upstream-diagnostic/tests/trace_host.c';s=trace_source.read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','').replace('memory+a-ST_FLASH_BASE','memory+(a-ST_FLASH_BASE)');(out/'trace.c').write_text(s)
 flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(out/'hosttest'),'-I'+str(out/'src')]
 modules=['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','motion_trace']
 cmd=[*flags,HERE/'test_capture.c',shim,out/'trace.c',*[out/'src'/(n+'.c') for n in modules],'-o',out/'probe'];run(cmd)
 cases=[dict(case=i,**run([out/'probe',i])) for i in range(4)]
 controls=[]
 for name,old,new,case in [('raw-status-disable','g_owner.status_enabled = 0;\n                    g_status_due = 0;','g_owner.status_enabled = 1;\n                    g_status_due = 0;',0),('raw-retry-clear','if (sent || session != g_session_generation) g_retry = 0;','if (session != g_session_generation) g_retry = 0;',0)]:
  body=em.read_text();assert old in body;em.write_text(body.replace(old,new,1));run(cmd);controls.append(dict(name=name,**run([out/'probe',case],expected=1)));em.write_text(body)
 # The production terminal function is tested with explicitly synthetic delays/pins.
 main=(src/'src/main.c').read_text();lo=main.index('static void powerdown_signal(void)');hi=main.index('\n}\n',lo)+3
 fixture=HERE.parent/'35-targeted-trace/test_tail.inc';tail=fixture.read_text().replace('/* EXTRACTED_PRODUCTION_FUNCTION */',main[lo:hi]);(out/'tail.c').write_text(tail)
 run([*flags,out/'tail.c','-o',out/'tail']);terminal=run([out/'tail'])
 delay=(src/'src/delay.c').read_text();uart=(src/'src/em_uart.c').read_text()
 waits=(HERE/'test_waits.inc').read_text().replace('/* EXTRACTED_CLOCK_FUNCTIONS */',function(delay,'void SysTick_Handler(void)')+function(delay,'uint32_t millis(void)')).replace('/* EXTRACTED_DELAY_FUNCTION */',function(delay,'void delay_ms(uint32_t ms)').replace('g_millis','probe_tick()')).replace('/* EXTRACTED_UART_FUNCTIONS */',''.join(function(uart,n) for n in ['static void em_uart_sync(void)','void em_uart_disable(void)','uint8_t em_uart_send(const uint8_t *buf, uint16_t len)']))
 (out/'waits.c').write_text(waits);run([*flags,out/'waits.c','-o',out/'waits']);wait_cases=[dict(case=i,**run([out/'waits',i])) for i in range(7)]
 upstream={};prefix='upstream/weiziqian/E-mount-impl-on-Techart-EA9/'
 for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
  digest,name=line.split(maxsplit=1)
  if name in [prefix+'src/'+n for n in ['main.c','emount.c','em_uart.c','delay.c']]:
   assert sha(ROOT/'references'/name)==digest;upstream[name]=digest
 assert len(upstream)==4
 result=dict(baselineManifestSHA256=sha(baseline),testedImageSHA256=m['imageSHA256'],testedVersion=m['loaderVersion'],waitCases=wait_cases,upstreamPins=upstream,status='offline-production-capture-and-terminal-audit-pass-no-runtime-patch',manifestSHA256=sha(manifest),sourceHashes=m['sources'],sourcePinCount=len(m['sources']),captureCases=cases,negativeControls=controls,terminalCases=6,terminalResult=terminal,externalInputs={str(p.relative_to(ROOT)):sha(p) for p in [trace_source,fixture,src/'tools/hosttest/shim.c']},inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.c','.py','.inc']},hardwareOperations=0,cameraQualified=False,productionCodeBytesAdded=0)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=str(out/'result.json'),captureCases=len(cases),terminalCases=6,controls=len(controls))))
if __name__=='__main__':
 if not __debug__:raise SystemExit('Run without Python optimization; source pins and checks are required')
 main()
