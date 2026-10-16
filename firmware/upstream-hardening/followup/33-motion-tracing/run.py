#!/usr/bin/env python3
"""Compile pinned production bodies + observation proposal; synthetic parity and bad-observer controls."""
import argparse, hashlib, json, re, shutil, struct, subprocess
from pathlib import Path
from apply import apply
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def function(s,name):
    start=s.index(name+'\n{');start=s.rfind('\n',0,start)+1
    return s[start:s.index('\n}',start)+2]+'\n'
def decode(h):
    b=bytes.fromhex(h);assert len(b)==144
    u=lambda o:struct.unpack_from('<I',b,o)[0]
    i=lambda o:struct.unpack_from('<i',b,o)[0]
    return dict(version=b[0],valid=b[1],frozen=b[2],flags=b[3],begin_ms=u(4),start=i(8),initial_target=i(12),target=i(16),leg_start=i(20),guard_ms=u(24),guard_position=i(28),duty=struct.unpack_from('<h',b,32)[0],command_operand=struct.unpack_from('<H',b,34)[0],command_op=b[36],accepted_op=b[37],accepted_operand=struct.unpack_from('<H',b,38)[0],direction=struct.unpack_from('<b',b,40)[0],retargets=b[41],state=b[42],outcome=b[43],count=struct.unpack_from('<H',b,44)[0],next=b[46],fault=b[47],completion_ms=u(48),completion_code=b[52],completion_param=b[53],completion_state=b[54],last_ms=u(56),accepted_ms=u(60),samples=[dict(ms=u(o),position=i(o+4),duty=struct.unpack_from('<h',b,o+8)[0],state=b[o+10],retargets=b[o+11]) for o in range(64,112,12)],reserved=list(b[112:]))
