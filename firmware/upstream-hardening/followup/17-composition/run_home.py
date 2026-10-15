#!/usr/bin/env python3
"""Offline exact-body composition probe: no device interfaces, fresh scratch only."""
import argparse,hashlib,json,re,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=a.source.resolve();out=a.output.resolve()
assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
hashes={p.name:sha(p) for p in (source/'src').iterdir() if p.is_file()}
manifest=json.loads((source/'manifest.json').read_text()) if (source/'manifest.json').exists() else None
if manifest:
 for name,h in manifest['sources'].items():assert sha(source/name)==h,name
def function(s,name):
 start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1;end=s.index('\n}',start)+2
 return s[start:end]+'\n'
rows=[]
for variant in ['composed','proposal']:
 work=out/variant;shutil.copytree(source/'src',work/'src')
 # A post-integration source can serve as the exact proposal while the
 # baseline removes only this lane's guard, preserving all other edits.
 main=work/'src/main.c';text=main.read_text()
 guard='''    /* A rejected encoder coordinate must never become a new home reference.
     * Inhibition is sticky until restart, so this attempt is terminal too. */
    if (motor_is_inhibited()) {
        g_next_pending = 0;
        g_home_state = HOME_FAILED;
        return 1;
    }
'''
 integrated=guard in text
 if integrated:
  assert text.count(guard)==1
  main.write_text(text.replace(guard,''))
 if variant=='proposal':runpy.run_path(str(HERE/'apply.py'))['apply'](work)
 if integrated and variant=='proposal':assert main.read_text()==text
 s=(work/'src/main.c').read_text();encoder=(work/'src/abs_encoder.c').read_text()
 constants='\n'.join(re.findall(r'^#define HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|POLL_LIMIT)\s+.*$',s,re.M))+'\n'
 body=constants+function(s,'static uint8_t home_cancel_requested(void)')
 body+=s[s.index('struct home_still {'):s.index('\n};',s.index('struct home_still {'))+3]+'\n'
 for n in ['static void home_still_init(struct home_still *st)','static uint8_t home_still_for(struct home_still *st, uint32_t ms)','static void motor_home(void)']:body+=function(s,n)
 (work/'home.inc').write_text(body)
 board=(work/'src/board.h').read_text()
 tracker=re.search(r'^#define ENC_COUNTS\s+.*$',board,re.M).group(0)+'\n'
 tracker+=function(encoder,'void abs_encoder_track_reset(void)').replace('g_track      = 0;','resets++;\n\tg_track      = 0;')+function(encoder,'int32_t abs_encoder_track(void)')
 (work/'tracker.inc').write_text(tracker)
 exe=work/'probe'
 cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'src'),str(HERE/'test_home.c'),'-o',str(exe)]
 r=subprocess.run(cmd,capture_output=True,text=True);assert r.returncode==0,r.stderr
 for cut in [0,1,3,4,8,100]:
  r=subprocess.run([str(exe),str(cut),str(int(variant=='proposal'))],capture_output=True,text=True,timeout=10)
  assert r.returncode==0,(variant,cut,r.stdout,r.stderr)
  rows.append(dict(variant=variant,cut=cut,stdout=r.stdout.strip()))
  if variant=='composed' and cut:
   r=subprocess.run([str(exe),str(cut),'1'],capture_output=True,text=True,timeout=10)
   assert r.returncode!=0 and 'Assertion' in r.stderr,(cut,r.stdout,r.stderr)
   rows.append(dict(variant=variant,cut=cut,negativeControl=True,exitCode=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr.strip()))
assert hashes=={p.name:sha(p) for p in (source/'src').iterdir() if p.is_file()}
if manifest:
 for name,h in manifest['sources'].items():assert sha(source/name)==h,name
(out/'result.json').write_text(json.dumps(dict(source=str(source),sourceHashes=hashes,imageSHA256=manifest['imageSHA256'] if manifest else None,manifestVerified=bool(manifest),results=rows),indent=2)+'\n')
print(json.dumps(rows,indent=2))
