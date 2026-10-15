#!/usr/bin/env python3
"""Frozen 3.4 versus exact 3.5 shared-sample composition, ASan/UBSan."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'firmware/upstream-hardening/followup/19-absolute-target'
BASE=ROOT/'artifacts/private/bounded34b'
def function(s, name):
    start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1
    return s[start:s.index('\n}',start)+2]+'\n'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.source.resolve();out=a.output.resolve()
    assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
    out.mkdir(exist_ok=False)
    manifest=json.loads((source/'manifest.json').read_text())
    for name,h in manifest['sources'].items():assert sha(source/name)==h,name
    base_manifest=json.loads((BASE/'manifest.json').read_text())
    assert sha(BASE/'manifest.json')=='8e358720a959a79a4636e1a9310fc23c08af9fa50539396d6946be6194c25a9a'
    for name,h in base_manifest['sources'].items():assert sha(BASE/name)==h,name
    assert manifest['loaderVersion']==[3,5,0]
    cases=['interior','upper','lower','relative','defocus','relative-clamp','distance','stationary','arrival','deadband','session','shutdown','stop','fault','stale','retarget','retarget-relative','retarget-defocus','retarget-repeat','retarget-small']
    fail={'interior','upper','lower','relative','defocus','relative-clamp','distance','arrival','retarget-repeat','retarget-small'}
    results={};relative={}
    for variant in ['frozen','proposal']:
        chosen=BASE if variant=='frozen' else source
        work=out/variant;work.mkdir();shutil.copytree(chosen/'src',work/'src');shutil.copytree(chosen/'tools',work/'tools')
        s=(work/'src/main.c').read_text()
        fragments=['#define MOVE_DUTY 1280\n#define FOCUS_DEADBAND_COUNTS 12\n']
        for name in ['static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)','static uint8_t focus_invalid(void)','static void focus_event(uint8_t code, uint8_t param)','static uint8_t focus_abort(void)','static uint8_t focus_retarget(int32_t *target)','static uint8_t focus_run(int32_t want, uint16_t target_u,\n                         const struct servo_cfg *cfg)']:
            body=function(s,name)
            if 'focus_run(' in name:body=body.replace('\tfocus_pred_end(&g_pred);','\tobserve(&r);\n\tfocus_pred_end(&g_pred);')
            fragments.append(body)
        cfg=s[s.index('static const struct servo_cfg STOCK = {'):];cfg=cfg[:cfg.index('\n};')+3]
        fragments.append(cfg+'\n');fragments.append(function(s,'static void focus_exec(const struct em_focus_cmd *c, uint32_t session)'))
        (work/'main.inc').write_text(''.join(fragments))
        encoder=(work/'src/abs_encoder.c').read_text();board=(work/'src/board.h').read_text()
        (work/'tracker.inc').write_text(re.search(r'^#define ENC_COUNTS\s+.*$',board,re.M).group(0)+'\n'+function(encoder,'int32_t abs_encoder_track(void)'))
        em=work/'src/emount.c';em.write_text(em.read_text()+'\nunsigned test_events(void){return g_event_n;}\nunsigned test_event_code(void){return g_event_code[0];}\n')
        flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(work/'src')]
        modules=['servo','emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred']
        cmd=[*flags,HERE/'test_target.c',work/'tools/hosttest/shim.c',ROOT/'firmware/upstream-diagnostic/tests/trace_host.c',*[work/'src'/(n+'.c') for n in modules],'-o',work/'probe']
        r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
        rows=[]
        for case in cases:
            r=subprocess.run([str(work/'probe'),case],capture_output=True,text=True,timeout=10)
            assert r.returncode==(1 if variant=='frozen' and case in fail else 0),(variant,case,r.returncode,r.stdout,r.stderr)
            rows.append(json.loads(r.stdout))
        results[variant]=rows
        # Existing relative callers must retain their sample/guard behavior.
        cmd=[*flags,ROOT/'firmware/upstream-hardening/lanes/06-motion/test_servo.c',work/'src/servo.c',work/'src/startup_trace.c',ROOT/'firmware/upstream-diagnostic/tests/trace_host.c','-o',work/'relative']
        r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
        relative[variant]=[]
        for case in ['runaway','wrongway','retarget','freeze','stale','final-inhibit','ordinary']:
            r=subprocess.run([str(work/'relative'),case],capture_output=True,text=True,timeout=10)
            assert r.returncode==0,(variant,case,r.stdout,r.stderr)
            relative[variant].append(dict(case=case,stdout=r.stdout.strip()))
    assert relative['frozen']==relative['proposal']
    for name,h in manifest['sources'].items():assert sha(source/name)==h,name
    results.update(source=str(source),sourceHashes=manifest['sources'],relativeParity=relative,proposalHashes={n:sha(out/'proposal/src'/n) for n in ['main.c','servo.c','servo.h']})
    (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(result=str(out/'result.json'),proposalCases=len(cases),frozenFailures=len(fail),relativeParityCases=len(relative['proposal'])),indent=2))
if __name__=='__main__':main()
