#!/usr/bin/env python3
"""Source-bound composed readiness -> real servo -> protocol acceptance tests."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
extract=runpy.run_path(str(HERE.parent/'46-shutter-readiness/run.py'))['function']
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate',type=Path);p.add_argument('--apply49',action='store_true');a=p.parse_args()
 base=ROOT/'artifacts/private/homing39-repeat';out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra50-');out.mkdir(exist_ok=False)
 def verify(b):
  m=json.loads((b/'manifest.json').read_text());assert sha(b/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
  for n,d in m['sources'].items():assert sha(b/n)==d,n
  assert sha(b/'tools/hosttest/shim.c')==m['hostTestShimSHA256'];return m
 bm=verify(base);assert sha(base/'manifest.json')=='9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a'
 assert bm['imageSHA256']=='87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44'
 source=a.candidate.resolve() if a.candidate else base;cm=verify(source);manifest_pin=sha(source/'manifest.json');results={}
 variants=['frozen','proposal','mutant-pending','mutant-origin','mutant-session','mutant-completion','mutant-raw','mutant-query']
 for variant in variants:
  work=out/variant;b=base if variant=='frozen' else source
  shutil.copytree(b/'src',work/'src');shutil.copytree(b/'tools',work/'tools')
  if a.apply49 and variant!='frozen':runpy.run_path(str(HERE.parent/'49-home-qualification/apply.py'))['apply'](work)
  s=(work/'src/main.c').read_text()
  replacements={'mutant-pending':('g_next_pending = 0;\n\t\t\t\tif (!g_aborted','g_next_pending = 1;\n\t\t\t\tif (!g_aborted'), 'mutant-session':('g_next_session == em_session_generation()','1'), 'mutant-completion':('focus_event(EM_REC_MOVE, 0x00u);','/* mutant omitted completion */'), 'mutant-query':('if (!em_handshake_done || g_aborted || em_shutdown_requested()) {','if (!em_handshake_done || g_aborted || em_shutdown_requested() || motor_is_inhibited()) {')}
  if variant=='mutant-origin':
   old='if (!abs_encoder_home_reset(still.at, HOME_STILL_COUNTS)) goto failed;' if 'abs_encoder_home_reset(still.at' in s else '/* Software reference: stationary feedback alone does not prove infinity. */\n\tabs_encoder_track_reset();'
   assert s.count(old)==1;s=s.replace(old,'/* mutant: omitted origin commit */')
  if variant in replacements:
   old,new=replacements[variant];assert s.count(old)==1,(variant,s.count(old));s=s.replace(old,new)
  if variant=='mutant-session':s=s.replace('focus_exec(&g_next, g_next_session);','focus_exec(&g_next, em_session_generation());')
  pins={n:sha(work/n) for n in cm['sources']};pins['src/main.c']=hashlib.sha256(s.encode()).hexdigest()
  constants='\n'.join(re.findall(r'^#define (?:HOME_\w+|MOVE_DUTY|FOCUS_DEADBAND_COUNTS)\s+[^\\\n]+$',s,re.M))+'\n#undef HOME_GATE_OPEN\n#define HOME_GATE_OPEN() 1\n'
  home=constants+s[s.index('enum home_state {'):s.index('#define HOME_ATTEMPTS')]
  for n in ['static void home_cutoff(void)','static void motion_shutdown_inhibit(void)','static uint8_t home_command(void)','static uint8_t home_cancel_requested(void)']:home+=extract(s,n)
  home+=s[s.index('struct home_still {'):s.index('\n};',s.index('struct home_still {'))+3]+'\n'
  for n in ['static void home_still_init(struct home_still *st)','static uint8_t home_still_for(struct home_still *st, uint32_t ms)','static void motor_home(void)','static void home_service(void)']:home+=extract(s,n)
  (work/'home.inc').write_text(home)
  names=['static void focus_report_at(int32_t counts)','static void focus_report(void)','static void focus_answer_queries(void)','static void pump(int32_t pos)','static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)','static uint8_t focus_invalid(void)','static void focus_event(uint8_t code, uint8_t param)','static uint8_t focus_abort(void)','static uint8_t focus_retarget(int32_t *target)','static uint8_t focus_run(int32_t want, uint16_t target_u,\n                         const struct servo_cfg *cfg)','static void focus_exec(const struct em_focus_cmd *c, uint32_t session)']
  (work/'focus.inc').write_text('\n'.join(extract(s,n) for n in names).replace('static void pump(int32_t pos)\n{','static void pump(int32_t pos)\n{\n host_millis++;'))
  encoder=(work/'src/abs_encoder.c').read_text()
  helper=extract(encoder,'uint8_t abs_encoder_home_reset(int32_t anchor, uint16_t tolerance)').replace('g_track = 0;','position = 0; resets++;') if 'uint8_t abs_encoder_home_reset(' in encoder else ''
  (work/'encoder.inc').write_text(helper)
  stock=s[s.index('static const struct servo_cfg STOCK = {'):s.index('\n};',s.index('static const struct servo_cfg STOCK = {'))+3]
  (work/'stock.inc').write_text(constants+stock)
  top=s[s.index('\tfor (;;) {')+len('\tfor (;;) {'):s.index('\t\t/* Trace stays in RAM')];footer=s[s.index('\t\t/* Home once, then serve'):s.rindex('\n\t}\n}')]
  (work/'foreground.inc').write_text('static void foreground(void){static unsigned step;\n'+top+footer+'\n}\n')
  em=work/'src/emount.c';es=em.read_text()
  if variant=='mutant-raw':es=es.replace('g_owner.status_enabled = 0;\n                    g_status_due = 0;','g_owner.status_enabled = 1;\n                    g_status_due = 0;')
  em.write_text(es+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\nunsigned host_status(void){return g_owner.status_enabled;}\n')
  servo=work/'src/servo.c';ss=servo.read_text();needle='void servo_move_from(';start=ss.index('{',ss.index(needle));ss=ss[:start+1]+'\n extern void servo_start(int32_t,int32_t);servo_start(start,target);\n'+ss[start+1:];servo.write_text(ss)
  trace=work/'src/startup_trace.c';trace.write_text(trace.read_text()+'\nunsigned host_fault(void){return s.fault;}\n')
  tracehost=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(work/'trace.c').write_text(tracehost)
  shim=(work/'tools/hosttest/shim.c').read_text().replace('uint32_t millis(void) { return host_millis; }','uint32_t millis(void) { extern void clock_hook(void);clock_hook(); return host_millis; }')
  shim=shim.replace('uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{','uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{\nextern void send_hook(const uint8_t *);send_hook(buf);');(work/'shim.c').write_text(shim)
  cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all',*[f'-I{x}' for x in [work,work/'tools/hosttest',work/'src']],HERE/'test_composed.c',work/'shim.c',work/'trace.c',*[work/'src'/(n+'.c') for n in ['servo','emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred','motion_trace']],'-o',work/'probe']
  r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr
  controls={'mutant-pending':('early','!g_next_pending'),'mutant-origin':('early','resets==1'),'mutant-session':('stale-session','servo_calls==0'),'mutant-completion':('early','wire_moves==1'),'mutant-raw':('early','!host_status()'),'mutant-query':('failed','wire_queries==1')}
  cases=['early','late','failed','session','stale-session','stop','shutdown'] if variant in ('frozen','proposal') else [controls[variant][0]];results[variant]={'sourcePins':pins,'cases':[]}
  for case in cases:
   r=subprocess.run([str(work/'probe'),case],capture_output=True,text=True,timeout=10)
   expected=variant in ('frozen','proposal') and not(case=='late' and (variant=='frozen' or not(a.candidate or a.apply49)))
   assert (r.returncode==0)==expected,(variant,case,r.stdout,r.stderr)
   if not expected:assert 'Assertion' in r.stderr and (controls[variant][1] if variant in controls else 'g_homed') in r.stderr,(variant,r.stderr)
   results[variant]['cases'].append({'case':case,'expectedPass':expected,'exitCode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()})
 verify(base);verify(source);assert sha(source/'manifest.json')==manifest_pin
 result={'status':'offline-composed-replay','baselineManifestSHA256':sha(base/'manifest.json'),'candidateManifestSHA256':sha(source/'manifest.json'),'candidateImageSHA256':cm['imageSHA256'],'hardwareAccess':False,'results':results,'inputs':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.c')},'overlay49':a.apply49,'overlay49SHA256':sha(HERE.parent/'49-home-qualification/apply.py') if a.apply49 else None}
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':str(out),'variants':len(results)}))
if __name__=='__main__':main()
