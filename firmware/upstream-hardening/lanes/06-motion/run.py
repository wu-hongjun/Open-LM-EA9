#!/usr/bin/env python3
"""Compile actual motion sources with host MMIO; all output stays in a new scratch dir."""
import argparse,hashlib,importlib.util,json,re,shutil,subprocess
from pathlib import Path
from apply import apply
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=ROOT/'firmware/upstream-diagnostic/build'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
out=args.output.resolve();out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((BASE/'manifest.json').read_text())
for name,digest in m['sources'].items():assert sha(BASE/name)==digest,name
assert sha(ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin')==m['imageSHA256']
work=out/'composed';shutil.copytree(BASE,work,ignore=shutil.ignore_patterns('*.o','*.elf','*.bin'))
for name in ['apply_frame.py','apply_tx.py','lanes/02-shutdown/apply.py','lanes/01-capture/apply.py','lanes/03-homing/apply.py','lanes/05-transport/apply.py']:
    spec=importlib.util.spec_from_file_location('overlay',ROOT/'firmware/upstream-hardening'/name);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.apply(work)
before=out/'before06';shutil.copytree(work/'src',before)
apply(work)
rows=[]
def run(exe,case,label,expected=None):
    r=subprocess.run([str(exe),*map(str,case)],capture_output=True,text=True,timeout=10)
    if expected is not None:assert r.returncode==expected,(label,case,r.returncode,r.stdout,r.stderr)
    rows.append(dict(source=label,case=case,exit=r.returncode,stdout=r.stdout.strip(),stderr=r.stderr[:700]))
    return r
for label,src in [('frozen32',BASE/'src'),('patched',work/'src')]:
    dest=out/label;dest.mkdir()
    for f in ['motor.h','servo.h','abs_encoder.h','delay.h']:shutil.copyfile(src/f,dest/f)
    shutil.copyfile(HERE/'board_host.h',dest/'board.h')
    (dest/'startup_trace.h').write_text('#include <stdint.h>\nuint32_t st_lock(void);void st_unlock(uint32_t);void host_wait(void);\n#define ST_WAIT_WHILE(c,f) host_wait()\n')
    # Pure observation hooks around each actual PORT/TCC register store; no motor semantics replaced.
    motor=(src/'motor.c').read_text()
    motor=re.sub(r'(?m)^(\s*)(PORT->[^;]+;|TCC0->[^;]+;)',lambda m:m[1]+'host_boundary();'+m[1]+m[2]+m[1]+'host_boundary();',motor)
    (dest/'motor_test.inc').write_text(motor)
    # Frozen code lacks inhibit API: harness supplies exact cutoff/latch, leaving frozen entry paths unguarded.
    if label=='frozen32':
        with (dest/'motor.h').open('a') as f:f.write('\nvoid motor_inhibit(void);uint8_t motor_is_inhibited(void);void motor_emergency_release(void);\n')
    flags=['clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(dest)]
    exe=dest/'motor'
    subprocess.run([*flags,*(['-DFROZEN'] if label=='frozen32' else []),str(HERE/'test_motor.c'),'-o',str(exe)],check=True,capture_output=True,text=True)
    for op in ['attach','drive','reverse','brake','release','init']:
        r=run(exe,[op,0],label,0);n=int(re.search(r'boundaries=(\d+)',r.stdout)[1])
        for cut in range(1,n+1):run(exe,[op,cut],label,0 if label=='patched' else None)
    for op in ['sticky','transient','seek-freeze','seek-duty']:run(exe,[op,0],label,0 if label=='patched' or op=='transient' else 1)
    shutil.copyfile(src/'servo.c',dest/'servo.c')
    exe=dest/'servo'
    subprocess.run([*flags,str(HERE/'test_servo.c'),str(dest/'servo.c'),'-o',str(exe)],check=True,capture_output=True,text=True)
    for case in ['freeze','stale','stationary','final-inhibit','retarget','runaway','wrongway']:run(exe,[case],label,0 if label=='patched' or case=='stationary' else 1)
    enc=(src/'abs_encoder.c').read_text();(dest/'encoder_test.inc').write_text(enc[enc.index('int32_t abs_encoder_track(void)'):])
    exe=dest/'encoder'
    subprocess.run([*flags,str(HERE/'test_encoder.c'),'-o',str(exe)],check=True,capture_output=True,text=True)
    for case in range(4):
        r=run(exe,[case],label,0 if label=='patched' or case>=2 else None)
        if label=='frozen32' and case<2:assert r.returncode and 'signed integer overflow' in r.stderr
def function(s,name):
    a=s.index(name);a=s.rfind('\n',0,a)+1;b=s.index('{',a);depth=1;i=b+1
    while depth:
        if s[i]=='{':depth+=1
        if s[i]=='}':depth-=1
        i+=1
    return s[a:i]+'\n'
for label,src in [('before06',before),('patched',work/'src')]:
    dest=out/(label+'-main');dest.mkdir()
    for f in ['servo.h','emount.h']:shutil.copyfile(src/f,dest/f)
    s=(src/'main.c').read_text()
    selected=''
    if label=='patched':selected+=function(s,'focus_invalid(void)')+function(s,'focus_event(uint8_t')
    selected+=function(s,'focus_abort(void)\n{')+function(s,'focus_exec(const struct em_focus_cmd *c'+(', uint32_t session' if label=='patched' else '')+')\n{')
    (dest/'main_test.inc').write_text(selected)
    exe=dest/'main'
    flags=['clang','-std=c11','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(dest)]
    subprocess.run([*flags,*(['-DFROZEN'] if label=='before06' else []),str(HERE/'test_main.c'),'-o',str(exe)],check=True)
    for case in range(9):run(exe,[case],label,0 if label=='patched' or case in [0,6] else 1)
    # Execute the exact final readiness commit with an ISR request at the publication boundary.
    mark=s.index('\tg_homed = 1;',s.index('static void motor_home(void)'))
    if label=='patched':
        a=s.rfind('\t{',0,mark);b=s.index('\n\t}',mark)+3
    else:
        a=s.rfind('\tif (home_cancel_requested())',0,mark);b=s.index('\n',s.index('g_home_state = HOME_READY;',mark))
    commit=s[a:b].replace('g_homed = 1;', 'host_boundary(); g_homed = 1;')
    (dest/'home_commit.inc').write_text(commit)
    exe=dest/'home-commit'
    subprocess.run([*flags,'-Wno-unused-function',str(HERE/'test_home_commit.c'),'-o',str(exe)],check=True)
    run(exe,[],label,0 if label=='patched' else 1)
    # Reuse lane05 source-bound RX handler fixture, adding the cutoff assertion.
    u=(src/'em_uart.c').read_text();a=u.index('static volatile uint8_t  g_rx[');b=u.index('static void em_uart_sync',a)
    selected=u[a:b]+''.join(function(u,n) for n in ['SERCOM1_Handler(', 'em_uart_rx_reset(', 'em_uart_rx_len(', 'em_uart_rx_buf('])
    selected=selected.replace('(uint8_t)EMSERCOM->USART.DATA.reg','probe_data()').replace('g_rx[i] = EM_RX_POISON;', 'g_rx[i] = EM_RX_POISON; reset_probe(i);')
    (dest/'uart_under_test.inc').write_text(selected)
    h=(HERE.parent/'05-transport/test_uart.c').read_text().replace('#include "uart_under_test.inc"','static unsigned inhibited;\nvoid motor_inhibit(void) { inhibited++; }\n#include "uart_under_test.inc"')
    h=h.replace('CHECK(reads==4);','CHECK(reads==4 && inhibited==1);').replace('puts("PASS");','if(strcmp(argv[1],"stuck")) CHECK(!inhibited);\n    puts("PASS");')
    (dest/'uart.c').write_text(h);exe=dest/'uart'
    subprocess.run([*flags,'-Wno-unused-function','-Wno-unused-variable',str(dest/'uart.c'),'-o',str(exe)],check=True)
    for case in ['stuck','error','overflow','reset']:run(exe,[case],label,1 if label=='before06' and case=='stuck' else 0)
# Compile entire actual ARM motion, encoder, UART and main units; do not execute.
deps=ROOT/'tools/firmware-deps';arm=deps/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-gcc'
flags=['-mthumb','-mcpu=cortex-m0plus','-Os','-DNDEBUG','-DEA9_NO_LOG','-D__SAMD21E17A__','-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-Werror','-std=gnu99','-fstack-usage','-I'+str(work/'src'),'-I'+str(deps/'samd21-dfp-2/samd21a/include'),'-I'+str(deps/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
for unit in ['motor','servo','abs_encoder','em_uart','main']:
    subprocess.run([str(arm),*flags,'-c',str(work/'src'/f'{unit}.c'),'-o',str(out/f'{unit}.o')],check=True)
report=dict(frozenImageSHA256=m['imageSHA256'],checks=len(rows),frozenNegativeControls=sum(r['source']=='frozen32' and r['exit']!=0 for r in rows),results=rows,hardwareAccess=False,cameraQualified=False,inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py','.c','.h']},patchedSources={n:sha(work/'src'/n) for n in ['motor.c','servo.c','abs_encoder.c']})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['results','inputs','patchedSources']},indent=2))
