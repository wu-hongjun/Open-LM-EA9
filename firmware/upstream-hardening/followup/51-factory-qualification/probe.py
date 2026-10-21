#!/usr/bin/env python3
"""Small pinned-source counterexample, not a complete candidate or hardware test."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private') and out.name.startswith('astra51-');out.mkdir(exist_ok=False)
base=ROOT/'artifacts/private/homing39-repeat';mp=base/'manifest.json'
assert sha(mp)=='9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a'
m=json.loads(mp.read_text());assert sha(base/'contax-zeiss-50-f1-4.bin')=='87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44'
for n,h in m['sources'].items():assert sha(base/n)==h,n
s=(base/'src/main.c').read_text();name='static uint8_t home_still_for(struct home_still *st, uint32_t ms)';lo=s.index(name+'\n{');helper=s[lo:s.index('\n}',lo)+2]
up=ROOT/'references/upstream/weiziqian/E-mount-impl-on-Techart-EA9/src/main.c'
checks=(ROOT/'references/checksums.sha256').read_text().splitlines();pin=next(l.split()[0] for l in checks if l.endswith(str(up.relative_to(ROOT/'references'))));assert sha(up)==pin
assert 'if (!drive_ok) goto failed;' in s and 'drive_ok' not in up.read_text()
c=r'''#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#define HOME_STILL_COUNTS 6
struct home_still {int32_t at;uint32_t t;};
static int32_t sample;static uint32_t tick;
static int32_t abs_encoder_track(void){return sample;}
static uint32_t millis(void){return tick;}
HELPER
int main(void){
 for(unsigned wrap=0;wrap<2;wrap++){
  uint32_t start=wrap?UINT32_MAX-100:0;
  struct home_still st={0,start};unsigned qualified=0;
  /* Supplied trace-shaped trajectory. This is not a recovered raw trace. */
  for(unsigned t=40;t<300;t++){
   tick=start+t;sample=t<280?-(int32_t)(t*10):-2902;
   if(home_still_for(&st,40))qualified=1;
  }
  assert(!qualified && st.at==-2902 && (uint32_t)(start+300-st.t)==20);
  /* A released fixed anchor can supply the missing dwell without more drive. */
  int32_t anchor=st.at;unsigned fixed=1;
  for(unsigned t=300;t<=340;t++){tick=start+t;sample=-2902;
   int64_t d=(int64_t)sample-anchor;if(d>6||d< -6)fixed=0;}
  assert(fixed);
  /* Counterexample: ordinary settle resets its anchor after postdrive drift. */
  st=(struct home_still){anchor,start+300};qualified=0;fixed=1;
  for(unsigned t=300;t<=400;t++){tick=start+t;sample=t<310?anchor:anchor-7;
   int64_t d=(int64_t)sample-anchor;if(d>6||d< -6)fixed=0;
   if(home_still_for(&st,40))qualified=1;}
  assert(qualified && !fixed);
 }
 /* Exact helper uses full-domain subtraction, including corrupted positions. */
 struct home_still st={INT32_MIN,0};sample=INT32_MAX;tick=40;
 assert(!home_still_for(&st,40)&&st.at==INT32_MAX&&st.t==40);
 st=(struct home_still){INT32_MAX,0};sample=INT32_MIN;tick=40;
 assert(!home_still_for(&st,40)&&st.at==INT32_MIN&&st.t==40);
 puts("PASS late280/cap300 counterexample; fixed-anchor drift rejection; tick wrap; signed extremes");
}
'''.replace('HELPER',helper)
(out/'probe.c').write_text(c)
subprocess.run(['clang','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=undefined,address',str(out/'probe.c'),'-o',str(out/'probe')],check=True)
r=subprocess.run([str(out/'probe')],check=True,capture_output=True,text=True)
report={'status':'source-policy-counterexample-confirmed','baselineManifestSHA256':sha(mp),'baselineSourcesVerified':len(m['sources']),'upstreamMainSHA256':pin,'helperSHA256':hashlib.sha256(helper.encode()).hexdigest(),'result':r.stdout.strip(),'hardwareOperations':0,'limits':'Source-extracted stillness helper with synthetic coordinates/ticks; not complete motor_home execution, physical endstop proof, or candidate acceptance.'}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
