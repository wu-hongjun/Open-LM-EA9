#!/usr/bin/env python3
"""AF3.8 exact home/pump/foreground + tracker/UART paths; synthetic MMIO/RX/ticks."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate',type=Path);a=p.parse_args()
base=ROOT/'artifacts/private/readiness38-repeat';out=a.output.resolve()
assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra45-');out.mkdir(exist_ok=False)
mp=ROOT/'firmware/candidates/3.8.0/contax-zeiss-50-f1-4.manifest.json';m=json.loads(mp.read_text())
assert sha(mp)=='be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0'
candidate=a.candidate.resolve() if a.candidate else None;cm=None
if candidate:
 assert candidate.is_relative_to(ROOT/'artifacts/private')
 cm=json.loads((candidate/'manifest.json').read_text());assert cm['loaderVersion']==[3,9,0]
 candidate_manifest_pin=sha(candidate/'manifest.json')
def verify():
 assert len(m['sources'])==49 and json.loads((base/'manifest.json').read_text())==m
 assert sha(base/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']=='8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9'
 for n,d in m['sources'].items():assert sha(base/n)==d,n
 assert sha(base/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
 if candidate:
  assert sha(candidate/'manifest.json')==candidate_manifest_pin
  for n,d in cm['sources'].items():assert sha(candidate/n)==d,n
  assert sha(candidate/'contax-zeiss-50-f1-4.bin')==cm['imageSHA256']
  assert sha(candidate/'tools/hosttest/shim.c')==cm['hostTestShimSHA256']
verify()
def function(s,n):
 lo=s.index(n+'\n{');lo=s.rfind('\n',0,lo)+1;return s[lo:s.index('\n}',lo)+2]+'\n'
cases=['normal','wrap','ramp200','ramp259','ramp260','noise6','noise7','storm','uart-ordinary','drive-deadline','settle-deadline','drive-cross','settle-cross','uart-drive-cross','uart-settle-cross','frozen-budget','shared-budget']
rows=[]
for variant in ['baseline','observation','baseline-missing-snapshot','mutant-last-iteration','mutant-extra-sample','mutant-drive-cutoff','mutant-settle-cutoff','mutant-inhibit','mutant-budget-reset','mutant-still-threshold']:
 work=out/variant;seed=candidate if candidate and variant not in ['baseline','baseline-missing-snapshot'] else base
 shutil.copytree(seed/'src',work/'src');shutil.copytree(seed/'tools',work/'tools')
 if seed==base and variant not in ['baseline','baseline-missing-snapshot']:runpy.run_path(str(HERE/'apply.py'))['apply'](work)
 s=(work/'src/main.c').read_text()
 if variant=='mutant-last-iteration':s=s.replace('home[7] = iteration_ms;', '(void)iteration_ms; home[7] = millis();')
 if variant=='mutant-extra-sample':s=s.replace('home[4] = (uint32_t)still.at;', 'home[4] = (uint32_t)abs_encoder_track();')
 if variant=='mutant-drive-cutoff':s=s.replace('\n\t\t    && (uint32_t)(millis() - t0) < HOME_MS','')
 if variant=='mutant-settle-cutoff':s=s.replace('\n\t\t    && (uint32_t)(millis() - t0) < HOME_SETTLE_MS','')
 if variant=='mutant-inhibit':
  old='\tmotor_inhibit();\n\tg_next_pending = 0;';assert s.count(old)==1;s=s.replace(old,'\tg_next_pending = 0;')
 if variant=='mutant-budget-reset':
  old='\tfailure = ST_HOME_SETTLE;\n';assert s.count(old)==1;s=s.replace(old,old+'\tpolls = 0;\n')
 if variant=='mutant-still-threshold':s=s.replace('#define HOME_STILL_COUNTS   6','#define HOME_STILL_COUNTS   7')
 constants='\n'.join(re.findall(r'^#define HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|POLL_LIMIT|ATTEMPTS)\s+.*$',s,re.M))+'\n#define HOME_GATE_OPEN() 1\n'
 home=constants+s[s.index('enum home_state {'):s.index('#define HOME_ATTEMPTS')]
 for n in ['static void home_cutoff(void)','static void motion_shutdown_inhibit(void)','static uint8_t home_command(void)','static uint8_t home_cancel_requested(void)']:home+=function(s,n)
 home+=s[s.index('struct home_still {'):s.index('\n};',s.index('struct home_still {'))+3]+'\n'
 for n in ['static void home_still_init(struct home_still *st)','static uint8_t home_still_for(struct home_still *st, uint32_t ms)','static void motor_home(void)','static void home_service(void)']:home+=function(s,n)
 (work/'home.inc').write_text(home)
 (work/'worker.inc').write_text(function(s,'static void focus_answer_queries(void)').replace('if (tag == EM_REC_Q_POS2D)','compute_hook();\n        if (tag == EM_REC_Q_POS2D)'))
 (work/'pump.inc').write_text(function(s,'static void pump(int32_t pos)').replace('\n}', '\n\tschedule_tick();\n}'))
 top=s[s.index('\tfor (;;) {')+len('\tfor (;;) {'):s.index('\t\t/* Trace stays in RAM')]
 footer=s[s.index('\t\t/* Home once, then serve'):s.rindex('\n\t}\n}')]
 (work/'foreground.inc').write_text('static void foreground(void)\n{\nstatic unsigned step;\n'+top+footer+'\n}\n')
 tracker=(base/'src/abs_encoder.c').read_text()
 (work/'tracker.inc').write_text(function(tracker,'int32_t abs_encoder_track(void)')+function(tracker,'void abs_encoder_track_reset(void)').replace('g_track      = 0;','resets++;\n\tg_track      = 0;'))
 uart=function((base/'src/em_uart.c').read_text(),'uint8_t em_uart_send(const uint8_t *buf, uint16_t len)').replace('em_uart_send(', 'production_uart_send(').replace('EMSERCOM->USART.INTFLAG.bit.DRE','uart_ready(1)').replace('EMSERCOM->USART.INTFLAG.bit.TXC','uart_ready(2)')
 (work/'uart.inc').write_text(uart)
 em=work/'src/emount.c';em.write_text(em.read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n')
 trace=work/'src/startup_trace.c';trace.write_text(trace.read_text()+'\nunsigned host_fault(void){return s.fault;}\n')
 trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(work/'trace.c').write_text(trace)
 shim=(work/'tools/hosttest/shim.c').read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(old)==1
 shim=shim.replace(old,old+'\n    extern void uart_begin(const uint8_t *);extern uint8_t production_uart_send(const uint8_t *,uint16_t);uart_begin(buf);if(!production_uart_send(buf,len))return 0;\n    extern void send_hook(const uint8_t *);send_hook(buf);');(work/'shim.c').write_text(shim)
 exe=work/'probe';cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(work/'src'),HERE/'test_home.c',work/'shim.c',work/'trace.c',*[work/'src'/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred','motion_trace']],'-o',exe]
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
 selected=cases if variant in ['baseline','observation'] else ['uart-drive-cross'] if variant=='mutant-drive-cutoff' else ['uart-settle-cross'] if variant=='mutant-settle-cutoff' else ['shared-budget'] if variant=='mutant-budget-reset' else ['noise7'] if variant=='mutant-still-threshold' else ['ramp260'] if variant=='baseline-missing-snapshot' else ['uart-drive-cross'] if variant=='mutant-last-iteration' else ['drive-deadline']
 for case in selected:
  r=subprocess.run([str(exe),case,str(int(variant!='baseline'))],capture_output=True,text=True,timeout=30);expected=variant in ['baseline','observation','mutant-extra-sample']
  assert (r.returncode==0)==expected,(variant,case,r.stdout,r.stderr)
  if not expected:
   predicate='(home[0]&255u)==0x39u' if variant=='baseline-missing-snapshot' else 'home[7]==start_time' if variant=='mutant-last-iteration' else 'home[6]==samples' if variant=='mutant-budget-reset' else '!g_homed && g_home_state==HOME_FAILED'
   assert 'Assertion' in r.stderr and predicate in r.stderr,(variant,case,r.stderr)
  rows.append(dict(variant=variant,case=case,expectedPass=expected,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:800]))
# Exact baseline/observation workload outcomes and sensor counts must match.
for case in cases:
 prior=next(r for r in rows if r['variant']=='baseline' and r['case']==case)
 observed=next(r for r in rows if r['variant']=='observation' and r['case']==case)
 a=next(l for l in prior['stdout'].splitlines() if l.startswith('home mode='))
 b=next(l for l in observed['stdout'].splitlines() if l.startswith('home mode='))
 if candidate:
  assert re.sub(r' adc=\d+', '',a)==re.sub(r' adc=\d+', '',b),(case,a,b)
  assert int(re.search(r' adc=(\d+)',b).group(1))==0
 else:assert a==b,(case,a,b)
extra=next(r for r in rows if r['variant']=='mutant-extra-sample')
a=next(l for l in rows[cases.index('drive-deadline')]['stdout'].splitlines() if l.startswith('home mode='))
b=next(l for l in extra['stdout'].splitlines() if l.startswith('home mode='))
assert a!=b and int(re.search(r'reads=(\d+)',b).group(1))==int(re.search(r'reads=(\d+)',a).group(1))+1
extra['expectedPass']=False;extra['negativeControl']='Sensor-read parity rejects the added read despite successful function assertions'
verify()
upstream={}
for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
 digest,name=line.split(maxsplit=1)
 if name.startswith('upstream/weiziqian/E-mount-impl-on-Techart-EA9/') and name.endswith(('/src/main.c','/docs/servo.md')):
  assert sha(ROOT/'references'/name)==digest;upstream[name]=digest
report=dict(status='offline-home-snapshot-verified-no-causal-drive-fix-established',baseManifestSHA256=sha(mp),sourcePins=m['sources'],candidateManifestSHA256=sha(candidate/'manifest.json') if candidate else None,candidateImageSHA256=cm['imageSHA256'] if cm else None,candidateSourcePins=cm['sources'] if cm else None,sourcePinsVerifiedBeforeAndAfter=49,upstreamPins=upstream,results=rows,hardwareReportsSent=0,cameraQualified=False,inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.c']})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(results=len(rows),passed=sum(r['expectedPass'] for r in rows),negativeControls=sum(not r['expectedPass'] for r in rows)),indent=2))
