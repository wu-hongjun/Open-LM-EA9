#!/usr/bin/env python3
"""AF3.9 exact home/pump/foreground + tracker/UART paths; synthetic MMIO/RX/ticks."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate',type=Path);a=p.parse_args()
base=ROOT/'artifacts/private/homing39-repeat';out=a.output.resolve()
assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra49-');out.mkdir(exist_ok=False)
mp=ROOT/'firmware/candidates/3.9.0/contax-zeiss-50-f1-4.manifest.json';m=json.loads(mp.read_text())
assert sha(mp)=='9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a'
candidate=a.candidate.resolve() if a.candidate else None;cm=None
if candidate:
 assert candidate.is_relative_to(ROOT/'artifacts/private')
 cm=json.loads((candidate/'manifest.json').read_text());assert cm['loaderVersion']==[4,0,0]
 candidate_manifest_pin=sha(candidate/'manifest.json')
def verify():
 assert len(m['sources'])==49 and json.loads((base/'manifest.json').read_text())==m
 assert sha(base/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']=='87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44'
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
cases=['normal','wrap','ramp200','ramp259','ramp260','late280','moving','wrong-way','too-far','release-drift','final-drift','after-drift','late-uart-cross','settle-session','settle-shutdown','settle-stop','stuck','noise6','noise7','storm','uart-ordinary','drive-deadline','settle-deadline','drive-cross','settle-cross','uart-drive-cross','uart-settle-cross','frozen-budget','shared-budget','session','shutdown','stop','corrupt']
rows=[]
for variant in ['baseline','qualification','mutant-polarity','mutant-anchor','mutant-reset','mutant-stale-pwm','mutant-cutoff']:
 work=out/variant;seed=candidate if candidate and variant not in ['baseline','baseline-missing-snapshot'] else base
 shutil.copytree(seed/'src',work/'src');shutil.copytree(seed/'tools',work/'tools')
 if seed==base and variant not in ['baseline','baseline-missing-snapshot']:runpy.run_path(str(HERE/'apply.py'))['apply'](work)
 s=(work/'src/main.c').read_text()
 if variant=='mutant-cutoff':s=s.replace('drive_ms != HOME_MS ||','0 ||')
 if variant=='mutant-polarity':s=s.replace('travel <= HOME_STILL_COUNTS ||','0 ||')
 if variant=='mutant-anchor':s=s.replace('if (released && ((int64_t)after', 'if (0 && released && ((int64_t)after').replace('if (drift > HOME_STILL_COUNTS || drift < -HOME_STILL_COUNTS)','if (0 && (drift > HOME_STILL_COUNTS || drift < -HOME_STILL_COUNTS))').replace('abs_encoder_home_reset(still.at, HOME_STILL_COUNTS)','abs_encoder_home_reset(abs_encoder_track(), HOME_STILL_COUNTS)')
 if variant=='mutant-reset':s=s.replace('if (!abs_encoder_home_reset(still.at, HOME_STILL_COUNTS)) goto failed;','abs_encoder_track_reset();')
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
 tracker=(work/'src/abs_encoder.c').read_text()
 tracker_text=function(tracker,'int32_t abs_encoder_track(void)')+function(tracker,'void abs_encoder_track_reset(void)').replace('g_track      = 0;','resets++;\n\tg_track      = 0;')
 if 'uint8_t abs_encoder_home_reset(' in tracker:tracker_text+=function(tracker,'uint8_t abs_encoder_home_reset(int32_t anchor, uint16_t tolerance)').replace('g_track = 0;','resets++; g_track = 0;')
 (work/'tracker.inc').write_text(tracker_text)
 motor=(work/'src/motor.c').read_text()
 motor_text='static volatile uint8_t g_motor_inhibited;\n'
 for n in ['uint8_t motor_is_inhibited(void)','void motor_emergency_release(void)','void motor_inhibit(void)','static void tcc0_sync_cc(void)','void motor_attach_pins(void)','static void pair_a(uint16_t fwd, uint16_t rev)','static void pair_b(uint16_t fwd, uint16_t rev)','void motor_drive(int16_t duty)','void motor_brake(void)']:
  if n=='uint8_t motor_is_inhibited(void)':part=n+' { return g_motor_inhibited; }\n'
  else:part=function(motor,n)
  if n=='void motor_emergency_release(void)':part=part.replace('{','{\n releases++; if(!cutoff)cutoff=host_millis;',1)
  if n=='void motor_drive(int16_t duty)':part=part.replace('{','{\n if(duty){assert(duty==-800);drives++;}',1)
  if n=='void motor_brake(void)':part=part.replace('{','{\n brakes++;phase_time=host_millis;',1)
  motor_text+=part
 if 'void motor_home_release(' in motor:
  release=function(motor,'void motor_home_release(void)')
  if variant=='mutant-stale-pwm':release=release.replace('pair_a(0, 0);','').replace('pair_b(0, 0);','')
  motor_text+=release
 (work/'motor.inc').write_text(motor_text)


 uart=function((base/'src/em_uart.c').read_text(),'uint8_t em_uart_send(const uint8_t *buf, uint16_t len)').replace('em_uart_send(', 'production_uart_send(').replace('EMSERCOM->USART.INTFLAG.bit.DRE','uart_ready(1)').replace('EMSERCOM->USART.INTFLAG.bit.TXC','uart_ready(2)')
 (work/'uart.inc').write_text(uart)
 em=work/'src/emount.c';em.write_text(em.read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n')
 trace=work/'src/startup_trace.c';trace.write_text(trace.read_text()+'\nunsigned host_fault(void){return s.fault;}\n')
 trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(work/'trace.c').write_text(trace)
 shim=(work/'tools/hosttest/shim.c').read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(old)==1
 shim=shim.replace(old,old+'\n    extern void uart_begin(const uint8_t *);extern uint8_t production_uart_send(const uint8_t *,uint16_t);uart_begin(buf);if(!production_uart_send(buf,len))return 0;\n    extern void send_hook(const uint8_t *);send_hook(buf);');(work/'shim.c').write_text(shim)
 exe=work/'probe';cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(work/'src'),HERE/'test_home.c',work/'shim.c',work/'trace.c',*[work/'src'/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred','motion_trace']],'-o',exe]
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
 for case in (['wrong-way'] if variant=='mutant-polarity' else ['release-drift'] if variant=='mutant-anchor' else ['final-drift'] if variant=='mutant-reset' else ['late280'] if variant=='mutant-stale-pwm' else ['late-uart-cross'] if variant=='mutant-cutoff' else cases):
  r=subprocess.run([str(exe),case,str(int(variant!='baseline'))],capture_output=True,text=True,timeout=30)
  expected=not variant.startswith('mutant-')
  assert (r.returncode==0)==expected,(variant,case,r.stdout,r.stderr)
  if not expected:assert 'Assertion' in r.stderr and ('tcc.CC' in r.stderr if variant=='mutant-stale-pwm' else '!g_homed' in r.stderr),r.stderr
  rows.append(dict(variant=variant,case=case,expectedPass=expected,exitCode=r.returncode,stdout=r.stdout.strip()))
verify()
upstream={}
for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
 digest,name=line.split(maxsplit=1)
 if name.startswith('upstream/weiziqian/E-mount-impl-on-Techart-EA9/') and name.endswith(('/src/main.c','/docs/servo.md')):
  assert sha(ROOT/'references'/name)==digest;upstream[name]=digest
report=dict(status='offline-guarded-reference-qualification-not-camera-qualified',baseManifestSHA256=sha(mp),sourcePins=m['sources'],candidateManifestSHA256=sha(candidate/'manifest.json') if candidate else None,candidateImageSHA256=cm['imageSHA256'] if cm else None,candidateSourcePins=cm['sources'] if cm else None,sourcePinsVerifiedBeforeAndAfter=49,upstreamPins=upstream,results=rows,hardwareReportsSent=0,cameraQualified=False,inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.c']})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(results=len(rows)),indent=2))
