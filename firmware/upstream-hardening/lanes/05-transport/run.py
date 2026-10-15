#!/usr/bin/env python3
"""Offline exact-function MMIO probes plus whole-unit ARM compilation.

Host register model substitutes DATA reads and a reset midpoint interrupt hook.
The executed function bodies are extracted from frozen/staged production source.
"""
import argparse, hashlib, json, runpy, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=ROOT/'firmware/upstream-diagnostic/build'; LANE=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);args=p.parse_args()
out=args.output.resolve();out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((BASE/'manifest.json').read_text())
for n,d in m['sources'].items():assert sha(BASE/n)==d,n
assert m['imageSHA256']=='e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df'
work=out/'work';shutil.copytree(BASE/'src',work/'src');shutil.copytree(BASE/'tools/hosttest',work/'tools/hosttest')
for f in [LANE/'apply_frame.py',LANE/'apply_tx.py',HERE.parent/'02-shutdown/apply.py',HERE.parent/'01-capture/apply.py',HERE.parent/'03-homing/apply.py']:
    runpy.run_path(str(f))['apply'](work)
prior=out/'before05';shutil.copytree(work/'src',prior)
runpy.run_path(str(HERE/'apply.py'))['apply'](work)
def function(s,name):
    a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);depth=1;i=b+1
    while depth:
        if s[i]=='{':depth+=1
        if s[i]=='}':depth-=1
        i+=1
    return s[a:i]+'\n'
results=[]
for name,src in [('frozen32',BASE/'src'),('before05',prior),('hardened',work/'src')]:
    d=out/name;d.mkdir(exist_ok=True)
    for header in ['em_owner.h','em_shutdown.h']:
        shutil.copyfile(work/'src'/header,d/header)
    s=(src/'emount.c').read_text();(d/'tx_under_test.inc').write_text(function(s,'em_transmit('))
    s=(src/'em_uart.c').read_text()
    a=s.index('static volatile uint8_t  g_rx[');b=s.index('static void em_uart_sync',a)
    selected=s[a:b]+''.join(function(s,n) for n in ['SERCOM1_Handler(', 'em_uart_rx_reset(', 'em_uart_rx_len(', 'em_uart_rx_buf('])
    selected=selected.replace('(uint8_t)EMSERCOM->USART.DATA.reg','probe_data()')
    selected=selected.replace('g_rx[i] = EM_RX_POISON;', 'g_rx[i] = EM_RX_POISON; reset_probe(i);')
    (d/'uart_under_test.inc').write_text(selected)
    for kind,cases in [('tx',['high','pending','status','shutdown','failed','race-high','race-pending','race-status','race-shutdown','immutable','length','ack','during-copy','after-copy']),('uart',['reset','stuck','error','overflow'])]:
        exe=d/kind
        cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-variable','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(d),str(HERE/('test_'+kind+'.c'))]
        if kind=='tx':cmd+=[str(work/'src/em_owner.c')]
        subprocess.run(cmd+['-o',str(exe)],check=True)
        for case in cases:
            try:
                r=subprocess.run([str(exe),case],capture_output=True,text=True,timeout=1)
                code=r.returncode;detail=r.stdout.strip();assert not r.stderr,r.stderr
            except subprocess.TimeoutExpired:code=124;detail='bounded process timeout (unbounded frozen ISR)'
            if name=='hardened':assert code==0,(name,kind,case,code,detail)
            results.append(dict(source=name,kind=kind,case=case,exitCode=code,detail=detail))
# Actual explicit UART completion, disabled rejection and finite wait failure.
(out/'send_under_test.inc').write_text(function((work/'src/em_uart.c').read_text(),'em_uart_send('))
subprocess.run(['clang','-std=gnu99','-Wall','-Wextra','-Werror','-I'+str(out),str(HERE/'test_send.c'),'-o',str(out/'send')],check=True)
for case in ['disabled','success','dre-timeout','txc-timeout']:
    r=subprocess.run([str(out/'send'),case],capture_output=True,text=True,timeout=1)
    assert r.returncode==0 and not r.stderr,(case,r.stdout,r.stderr)
    results.append(dict(source='hardened',kind='send',case=case,exitCode=0,detail=r.stdout.strip()))
# Actual EIC pending predicate, including unrelated VD and disabled IRQ delivery.
s=(work/'src/em_eic.c').read_text()
eic='#include <stdint.h>\n#define EM_EXTINT_BODY_CS 2\nstruct {struct {uint32_t reg;} INTFLAG;} eic;\n#define EIC (&eic)\n'+function(s,'em_eic_receive_pending(')+'''int main(void) {for(unsigned i=0;i<65536;++i){eic.INTFLAG.reg=i;if(em_eic_receive_pending()!=!!(i&4))return 1;}return 0;}\n'''
(out/'eic.c').write_text(eic);subprocess.run(['clang',str(out/'eic.c'),'-o',str(out/'eic')],check=True);subprocess.run([str(out/'eic')],check=True)
# Whole actual transport + caller units against SAMD21 CMSIS, never execute ARM.
deps=ROOT/'tools/firmware-deps';arm=deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-gcc'
flags=['-mthumb','-mcpu=cortex-m0plus','-O2','-DNDEBUG','-DEA9_NO_LOG','-D__SAMD21E17A__','-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-Werror','-std=gnu99','-fstack-usage','-I'+str(work/'src'),'-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
for unit in ['emount','em_uart','em_eic']:
    subprocess.run([str(arm),*flags,'-c',str(work/'src'/f'{unit}.c'),'-o',str(out/f'{unit}.o')],check=True)
for unit in ['emount','em_uart','em_eic']:
    (out/f'{unit}.asm').write_text(subprocess.check_output([str(arm).replace('gcc','objdump'),'-dr',str(out/f'{unit}.o')],text=True))
report=dict(baseSHA256=m['imageSHA256'],hardwareAccess=False,cameraQualified=False,results=results,
    frozenFailingControls=sum(r['source']=='frozen32' and r['exitCode']!=0 for r in results),
    hardenedPassingCases=sum(r['source']=='hardened' and r['exitCode']==0 for r in results),eicFlagCombinations=65536,
    inputs={str(p.relative_to(ROOT)):sha(p) for p in HERE.iterdir() if p.is_file()},
    armStackUsage=(out/'emount.su').read_text())
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['results','inputs','armStackUsage']},indent=2))
