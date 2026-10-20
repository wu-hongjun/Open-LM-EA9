#!/usr/bin/env python3
"""Pinned AF3.8 home-failure downstream protocol replay; synthetic boundaries."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
if not __debug__:raise RuntimeError('Assertions required')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
SHA='8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9'
MANIFEST='be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def function(s,name):
 start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1;end=s.index('\n}',start)+2
 return s[start:end]+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--candidate',type=Path);a=p.parse_args()
 base=ROOT/'artifacts/private/readiness38-repeat';out=a.output.resolve()
 assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra46-')
 m=json.loads((base/'manifest.json').read_text())
 def verify():
  assert sha(base/'manifest.json')==MANIFEST
  assert sha(base/'contax-zeiss-50-f1-4.bin')==SHA
  for n,d in m['sources'].items():assert sha(base/n)==d,n
  assert sha(base/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
 verify();out.mkdir(exist_ok=False);results={};variant_source_pins={}
 candidate=a.candidate.resolve() if a.candidate else None
 cm=json.loads((candidate/'manifest.json').read_text()) if candidate else None
 candidate_manifest_sha=sha(candidate/'manifest.json') if candidate else None
 def verify_candidate():
  if candidate:
   assert candidate.is_relative_to(ROOT/'artifacts/private')
   assert sha(candidate/'manifest.json')==candidate_manifest_sha
   assert sha(candidate/'contax-zeiss-50-f1-4.bin')==cm['imageSHA256']
   for n,d in cm['sources'].items():assert sha(candidate/n)==d,n
   assert sha(candidate/'tools/hosttest/shim.c')==cm['hostTestShimSHA256']
 verify_candidate()
 cases=['no-motion','moves-inhibited','raw-readiness','session-cut','shutdown-cut','failed-stop-retry']
 for variant in ['frozen','proposal','mutant-query-inhibit','mutant-fake-completion','mutant-raw-rearm','mutant-no-count','mutant-count-wrap','mutant-no-tag','mutant-no-inhibit']:
  work=out/variant;source=candidate if candidate and variant!='frozen' else base
  shutil.copytree(source/'src',work/'src');shutil.copytree(source/'tools',work/'tools')
  if variant!='frozen' and not candidate:
   runpy.run_path(str(HERE.parent/'45-home-drive/apply.py'))['apply'](work)
   assert sha(work/'src/main.c')=='484756cdd760a9b7317cae6b7dda632abd03793df889557248e8e329e6d31ebc'
   runpy.run_path(str(HERE/'apply.py'))['apply'](work)
  s=(work/'src/main.c').read_text()
  if variant=='mutant-query-inhibit':
   old='if (!em_handshake_done || g_aborted || em_shutdown_requested()) {';assert s.count(old)==1
   s=s.replace(old,'if (!em_handshake_done || g_aborted || em_shutdown_requested() || motor_is_inhibited()) {')
  if variant=='mutant-fake-completion':
   old='    g_next_pending = 1;\n    return 1;';assert s.count(old)==1
   s=s.replace(old,'    g_next_pending = 1;\n    em_post_event(EM_REC_MOVE, 0);\n    return 1;')
  if variant=='mutant-no-count':
   old='        ++home[3];';assert s.count(old)==1;s=s.replace(old,'        home[3] = home[3];')
  if variant=='mutant-count-wrap':
   old=' && home[3] != 255';assert s.count(old)==1;s=s.replace(old,'')
  if variant=='mutant-no-tag':
   old='home[0] == 0x39 && ';assert s.count(old)==1;s=s.replace(old,'')
  if variant=='mutant-no-inhibit':
   old='motor_is_inhibited() && home[0]';assert s.count(old)==1;s=s.replace(old,'home[0]')
  (work/'src/main.c').write_text(s)
  variant_source_pins[variant]={n:sha(work/n) for n in m['sources']}
  constants='\n'.join(re.findall(r'^#define HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|POLL_LIMIT|ATTEMPTS)\s+.*$',s,re.M))+'\n#define HOME_GATE_OPEN() 1\n'
  home=constants+s[s.index('enum home_state {'):s.index('#define HOME_ATTEMPTS')]
  for n in ['static void home_cutoff(void)','static void motion_shutdown_inhibit(void)','static uint8_t home_command(void)','static uint8_t home_cancel_requested(void)']:home+=function(s,n)
  home+=s[s.index('struct home_still {'):s.index('\n};',s.index('struct home_still {'))+3]+'\n'
  for n in ['static void home_still_init(struct home_still *st)','static uint8_t home_still_for(struct home_still *st, uint32_t ms)','static void motor_home(void)','static void home_service(void)']:home+=function(s,n)
  (work/'home.inc').write_text(home)
  (work/'worker.inc').write_text(function(s,'static void focus_answer_queries(void)').replace('if (tag == EM_REC_Q_POS2D)','compute_hook();\n        if (tag == EM_REC_Q_POS2D)'))
  (work/'pump.inc').write_text(function(s,'static void pump(int32_t pos)'))
  (work/'focus_entry.inc').write_text(''.join(function(s,n) for n in ['static uint8_t focus_invalid(void)','static void focus_event(uint8_t code, uint8_t param)','static void focus_exec(const struct em_focus_cmd *c, uint32_t session)']))
  top=s[s.index('\tfor (;;) {')+len('\tfor (;;) {'):s.index('\t\t/* Trace stays in RAM')]
  footer=s[s.index('\t\t/* Home once, then serve'):s.rindex('\n\t}\n}')]
  (work/'foreground.inc').write_text('static void foreground(void)\n{\nstatic unsigned step;\n'+top+footer+'\n}\n')
  em=work/'src/emount.c';text=em.read_text()
  if variant=='mutant-raw-rearm':
   old='g_owner.status_enabled = 0;\n                    g_status_due = 0;';assert text.count(old)==1;text=text.replace(old,'g_owner.status_enabled = 1;\n                    g_status_due = 0;')
  em.write_text(text+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\nunsigned host_status(void){return g_owner.status_enabled;}\n')
  trace=work/'src/startup_trace.c';trace.write_text(trace.read_text()+'\nunsigned host_fault(void){return s.fault;}\n')
  tracehost=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(work/'trace.c').write_text(tracehost)
  shim=(work/'tools/hosttest/shim.c').read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(old)==1
  shim=shim.replace('uint32_t millis(void) { return host_millis; }','uint32_t millis(void) { return host_millis++; }')
  (work/'shim.c').write_text(shim.replace(old,old+'\n    extern void send_hook(const uint8_t *);send_hook(buf);'))
  flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(work/'src')]
  if variant!='frozen':flags+=['-DEXPECT_HOME_TAIL=1']
  cmd=[*flags,HERE/'test_shutter.c',work/'shim.c',work/'trace.c',*[work/'src'/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred','motion_trace']],'-o',work/'probe']
  r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr
  negative={'mutant-query-inhibit':('no-motion','wire_queries==1'),'mutant-fake-completion':('moves-inhibited','!wire_moves'),'mutant-raw-rearm':('raw-readiness','!host_status()'),'mutant-no-count':('moves-inhibited','p[115]==expected_observed'),'mutant-count-wrap':('saturating','p[115]==expected_observed'),'mutant-no-tag':('uninitialized-tail','tail[3]==3'),'mutant-no-inhibit':('no-inhibit-tail','st_motion_data()[115]==3')}
  selected=cases+(['observe-command'] if variant=='frozen' else ['observe-command','saturating','uninitialized-tail','no-inhibit-tail']) if variant in ('frozen','proposal') else [negative[variant][0]]
  results[variant]=[]
  for case in selected:
   r=subprocess.run([str(work/'probe'),case],capture_output=True,text=True,timeout=10)
   passing=variant=='proposal' or variant=='frozen' and case!='observe-command'
   assert (r.returncode==0)==passing,(variant,case,r.stdout,r.stderr)
   if not passing:
    predicate='st_motion_data()[115]==3' if variant=='frozen' else negative[variant][1]
    assert 'Assertion' in r.stderr and predicate in r.stderr,(variant,case,r.stderr)
   results[variant].append({'case':case,'expectedPass':passing,'exitCode':r.returncode,'stdout':r.stdout.strip(),'stderr':r.stderr.strip()})
 verify();verify_candidate()
 upstream={}
 for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
  digest,name=line.split(maxsplit=1)
  if name=='upstream/weiziqian/E-mount-impl-on-Techart-EA9/src/main.c':
   assert sha(ROOT/'references'/name)==digest;upstream[name]=digest
 assert len(upstream)==1
 result={'status':'offline-downstream-replay','baseImageSHA256':SHA,'baseManifestSHA256':MANIFEST,'sourcePins':m['sources'],'sourceDigestsVerified':49,'cases':results,'hardwareAccess':False,'cameraShutterFixEstablished':False,'inputs':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.c')},'lane45ApplySHA256':sha(HERE.parent/'45-home-drive/apply.py'),'candidateManifest':cm,'candidateManifestSHA256':candidate_manifest_sha,'testedProductionSources':variant_source_pins,'upstreamPins':upstream}
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 if not candidate:(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'frozenPassingCases':6,'frozenStopThenMoveRemainsInhibited':True,'proposalPasses':10,'mutantsRejected':7,'frozenMissingDiscriminatorReproduced':True}))
if __name__=='__main__':main()
