#!/usr/bin/env python3
"""Offline final-source composition probes; all mutations stay in fresh scratch."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
MANIFEST='a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de'
IMAGE='04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def function(s,name):
    start=s.index(name+'\n{'); start=s.rfind('\n',0,start)+1
    return s[start:s.index('\n}',start)+2]+'\n'
def run(cmd):
    r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=30)
    assert r.returncode==0,(cmd,r.stdout,r.stderr)
    return r.stdout.strip()
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    src=a.source.resolve();out=a.output.resolve()
    assert src.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
    out.mkdir(exist_ok=False)
    manifest=json.loads((src/'manifest.json').read_text());assert manifest['imageSHA256']==IMAGE
    digest=sha(src/'manifest.json');assert digest==MANIFEST;assert sha(src/'contax-zeiss-50-f1-4.bin')==IMAGE
    for n,h in manifest['sources'].items():assert sha(src/n)==h,n
    cases=['home-to-absolute','home-to-relative','home-to-defocus','home-to-capture',
      'home-drive-pump-cap-move','home-settle-pump-cap-relative','home-drive-read-cap-capture',
      'home-settle-read-cap-capture','home-drive-pump-before-relative','home-settle-read-before-relative',
      'home-drive-pump-cap-session','home-settle-pump-cap-shutdown','home-drive-read-cap-fault',
      'home-settle-read-cap-fault','home-final-fault','home-reset-session',
      'servo-start-session','servo-start-shutdown','servo-start-stop','servo-start-fault',
      'servo-first-query-session','servo-first-query-shutdown','servo-first-capture',
      'servo-gap-max','servo-gap-max-relative','servo-gap-max-capture',
      'servo-gap-max-query-session','servo-gap-max-query-shutdown',
      'servo-wrap-arrival','servo-retarget-wrap','servo-final-fault'] + [f'deadband-{caller}-{cut}' for caller in ['move','scan','drive'] for cut in ['inhibit','session','shutdown']]
    work=out/'final';shutil.copytree(src/'src',work/'src');shutil.copytree(src/'tools',work/'tools')
    s=(work/'src/main.c').read_text()
    constants='\n'.join(re.findall(r'^#define (?:HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|POLL_LIMIT|ATTEMPTS)|FOCUS_DEADBAND_COUNTS|MOVE_DUTY|SCAN_(?:V_MIN|V_MAX|STOP_MS|RUNUP_COUNTS|RUNOUT_COUNTS))\s+.*$',s,re.M))+'\n'
    stock=s[s.index('static const struct servo_cfg STOCK = {'):];stock=stock[:stock.index('\n};')+4]
    (work/'config.inc').write_text(constants+stock)
    names=['static void focus_report_at(int32_t counts)','static void focus_answer_queries(void)',
      'static void focus_report(void)','static void pump(int32_t pos)',
      'static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)',
      'static uint8_t focus_invalid(void)','static void focus_event(uint8_t code, uint8_t param)',
      'static uint8_t focus_abort(void)','static uint8_t focus_retarget(int32_t *target)',
      'static uint8_t focus_run(int32_t want, uint16_t target_u,\n                         const struct servo_cfg *cfg)',
      'static void focus_scan(const struct em_focus_cmd *c)',
      'static void focus_drive(const struct em_focus_cmd *c)',
      'static void focus_exec(const struct em_focus_cmd *c, uint32_t session)',
      'static void home_cutoff(void)','static uint8_t home_command(void)',
      'static uint8_t home_cancel_requested(void)']
    body=''.join(function(s,n) for n in names)
    body=body.replace('if (tag == EM_REC_Q_POS2D)','compute_hook();\n        if (tag == EM_REC_Q_POS2D)')
    body=body.replace('\tfocus_pred_end(&g_pred);','\tobserve(&r);\n\tfocus_pred_end(&g_pred);')
    body=body.replace('\t\treturn SERVO_OK;', '\t\tdeadband_hits++;\n\t\treturn SERVO_OK;')
    begin=s.index('struct home_still {');body+=s[begin:s.index('\n};',begin)+3]+'\n'
    body+=''.join(function(s,n) for n in ['static void home_still_init(struct home_still *st)',
      'static uint8_t home_still_for(struct home_still *st, uint32_t ms)',
      'static void motor_home(void)','static void home_service(void)'])
    (work/'main.inc').write_text(body)
    encoder=(work/'src/abs_encoder.c').read_text()
    tracker='#define ENC_COUNTS 16384\n'+function(encoder,'void abs_encoder_track_reset(void)').replace('g_track      = 0;','resets++;\n\tg_track      = 0;')+function(encoder,'int32_t abs_encoder_track(void)')
    (work/'tracker.inc').write_text(tracker)
    em=work/'src/emount.c';em.write_text(em.read_text()+'\nunsigned test_events(void){return g_event_n;}\nunsigned query_answers(void){return g_ans_n;}\nunsigned query_pending(void){return g_query_n;}\nunsigned test_scan(void){return ea9_data[EA9_OFF_06+EM06_SCAN_STATE];}\n')
    trace_source=work/'src/startup_trace.c';trace_source.write_text(trace_source.read_text()+'\nunsigned test_fault(void){return fault;}\n')
    trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','').replace('void st_unlock(uint32_t k) { (void)k; }','').replace('memory+a-ST_FLASH_BASE','memory+(a-ST_FLASH_BASE)');(work/'trace.c').write_text(trace)
    shim=(work/'tools/hosttest/shim.c').read_text();old='uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{';assert shim.count(old)==1
    (work/'shim.c').write_text(shim.replace(old,old+'\n    extern void send_hook(const uint8_t *);send_hook(buf);'))
    flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(work),'-I'+str(work/'tools/hosttest'),'-I'+str(work/'src')]
    modules=['servo','emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred']
    run([*flags,HERE/'test_composition.c',work/'shim.c',work/'trace.c',*[work/'src'/(n+'.c') for n in modules],'-o',work/'probe'])
    rows=[dict(case=c,output=run([work/'probe',c])) for c in cases]
    # Retained relative API, independently compiled with prior finite probes.
    run([*flags,ROOT/'firmware/upstream-hardening/lanes/06-motion/test_servo.c',work/'src/servo.c',work/'src/startup_trace.c',ROOT/'firmware/upstream-diagnostic/tests/trace_host.c','-o',work/'relative'])
    relative=[dict(case=c,output=run([work/'relative',c])) for c in ['runaway','wrongway','retarget','freeze','stale','final-inhibit','ordinary']]
    controls=[]
    for label,case,filename,old,new in [
      ('target','home-to-absolute','main.inc','servo_move_from(here, want, cfg, &r);','servo_move_rel(want - here, cfg, &r);'),
      ('drive-deadline','home-drive-pump-cap-move','main.inc','\\n\\t\\t    && (uint32_t)(millis() - t0) < HOME_MS',''),
      ('settle-deadline','home-settle-read-cap-capture','main.inc','\\n\\t\\t    && (uint32_t)(millis() - t0) < HOME_SETTLE_MS',''),
      ('positive-time','servo-gap-max-relative','src/focus_pred.c','(dt > INT32_MAX ? 0 : ((pos - p->last_pos) * 256) / (int32_t)dt)','((pos - p->last_pos) * 256) / (int32_t)dt')]:
        control=out/label;shutil.copytree(work,control)
        old=old.replace('\\n','\n').replace('\\t','\t')
        path=control/filename;body=path.read_text();assert body.count(old)==1;path.write_text(body.replace(old,new))
        cflags=[x.replace(str(work),str(control)) for x in flags]
        run([*cflags,HERE/'test_composition.c',control/'shim.c',control/'trace.c',*[control/'src'/(n+'.c') for n in modules],'-o',control/'probe'])
        r=subprocess.run([str(control/'probe'),case],capture_output=True,text=True,timeout=10)
        assert r.returncode!=0 and 'Assertion failed:' in r.stderr,(label,r.stdout,r.stderr)
        controls.append(dict(variant=label,case=case,exitCode=r.returncode,stderr=r.stderr.strip()))
    assert sha(src/'manifest.json')==digest
    for n,h in manifest['sources'].items():assert sha(src/n)==h,n
    result=dict(source=str(src),manifestSHA256=digest,imageSHA256=IMAGE,sourceHashes=manifest['sources'],cases=rows,relativeCases=relative,negativeControls=controls,hardwareAccess=False,externalFixtureHashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'firmware/upstream-hardening/lanes/06-motion/test_servo.c',ROOT/'firmware/upstream-diagnostic/tests/trace_host.c']},inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.c','.py']})
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=str(out/'result.json'),cases=len(rows),relativeCases=len(relative))))
if __name__=='__main__': main()
