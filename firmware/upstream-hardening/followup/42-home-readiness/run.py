#!/usr/bin/env python3
"""Exact-source home + pump + foreground bodies, real protocol, synthetic hardware."""
import argparse, hashlib, json, re, runpy, shutil, subprocess, difflib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate',type=Path);a=p.parse_args()
base=ROOT/'artifacts/private/targeted37-repeat';out=a.output.resolve()
assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra42-')
out.mkdir(exist_ok=False)
manifest_path=ROOT/'firmware/candidates/3.7.0/contax-zeiss-50-f1-4.manifest.json'
m=json.loads(manifest_path.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
candidate=a.candidate.resolve() if a.candidate else None
cm=None
base_manifest_pin=sha(manifest_path)
candidate_manifest_pin=sha(candidate/'manifest.json') if candidate else None
if candidate:
 assert candidate.is_relative_to(ROOT/'artifacts/private')
 cm=json.loads((candidate/'manifest.json').read_text())
 assert cm['loaderVersion']==[3,8,0], 'Expected completed AF3.8 private build'
 assert 'ST_HOME_DRIVE=17' in (candidate/'src/startup_trace.h').read_text(), 'Expected integrated phase labels'
def verify():
 assert sha(manifest_path)==base_manifest_pin
 assert len(m['sources'])==49
 for n,d in m['sources'].items():assert sha(base/n)==d,n
 assert sha(base/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
 if candidate:
  assert sha(candidate/'manifest.json')==candidate_manifest_pin
  assert sha(candidate/'contax-zeiss-50-f1-4.bin')==cm['imageSHA256']
  for n,d in cm['sources'].items():assert sha(candidate/n)==d,n
  assert sha(candidate/'tools/hosttest/shim.c')==cm['hostTestShimSHA256']
verify()
def function(s,name):
 start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1;end=s.index('\n}',start)+2
 return s[start:end]+'\n'
cases=['normal','wrap','drive-deadline','settle-deadline','drive-cross','settle-cross','frozen-budget','shared-budget']
rows=[];sizes=[]
for variant in ['baseline','proposal','phase','mutant-phase-label','worker-gate-only','foreground-gate-only','mutant-drive-cutoff','mutant-settle-cutoff','mutant-inhibit','mutant-budget-reset']:
 work=out/variant;seed=candidate if candidate and variant!='baseline' else base
 build_manifest=cm if seed==candidate else m
 shutil.copytree(seed/'src',work/'src');shutil.copytree(seed/'tools',work/'tools')
 if seed==base:
  if variant!='baseline':runpy.run_path(str(HERE/'apply.py'))['apply'](work)
  if variant in ['phase','mutant-phase-label']:runpy.run_path(str(HERE/'apply_phase.py'))['apply_phase_labels'](work)
 main=work/'src/main.c';s=main.read_text()
 if variant=='mutant-phase-label':s=s.replace('uint8_t failure = ST_HOME_DRIVE;', 'uint8_t failure = ST_HOME_SETTLE;')
 if variant=='worker-gate-only':
  s=s.replace('\t\tfocus_answer_queries();\n\t\tem_poll();','\t\tem_poll();').replace('\t\t\tfocus_report();','\t\t\tfocus_report();\n\t\t\tfocus_answer_queries();')
 if variant=='foreground-gate-only':
  old=(base/'src/main.c').read_text();s=s.replace(function(s,'static void focus_answer_queries(void)'),function(old,'static void focus_answer_queries(void)'))
 if variant=='mutant-budget-reset':
  old='\tt0 = millis();\n\thome_still_init(&still);\n\twhile ((uint32_t)(millis() - t0) < HOME_SETTLE_MS)';assert s.count(old)==1;s=s.replace(old,'\tpolls = 0;\n'+old)
 if variant=='mutant-drive-cutoff':s=s.replace('\n\t\t    && (uint32_t)(millis() - t0) < HOME_MS','')
 if variant=='mutant-settle-cutoff':s=s.replace('\n\t\t    && (uint32_t)(millis() - t0) < HOME_SETTLE_MS','')
 if variant=='mutant-inhibit':
  old='\tmotor_inhibit();\n\tg_next_pending = 0;';assert s.count(old)==1;s=s.replace(old,'\tg_next_pending = 0;')
 main.write_text(s)
 # Build ARM production sources BEFORE introducing host-only observations.
 if variant in ['baseline','proposal','phase']:
  deps=ROOT/'tools/firmware-deps';arm=str(deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
  inc=['-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
  objects=[]
  for unit in build_manifest['units']:
   obj=work/(unit+'.o');objects.append(str(obj))
   subprocess.run([arm+'gcc',*build_manifest['flags'],*build_manifest['unitFlags'].get(unit,[]),*inc,'-c','src/'+unit+'.c','-o',str(obj)],cwd=work,check=True,capture_output=True)
  elf=work/'hardened.elf'
  subprocess.run([arm+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld','-Wl,--gc-sections,-Map='+str(work/'hardened.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],cwd=work,check=True,capture_output=True)
  sym={}
  for line in subprocess.check_output([arm+'nm',str(elf)],text=True).splitlines():
   f=line.split()
   if len(f)==3:sym[f[2]]=int(f[0],16)
  end=sym['_etext']+sym['_erelocate']-sym['_srelocate']
  subprocess.run([arm+'objcopy','-O','binary','--gap-fill=0xff',str(elf),str(work/'raw.bin')],check=True,capture_output=True)
  raw=(work/'raw.bin').read_bytes();assert len(raw)<=0x4c00
  rebuilt_hash=hashlib.sha256(raw+b'\xff'*(0x5000-len(raw))).hexdigest()
  if variant=='baseline':assert rebuilt_hash==m['imageSHA256']
  elif candidate:assert rebuilt_hash==cm['imageSHA256']
  sizes.append(dict(variant=variant,imageSHA256=rebuilt_hash,codeAndDataEnd=end,margin=0x9c00-end,staticRAMBytes=sym['_ezero']-0x20000000))
  assert 0x9c00-end>=256
  if variant=='baseline':assert end==m['codeAndDataEnd']
  elif candidate:assert end==cm['codeAndDataEnd']
  if variant!='baseline':(work/'from37.patch').write_text(''.join(difflib.unified_diff((base/'src/main.c').read_text().splitlines(True),s.splitlines(True),fromfile='base/main.c',tofile='proposal/main.c')))
 assert '#define HOME_DELAY_MS       0' in s and '#define HOME_GATE_OPEN()    1' in s
 constants='\n'.join(re.findall(r'^#define HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|POLL_LIMIT|ATTEMPTS)\s+.*$',s,re.M))+'\n#define HOME_GATE_OPEN() 1\n'
 home=constants+s[s.index('enum home_state {'):s.index('#define HOME_ATTEMPTS')]
 for n in ['static void home_cutoff(void)','static void motion_shutdown_inhibit(void)','static uint8_t home_command(void)','static uint8_t home_cancel_requested(void)']:home+=function(s,n)
 home+=s[s.index('struct home_still {'):s.index('\n};',s.index('struct home_still {'))+3]+'\n'
 for n in ['static void home_still_init(struct home_still *st)','static uint8_t home_still_for(struct home_still *st, uint32_t ms)','static void motor_home(void)','static void home_service(void)']:home+=function(s,n)
 (work/'home.inc').write_text(home)
 (work/'worker.inc').write_text(function(s,'static void focus_answer_queries(void)').replace('if (tag == EM_REC_Q_POS2D)','compute_hook();\n        if (tag == EM_REC_Q_POS2D)'))
 (work/'pump.inc').write_text(function(s,'static void pump(int32_t pos)'))
 top=s[s.index('\tfor (;;) {')+len('\tfor (;;) {'):s.index('\t\t/* Trace stays in RAM')]
 footer=s[s.index('\t\t/* Home once, then serve'):s.rindex('\n\t}\n}')]
 (work/'foreground.inc').write_text('static void foreground(void)\n{\nstatic unsigned step;\n'+top+footer+'\n}\n')
 em=work/'src/emount.c';em.write_text(em.read_text()+'\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\n')
 trace_source=work/'src/startup_trace.c';trace_source.write_text(trace_source.read_text()+'\nunsigned host_fault(void){return s.fault;}\n')
 trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','');(work/'trace.c').write_text(trace)
 shim=(work/'tools/hosttest/shim.c').read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(old)==1
 (work/'shim.c').write_text(shim.replace(old,old+'\n    extern void send_hook(const uint8_t *);send_hook(buf);'))
 flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(work/'src')]
 if 'ST_HOME_DRIVE=17' in (work/'src/startup_trace.h').read_text():flags+=['-DPHASE_LABELS']
 exe=work/'probe';cmd=[*flags,HERE/'test_home.c',work/'shim.c',work/'trace.c',*[work/'src'/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred','motion_trace']],'-o',exe]
 r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
 selected=cases if variant in ['baseline','proposal','phase'] else (['drive-cross'] if variant=='mutant-drive-cutoff' else ['settle-cross'] if variant=='mutant-settle-cutoff' else ['shared-budget'] if variant=='mutant-budget-reset' else ['drive-deadline'])
 for case in selected:
  r=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=30)
  expected=variant in ['proposal','phase'] or (variant=='baseline' and case in ['normal','wrap'])
  assert (r.returncode==0)==expected,(variant,case,r.stdout,r.stderr)
  if not expected:
   predicate='host_fault()==expected_fault' if variant=='mutant-phase-label' else 'samples==HOME_POLL_LIMIT-1' if variant=='mutant-budget-reset' else '!g_homed && g_home_state==HOME_FAILED' if variant in ['mutant-drive-cutoff','mutant-settle-cutoff','mutant-inhibit'] else 'wire_queries>answered'
   assert 'Assertion' in r.stderr and predicate in r.stderr,(variant,case,r.stderr)
  rows.append(dict(variant=variant,case=case,expectedPass=expected,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:800]))
verify()
report=dict(status='offline-source-fix-verified-camera-unqualified',baseManifestSHA256=sha(manifest_path),candidateManifestSHA256=sha(candidate/'manifest.json') if candidate else None,candidateImageSHA256=cm['imageSHA256'] if cm else None,candidateSourcePins=cm['sources'] if cm else None,sourcePins=m['sources'],sourcePinsVerifiedBeforeAndAfter=49,results=rows,sizes=sizes,hardwareReportsSent=0,cameraQualified=False,inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.c']})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['sourcePins','candidateSourcePins','results']},indent=2))
