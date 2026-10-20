#!/usr/bin/env python3
"""Source-bound release/legacy ADC dependency and failure controls; offline."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
if not __debug__:raise SystemExit('Assertions required')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--candidate',type=Path);a=p.parse_args();out=a.output.resolve()
assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
base=ROOT/'artifacts/private/readiness38-repeat';m=json.loads((base/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'manifest.json')=='be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0'
for name,pin in m['sources'].items():assert sha(base/name)==pin
candidate=a.candidate.resolve() if a.candidate else None
if candidate:
 assert candidate.is_relative_to(ROOT/'artifacts/private')
 cm=json.loads((candidate/'manifest.json').read_text());cpin=sha(candidate/'manifest.json')
 assert cm['loaderVersion']==[3,9,0] and len(cm['sources'])==49
 def verify_candidate():
  assert sha(candidate/'manifest.json')==cpin
  assert sha(candidate/'contax-zeiss-50-f1-4.bin')==cm['imageSHA256']
  assert sha(candidate/'tools/hosttest/shim.c')==cm['hostTestShimSHA256']
  for name,pin in cm['sources'].items():assert sha(candidate/name)==pin,name
 verify_candidate()
board='''#include <stdint.h>
typedef union {volatile uint32_t reg;struct {volatile uint32_t RESRDY:1;volatile uint32_t SYNCBUSY:1;}bit;} R;
struct adc_regs {R CALIB,CTRLB,SAMPCTRL,REFCTRL,INPUTCTRL,STATUS,CTRLA,INTFLAG,SWTRIG,RESULT;};
extern struct adc_regs fake_adc;extern uint32_t fake_fuse;
#define ADC (&fake_adc)
#define ADC_FUSES_BIASCAL_ADDR ((uintptr_t)&fake_fuse)
#define ADC_FUSES_BIASCAL_Msk 0u
#define ADC_FUSES_BIASCAL_Pos 0u
#define ADC_FUSES_LINEARITY_0_ADDR ((uintptr_t)&fake_fuse)
#define ADC_FUSES_LINEARITY_0_Msk 0u
#define ADC_FUSES_LINEARITY_0_Pos 0u
#define ADC_FUSES_LINEARITY_1_ADDR ((uintptr_t)&fake_fuse)
#define ADC_FUSES_LINEARITY_1_Msk 0u
#define ADC_FUSES_LINEARITY_1_Pos 0u
#define ADC_CALIB_BIAS_CAL(x) (x)
#define ADC_CALIB_LINEARITY_CAL(x) (x)
#define GCLK_CLKCTRL_ID_ADC_Val 1u
#define PM_APBCMASK_ADC 1u
#define ADC_CTRLB_PRESCALER_DIV64 1u
#define ADC_CTRLB_RESSEL_12BIT 1u
#define ADC_REFCTRL_REFSEL_INT1V 1u
#define ADC_INPUTCTRL_GAIN_1X 1u
#define ADC_INPUTCTRL_MUXNEG_GND 1u
#define ADC_INPUTCTRL_MUXPOS_SCALEDIOVCC 1u
#define ADC_CTRLA_ENABLE 1u
#define ADC_INTFLAG_RESRDY 1u
#define ADC_SWTRIG_START 1u
'''
def function(s,name):
 start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1;return s[start:s.index('\n}',start)+2]+'\n'
rows=[]
for variant in ('baseline-release','proposal-release','proposal-legacy','mutant-resample'):
 w=out/variant;shutil.copytree(base/'src',w/'src')
 if variant!='baseline-release':runpy.run_path(str(HERE/'apply.py'))['apply'](w)
 s=(w/'src/main.c').read_text()
 if variant=='mutant-resample':
  old='#ifndef EA9_NO_LOG\n\tvdd_track_sample();\n#endif';assert s.count(old)==1;s=s.replace(old,'\tvdd_track_sample();')
 pump=function(s,'static void pump(int32_t pos)')
 start=s.index('\tabs_encoder_init();');end=s.index('\tmotor_release();',start)+len('\tmotor_release();')
 if candidate and variant=='proposal-release':
  final=(candidate/'src/main.c').read_text()
  fs=final.index('\tabs_encoder_init();');fe=final.index('\tmotor_release();',fs)+len('\tmotor_release();')
  assert function(final,'static void pump(int32_t pos)')==pump
  assert final[fs:fe]==s[start:end]
 (w/'pump.inc').write_text(pump);(w/'startup.inc').write_text(s[start:end]+'\n')
 (w/'board.h').write_text('#ifndef ADC_TEST_BOARD\n#define ADC_TEST_BOARD\n'+board+'\n#endif\n')
 for name in ('vdd.h','clock.h','delay.h','startup_trace.h'):(w/name).write_bytes((w/'src'/name).read_bytes())
 vdd=(w/'src/vdd.c').read_text();old='\tADC->SWTRIG.reg  = ADC_SWTRIG_START;';assert vdd.count(old)==1
 # Explicit peripheral boundary: model W1C RESRDY and completed/stuck conversion.
 vdd=vdd.replace(old,old+'\n\textern void host_adc_start(void);host_adc_start();')
 (w/'vdd.c').write_text(vdd)
 flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-Wno-unused-function','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(w)]
 if variant!='proposal-legacy':flags+=['-DEA9_NO_LOG']
 if variant in ('proposal-release','mutant-resample'):flags+=['-DFIXED_RELEASE']
 r=subprocess.run([*flags,str(HERE/'test_adc.c'),str(w/'vdd.c'),'-o',str(w/'probe')],capture_output=True,text=True);assert r.returncode==0,r.stderr
 for case in ('healthy','stalled-capture','stalled-startup'):
  expected=(case=='healthy' and variant in ('baseline-release','proposal-legacy')) or variant=='proposal-release' or (variant=='mutant-resample' and case=='stalled-startup')
  r=subprocess.run([str(w/'probe'),case],capture_output=True,text=True,timeout=20)
  assert (r.returncode==0)==expected,(variant,case,r.stdout,r.stderr)
  if not expected:
   assert 'FAIL:' in r.stderr and 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr
   if case=='stalled-capture':assert 'production ADC fail-stop=3' in r.stderr and 'fault=3 adc=1 polls=1 answers=1 ack=0 motors=0 encoders=0' in r.stderr and 'FAIL: !fault&&ack==1&&answers==2&&polls==2&&inhibited' in r.stderr
   elif case=='stalled-startup':assert 'production ADC fail-stop=3' in r.stderr and 'fault=3 adc=1 polls=0 answers=0 ack=0 motors=0 encoders=1' in r.stderr and 'FAIL: !fault&&motors==1&&encoders==1&&releases==1' in r.stderr
   else:assert variant=='mutant-resample' and 'FAIL: !conversions&&!stage_adc' in r.stderr and 'fault=0 adc=2 polls=2 answers=2 ack=1 motors=1 encoders=1' in r.stderr
  rows.append(dict(variant=variant,case=case,expectedPass=expected,exitCode=r.returncode,stdout=r.stdout.strip(),failure=r.stderr.strip()))
for name,pin in m['sources'].items():assert sha(base/name)==pin
if candidate:verify_candidate()
report={'status':'passed-offline-unused-adc-dependency-controls','sourceFilesVerified':len(m['sources']),'results':rows,'productionADCConversionAndWaitBody':True,'productionWaitBudget':4194304,'syntheticBoundary':'RESRDY W1C/start completion or stalled conversion; protocol scheduler supplied, not measured hardware timing','physicalHomeFaultCauseProven':False,'hardwareReportsSent':0,'inputSHA256':{p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.c')}}
report['candidateManifestSHA256']=cpin if candidate else None
report['candidatePumpAndStartupBodiesMatched']=bool(candidate)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'cases':len(rows),'expectedPasses':sum(x['expectedPass'] for x in rows),'expectedFailures':sum(not x['expectedPass'] for x in rows),'allMatched':True}))
