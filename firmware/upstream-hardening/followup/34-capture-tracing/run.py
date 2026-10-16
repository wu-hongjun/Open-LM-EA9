#!/usr/bin/env python3
"""Exact AF3.6 production emount bodies, synthetic IRQ cuts, parity and controls."""
import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from apply import apply
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CASES=['ordinary','raw','session-irq','shutdown-irq','pending','session-high','failed-tx','shutdown','queue','phase']
ENUMS='''
enum { ST_OWNER_CS=11, ST_OWNER_OFFER=12, ST_OWNER_TAKE=13, ST_TX_START=14,
 ST_TX_RETURN=15, ST_SHUTDOWN_ADMIT=16, ST_OWNER_COMPLETE=17, ST_OWNER_PHASE=18 };
'''
MOTION='''#include <stdint.h>
enum { ST_MC_NONE=0, ST_MC_ATTEMPT=1, ST_MC_QUEUED=2, ST_MC_SUPPRESSED=3,
 ST_MC_QUEUE_FULL=4, ST_MC_TX_RETURN=5, ST_MC_ABORTED=6 };
void st_motion_completion(uint8_t state, uint16_t event);
'''
def command(args, cwd=None):
    r=subprocess.run(list(map(str,args)),capture_output=True,text=True,cwd=cwd,timeout=40)
    assert r.returncode==0,(args,r.stderr)
    return r.stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base=ROOT/'artifacts/private/handoff36-repeat';out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
    m=json.loads((base/'manifest.json').read_text())
    assert m==json.loads((ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    for name,h in m['sources'].items():assert sha(base/name)==h,name
    assert sha(base/'contax-zeiss-50-f1-4.bin')==m['imageSHA256']
    shim=(base/'tools/hosttest/shim.c').read_text()
    shim=shim.replace('uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{',
        'void host_probe_send(const uint8_t *,uint16_t);\nextern int host_tx_fail;\nuint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{\n if(host_tx_fail)return 0;\n host_probe_send(buf,len);')
    (out/'shim.c').write_text(shim)
    results={};sizes={};stacks={}
    for variant in ['frozen','proposal','live-return-mutant','raw-bit-mutant']:
        work=out/variant;shutil.copytree(base/'src',work/'src');src=work/'src'
        if variant!='frozen':apply(src)
        if variant=='live-return-mutant':
            q=src/'emount.c';s=q.read_text();old='em_trace(ST_TX_RETURN, trace_identity, trace_flags, trace_session);';assert s.count(old)==1
            q.write_text(s.replace(old,'em_trace(ST_TX_RETURN, trace_identity, trace_flags, g_session_generation);'))
        if variant=='raw-bit-mutant':
            q=src/'emount.c';s=q.read_text();old='| (g_owner.capture ? ET_RAW : 0) | (admitted ? ET_RESULT : 0)';assert s.count(old)==1
            q.write_text(s.replace(old,'| (admitted ? ET_RESULT : 0)'))
        # Test-only ABI declarations for lane35/lane33. Production integration
        # must use their actual headers and core, not this observation collector.
        q=src/'startup_trace.h';q.write_text(q.read_text()+ENUMS)
        (src/'motion_trace.h').write_text(MOTION)
        flags=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(base/'tools/hosttest')]
        q=src/'emount.c';production=q.read_text();q.write_text(production+'\nvoid test_set_session(uint32_t value){g_session_generation=value;}\n')
        command([*flags,HERE/'test_capture.c',out/'shim.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown']],'-o',work/'probe'])
        q.write_text(production)  # Test seam is excluded from production ARM measurement.
        rows=[]
        cases=CASES if variant in ['frozen','proposal'] else ['session-irq'] if variant=='live-return-mutant' else ['raw']
        for case in cases:
            r=subprocess.run([str(work/'probe'),case,'1','1'],capture_output=True,text=True,timeout=10)
            expected=0 if variant=='proposal' else 1
            assert r.returncode==expected,(variant,case,r.returncode,r.stdout,r.stderr)
            assert 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr,r.stderr
            row={'case':case,'traceAssertionsExit':r.returncode,'assertion':r.stderr.strip()}
            if variant in ['frozen','proposal']:
                on=command([work/'probe',case,'0','1']);off=command([work/'probe',case,'0','0'])
                assert on==off,(variant,case,on,off)
                row['parity']=json.loads(on)
            rows.append(row)
        results[variant]=rows
        if variant in ['frozen','proposal']:
            deps=ROOT/'tools/firmware-deps';arm=deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-'
            command([str(arm)+'gcc',*m['flags'],*m['unitFlags']['emount'],'-Isrc','-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include'),'-c','src/emount.c','-o','emount.o'],cwd=work)
            sized=command([str(arm)+'size',work/'emount.o']).splitlines()[1].split();sizes[variant]={'text':int(sized[0]),'data':int(sized[1]),'bss':int(sized[2])}
            stacks[variant]=[line.split('\t')[0].split(':')[-1]+':'+line.split('\t')[1] for line in (work/'emount.su').read_text().splitlines() if any(k in line for k in ['em_transmit','em_poll','em_cs_edge','em_pump_status','em_trace'])]
    assert [r['parity'] for r in results['frozen']]==[r['parity'] for r in results['proposal']]
    for name,h in m['sources'].items():assert sha(base/name)==h,name
    report={'status':'offline-staged-observation-only','baseImageSHA256':m['imageSHA256'],'baseManifestSHA256':sha(base/'manifest.json'),'sourceHashes':{n:m['sources'][n] for n in ['src/emount.c','src/em_owner.c','src/em_shutdown.c','src/em_frame.c']},'proposalEmountSHA256':sha(out/'proposal/src/emount.c'),'cases':results,'objectSizes':sizes,'textDelta':sizes['proposal']['text']-sizes['frozen']['text'],'selectedStackBytes':stacks,'hardwareAccess':False,'factoryParityClaimed':False,'captureFixClaimed':False,'abiCollectorOnly':True}
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'cases':len(CASES),'frozenFailingControls':len(CASES),'mutationControls':2,'textDelta':report['textDelta'],'objectSizes':sizes,'selectedStackBytes':stacks},indent=2))
if __name__=='__main__':main()