def verify_servo(case,d):
    if case==6:
        assert d['valid']==1 and d['frozen']==0 and d['outcome']==5 and d['completion_state']==6
        return
    pos=[379,1121,1601,-101,761,761][case];reads=[5,4,4,4,7,8][case]
    assert d['version']==1 and d['valid']==1 and d['frozen']==1
    assert d['guard_position']==pos and d['guard_ms']==reads*5
    assert d['initial_target']==(500 if case in (1,3) else 1000)
    assert d['start']==(1000 if case in (1,3) else 500)
    assert d['target']==(200 if case>=4 else d['initial_target'])
    assert d['leg_start']==(640 if case>=4 else d['start'])
    assert d['direction']==(-1 if case in (1,3,4,5) else 1)
    assert d['fault']==(14 if case in (2,3) else 15)
    assert d['outcome']==(3 if case in (2,3) else 4)
    assert d['count']==reads and d['next']==reads%4
    assert d['command_op']==1 and d['command_operand']==0x1234
    assert d['accepted_op']==(3 if case>=4 else 1)
    assert d['accepted_operand']==(((-250)&65535) if case>=4 else 0x1234)
    assert d['retargets']==int(case>=4)
    assert d['completion_state']==3 and d['completion_ms']==(reads+1)*5
    assert d['reserved']==[0]*32
    ordered=d['samples'][d['next']:]+d['samples'][:d['next']]
    assert [s['ms'] for s in ordered]==list(range((reads-3)*5,(reads+1)*5,5))
    assert ordered[-1]['position']==pos
    if case==0:assert [s['position'] for s in ordered]==[460,420,380,379]
    if case==4:assert [s['position'] for s in ordered]==[630,700,760,761]
    assert ordered[-1]['state']==d['state']
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.source.resolve();out=a.output.resolve()
    assert source.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
    pins=json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    assert sha(source/'contax-zeiss-50-f1-4.bin')==pins['imageSHA256']
    for n,h in pins['sources'].items():assert sha(source/n)==h,n
    out.mkdir(exist_ok=False)
    results={};focus_cases=['interior','upper','lower','relative','defocus','relative-clamp','distance','stationary','arrival','deadband','session','shutdown','stop','fault','stale','retarget','retarget-relative','retarget-defocus','retarget-repeat','retarget-small','wrongway','runaway']
    variants=['frozen','proposal','missing-samples','wrong-guard','wrong-direction','lost-first','wrong-command','missing-completion']
    mutations={
      'missing-samples':('    if (!trace.valid || trace.frozen) return;\n    struct st_motion_sample *s=', '    if (1) return;\n    struct st_motion_sample *s='),
      'wrong-guard':('trace.guard_position=trace.samples[(trace.sample_next-1u)&3u].position;', 'trace.guard_position=trace.initial_start;'),
      'wrong-direction':('trace.direction=(packed&ST_MS_NEGATIVE) ? -1 : 1;', 'trace.direction=1;'),
      'lost-first':('    if (trace.frozen) return;', '    if (0) return;'),
      'wrong-command':('trace.accepted_operand=pending_operand;', 'trace.accepted_operand=0;'),
      'missing-completion':('    trace.completion_ms=millis(); trace.completion_state=state;', '    trace.completion_ms=millis(); trace.completion_state=0; (void)state;'),
    }
    for variant in variants:
        w=out/variant;shutil.copytree(source/'src',w/'src');shutil.copytree(source/'tools',w/'tools')
        if variant!='frozen':apply(w/'src')
        else:
            for name in ('motion_trace.c','motion_trace.h'):shutil.copyfile(HERE/name,w/'src'/name)
        if variant in mutations:
            p=w/'src/motion_trace.c';s=p.read_text();old,new=mutations[variant];assert old in s;s=s.replace(old,new);p.write_text(s)
        flags=['clang','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(w),'-I'+str(w/'tools/hosttest'),'-I'+str(w/'src')]
        tracehost=w/'trace_host.c';tracehost.write_text((ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('memory+a-ST_FLASH_BASE','memory+(a-ST_FLASH_BASE)'))
        def build(test,modules,name,extra=[]):
            r=subprocess.run(list(map(str,[*flags,HERE/test,tracehost,*extra,*[w/'src'/(n+'.c') for n in modules],'-o',w/name])),capture_output=True,text=True)
            assert r.returncode==0,r.stderr
        build('test_servo.c',['servo','startup_trace','motion_trace'],'servo')
        rows=[]
        for case in range(7):
            capture=w/f'servo-{case}.bin';r=subprocess.run([str(w/'servo'),str(case),str(capture)],capture_output=True,text=True,timeout=10);assert r.returncode==0,(variant,case,r.stderr,r.stdout)
            row=json.loads(r.stdout);d=decode(row.pop('trace'));row['controlSHA256']=sha(capture)
            try:verify_servo(case,d);good=True
            except AssertionError:good=False
            row['traceCorrect']=good;row['decoded']=d;rows.append(row)
            if variant=='proposal':
                assert good,(case,d)
                words=struct.unpack('<'+'i'*(len(capture.read_bytes())//4),capture.read_bytes())
                last_duty=0;samples=[]
                for kind,value in zip(words[::2],words[1::2]):
                    if kind==4:last_duty=value
                    if kind==1:samples.append((value,last_duty))
                # Final post-brake read is deliberately excluded from guard history.
                samples=samples[:-1][-4:]
                ordered=d['samples'][d['next']:]+d['samples'][:d['next']]
                assert [(x['position'],x['duty']) for x in ordered]==samples,(case,d,samples)
                if case!=6:assert d['duty']==samples[-1][1]

            if variant!='frozen':assert capture.read_bytes()==(out/'frozen'/f'servo-{case}.bin').read_bytes(),(variant,case,'control outputs changed')
        if variant in mutations:assert any(not r['traceCorrect'] for r in rows),variant
        results[variant]=dict(servo=rows)
        if variant not in ('frozen','proposal'):continue
        s=(w/'src/main.c').read_text();fragments=['#define MOVE_DUTY 1280\n#define FOCUS_DEADBAND_COUNTS 12\n']
        for name in ['static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)','static uint8_t focus_invalid(void)','static void focus_event(uint8_t code, uint8_t param)','static uint8_t focus_abort(void)','static uint8_t focus_retarget(int32_t *target)','static uint8_t focus_run(int32_t want, uint16_t target_u,\n                         const struct servo_cfg *cfg)']:
            body=function(s,name)
            if 'focus_run(' in name:body=body.replace('\tfocus_pred_end(&g_pred);','\tobserve(&r);\n\tfocus_pred_end(&g_pred);')
            fragments.append(body)
        cfg=s[s.index('static const struct servo_cfg STOCK = {'):];cfg=cfg[:cfg.index('\n};')+3]
        fragments.extend([cfg+'\n',function(s,'static void focus_exec(const struct em_focus_cmd *c, uint32_t session)')]);(w/'main.inc').write_text(''.join(fragments))
        enc=(w/'src/abs_encoder.c').read_text();board=(w/'src/board.h').read_text();(w/'tracker.inc').write_text(re.search(r'^#define ENC_COUNTS\s+.*$',board,re.M).group(0)+'\n'+function(enc,'int32_t abs_encoder_track(void)'))
        em=w/'src/emount.c';em.write_text(em.read_text()+'\nunsigned test_events(void){return g_event_n;}\nunsigned test_event_code(void){return g_event_code[0];}\n')
        build('test_focus.c',['servo','emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','focus_map','focus_dist','focus_pred','motion_trace'],'focus',[w/'tools/hosttest/shim.c'])
        frows=[]
        for case in focus_cases:
            capture=w/f'focus-{case}.bin';r=subprocess.run([str(w/'focus'),case,str(capture)],capture_output=True,text=True,timeout=10);assert r.returncode==0,(variant,case,r.stderr,r.stdout)
            lines=r.stdout.splitlines();row=json.loads(lines[0]);d=decode(json.loads(lines[1])['trace']);row['decoded']=d;row['controlAndProtocolSHA256']=sha(capture);frows.append(row)
            if variant=='proposal':
                assert capture.read_bytes()==(out/'frozen'/f'focus-{case}.bin').read_bytes(),case
                if case in ('wrongway','runaway'):
                    assert d['frozen']==1 and d['completion_state']==3 and d['guard_position']==(379 if case=='wrongway' else 1601)
                    assert d['command_op']==1 and d['initial_target']==1000 and d['start']==500
                if case in ('arrival','deadband'):assert d['completion_state']==1 and d['completion_code']==0x1d
                if case=='relative':assert d['command_op']==3 and d['command_operand']==100
                if case=='defocus':assert d['command_op']==4 and d['command_operand']==10
        results[variant]['focus']=frows
        # Retain the production finite-work and post-read inhibition regressions.
        r=subprocess.run(list(map(str,[*flags,ROOT/'firmware/upstream-hardening/lanes/06-motion/test_servo.c',tracehost,w/'src/servo.c',w/'src/startup_trace.c',w/'src/motion_trace.c','-o',w/'relative'])),capture_output=True,text=True);assert r.returncode==0,r.stderr
        relative=[]
        for case in ('runaway','wrongway','retarget','freeze','stale','final-inhibit','ordinary'):
            r=subprocess.run([str(w/'relative'),case],capture_output=True,text=True,timeout=20);assert r.returncode==0,(case,r.stderr,r.stdout);relative.append(r.stdout.strip())
        results[variant]['relative']=relative
        if variant=='proposal':
            cmd=[*flags,HERE/'test_trace.c',w/'src/motion_trace.c','-o',w/'bounds']
            r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);assert r.returncode==0,r.stderr
            r=subprocess.run([str(w/'bounds')],capture_output=True,text=True);assert r.returncode==0,r.stderr
            results[variant]['bounds']=r.stdout.strip()
    assert results['frozen']['relative']==results['proposal']['relative']
    for n,h in pins['sources'].items():assert sha(source/n)==h,n
    report=dict(baseImageSHA256=pins['imageSHA256'],sourceManifestSHA256=sha(source/'manifest.json'),sourceFilesVerified=len(pins['sources']),servoParityCases=7,focusParityCases=len(focus_cases),relativeParityCases=7,failingObserverControls=len(mutations),hardwareQualified=False,hardwareReportsSent=0,variants=results)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='variants'},indent=2))
if __name__=='__main__':main()
