#!/usr/bin/env python3
"""Materialize and build upstream C startup diagnostic 3.2; never opens USB."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references/upstream/weiziqian/E-mount-impl-on-Techart-EA9'
LANE=ROOT/'firmware/upstream-diagnostic'
WORK=LANE/'build'
DEPS=ROOT/'tools/firmware-deps'
ARM=str(DEPS/'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
sha=lambda b:hashlib.sha256(b).hexdigest()
catalog={}
prefix='upstream/weiziqian/E-mount-impl-on-Techart-EA9/'
for line in (ROOT/'references/checksums.sha256').read_text().splitlines():
    h,n=line.split(maxsplit=1)
    if n.startswith(prefix): catalog[n[len(prefix):]]=h
assert catalog
for n,h in catalog.items():
    assert sha((REF/n).read_bytes())==h,n
WORK.mkdir(parents=True,exist_ok=True)
for n in catalog:
    dst=WORK/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REF/n,dst)
for src in (LANE/'src').glob('*.[ch]'):
    shutil.copyfile(src,WORK/'src'/src.name)

def replace(name,old,new,count=1):
    p=WORK/name;s=p.read_text();assert s.count(old)==count,(name,old,s.count(old))
    p.write_text(s.replace(old,new))

replace('src/startup_samd21.c','#include "samd21.h"','#include "sam.h"')
replace('src/startup_samd21.c','.pfnNMI_Handler','.pfnNonMaskableInt_Handler')
replace('src/startup_samd21.c','.pfnSVC_Handler','.pfnSVCall_Handler')
replace('src/system_samd21.c','#include "samd21.h"','#include "sam.h"')
replace('src/ea9.ld','LENGTH = 0x0001b000','LENGTH = 0x00004c00')
replace('src/emount.h','0x59u','0x32u')
replace('src/emount.h','0x11C0u','0x1100u',3)
replace('src/emount.h','50496u','234u')
replace('src/emount.h','{ 0xD1, 0xD0, 0xD5, 0xE8, 0xE9, 0xEF }','{ 0xD2, 0x5A, 0xC8, 0xE1, 0xE2, 0xEA }')
replace('tools/hosttest/test_emount.c','{ 0x16, EM_APERTURE_NOW }','{ 0x10, EM_APERTURE_NOW }')

for name,reason,expected in [('clock', 'ST_CLOCK_WAIT',3),('abs_encoder','ST_ENCODER_WAIT',5),
                             ('vdd','ST_ADC_WAIT',3),('motor','ST_MOTOR_WAIT',4),
                             ('em_uart','ST_UART_WAIT',4),('em_eic','ST_EIC_WAIT',3)]:
    file=WORK/'src'/f'{name}.c';s=file.read_text()
    s=s.replace('#include "board.h"','#include "board.h"\n#include "startup_trace.h"')
    # Only empty hardware poll loops; servo/control algorithms are untouched.
    s,n=re.subn(r'while \(([^\n]+)\) \{\n\t+\}',lambda m:'ST_WAIT_WHILE('+m[1]+', '+reason+');',s)
    assert n==expected,(name,n,expected)
    file.write_text(s)

replace('src/delay.c','#include "board.h"','#include "board.h"\n#include "startup_trace.h"')
replace('src/delay.c','\twhile ((uint32_t)(g_millis - start) < ms) {\n\t}',
        '\tuint32_t budget=268435456u;\n\twhile ((uint32_t)(g_millis - start) < ms) {\n\t\tif (--budget==0) st_fail(ST_TICK_WAIT);\n\t}')
replace('src/delay.c','\twhile (elapsed < target) {',
        '\tuint32_t budget=4194304u;\n\twhile (elapsed < target) {\n\t\tif (--budget==0) st_fail(ST_TICK_WAIT);')

replace('src/main.c','#include "board.h"','#include "board.h"\n#include "startup_trace.h"')
replace('src/main.c','\tboard_init_pins();','\tboard_init_pins();\n\tst_init();\n\tst_note(ST_STAGE,ST_MAIN,0,0,0,0,0);')
for call,stage in [('clock_init();','ST_CLOCK'),('delay_init();','ST_TICK'),
                   ('abs_encoder_init();','ST_ENCODER'),('vdd_init();','ST_ADC'),
                   ('motor_init();','ST_MOTOR'),('em_init();','ST_BUS_READY'),
                   ('abs_encoder_track_reset();','ST_REFERENCE')]:
    # The reference-reset call also occurs in other functions: instrument only main.
    p=WORK/'src/main.c';s=p.read_text();i=s.index('int main(void)');head,main=s[:i],s[i:]
    assert main.count('\t'+call)==1,call
    stamp='0' if stage=='ST_CLOCK' else 'millis()'
    main=main.replace('\t'+call,'\t'+call+'\n\tst_note(ST_STAGE,'+stage+',0,0,0,0,'+stamp+');',1)
    p.write_text(head+main)
replace('src/main.c','\tem_uart_disable();','\tem_uart_disable();\n\tst_note(ST_SHUTDOWN,0,0,0,0,0,millis());\n\tst_flush(1,millis(),em_rx_bytes,(uint16_t)em_rx_errors,em_rx_status,0);')
replace('src/main.c','\t\tem_poll();\n\n\t\t/* If the handshake',
        '\t\tem_poll();\n\t\t/* Persist once only after an incomplete handshake goes quiet. */\n'
        '\t\tstatic uint8_t startup_saved;\n'
        '\t\tif (!startup_saved && !em_handshake_done && millis()>=2000u\n'
        '\t\t    && (uint32_t)(millis()-em_t_last_frame)>=100u\n'
        '\t\t    && !em_pin_level(EM_PIN_BODY_CS)) {\n'
        '\t\t\tstartup_saved=1;\n'
        '\t\t\tst_flush(1,millis(),em_rx_bytes,(uint16_t)em_rx_errors,em_rx_status,0);\n'
        '\t\t}\n\n\t\t/* If the handshake')

replace('src/emount.c','#include "board.h"','#include "board.h"\n#include "startup_trace.h"')
replace('src/emount.c','\tem_cs_edges++;','\tem_cs_edges++;\n\tst_note(ST_CS,(uint8_t)level,0,0,0,0,millis());')
replace('src/emount.c','\tem_frames_rx++;','\tem_frames_rx++;\n\tst_note(ST_RX,rx[5],rx[3],rx[4],n,n>7 ? (uint16_t)(rx[6]|((uint16_t)rx[7]<<8)) : 0,millis());')
replace('src/emount.c','\t\t\tem_bad_frames++;','\t\t\tem_bad_frames++;\n\t\t\tst_note(ST_BAD_RX,0,0,0,n,0,millis());')
replace('src/emount.c','\tem_frames_tx++;','\tem_frames_tx++;\n\tst_note(ST_TX,frame[5],frame[3],frame[4],len,0,millis());')
replace('src/emount.c','\t\t\tem_handshake_done = 1;',
        '\t\t\tem_handshake_done = 1;\n\t\t\tst_note(ST_HANDSHAKE,id,0,0,0,0,millis());')
replace('src/emount.c','\tem_uart_init();','\tem_uart_init();\n\tst_note(ST_STAGE,ST_UART,0,0,0,0,millis());\n\tst_note(ST_STAGE,ST_WAIT_RISE,0,0,0,0,millis());')
replace('src/emount.c','\t\twhile (!em_pin_level(EM_PIN_BODY_CS)) {',
        '\t\tuint32_t budget=268435456u;\n\t\twhile (!em_pin_level(EM_PIN_BODY_CS)) {\n'
        '\t\t\tif (--budget==0 || (uint32_t)(millis()-t0)>=8000u) st_fail(ST_CS_RISE_WAIT);')
replace('src/emount.c','\t\t\tdiag_tally_mark(DIAG_MARK_NOBODY, 0);',
        '\t\t\tdiag_tally_mark(DIAG_MARK_NOBODY, 0);\n'
        '\t\t\tst_flush(1,millis(),em_rx_bytes,(uint16_t)em_rx_errors,em_rx_status,0);')
replace('src/emount.c','\tem_uart_rx_reset();\n\tem_t_cs_first_high = millis();',
        '\t/* RX IRQ may have delivered the opener before this polling read. */\n'
        '\tuint32_t rx_key=st_lock();\n'
        '\tif (st_preserve_first_window(em_uart_rx_buf(),em_uart_rx_len())) {\n'
        '\t\tst_note(ST_WINDOW_PRESERVED,0,0,0,em_uart_rx_len(),0,millis());\n'
        '\t} else {\n\t\tem_uart_rx_reset();\n\t}\n\tst_unlock(rx_key);\n'
        '\tem_t_cs_first_high = millis();\n'
        '\tst_note(ST_STAGE,ST_WAIT_FALL,0,0,0,0,millis());')
replace('src/emount.c','\twhile (em_pin_level(EM_PIN_BODY_CS)) {\n\t}',
        '\tuint32_t close_budget=268435456u;\n\twhile (em_pin_level(EM_PIN_BODY_CS)) {\n'
        '\t\tif (--close_budget==0 || (uint32_t)(millis()-em_t_cs_first_high)>=8000u) st_fail(ST_CS_FALL_WAIT);\n\t}')
replace('src/emount.c','\tem_eic_init(on_cs_edge, on_vd_edge);',
        '\tem_eic_init(on_cs_edge, on_vd_edge);\n\tst_note(ST_STAGE,ST_EIC,0,0,0,0,millis());')

# Read actual bus levels where they are configured; 255 means unavailable at boot.
for name in ('main','emount'):
    p=WORK/'src'/f'{name}.c';s=p.read_text()
    s=s.replace('em_rx_status,0);','em_rx_status,(uint8_t)(em_pin_level(EM_PIN_BODY_CS)|(em_pin_level(EM_PIN_BODY_VD)<<1)));')
    p.write_text(s)

patch=[]
for n in catalog:
    if n.endswith(('.c','.h','.ld')):
        before=(REF/n).read_text();after=(WORK/n).read_text()
        if before!=after:
            patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='upstream/'+n,tofile='diagnostic/'+n,n=0))
(WORK/'upstream-changes.patch').write_text(''.join(patch))

sources='startup_samd21 system_samd21 board clock delay emount emount_packets em_uart em_eic motor abs_encoder servo focus_map focus_dist focus_pred vdd main startup_trace startup_trace_flash'.split()
flags=['-mthumb','-mcpu=cortex-m0plus','-O2','-DNDEBUG','-DEA9_NO_LOG','-D__SAMD21E17A__',
       '-ffunction-sections','-fdata-sections','-fno-common','-Wall','-Wextra','-Werror','-std=gnu99','-g']
inc=['-Isrc','-I'+str(DEPS/'samd21-dfp-2/samd21a/include'),'-I'+str(DEPS/'CMSIS_5-5.9.0/CMSIS/Core/Include')]
objects=[]
for name in sources:
    obj=WORK/(name+'.o');objects.append(str(obj))
    subprocess.run([ARM+'gcc',*flags,*inc,'-c','src/'+name+'.c','-o',str(obj)],cwd=WORK,check=True)
elf=WORK/'diagnostic.elf'
subprocess.run([ARM+'gcc',*objects,'-mthumb','-mcpu=cortex-m0plus','-Tsrc/ea9.ld',
               '-Wl,--gc-sections,-Map='+str(WORK/'diagnostic.map'),'--specs=nano.specs','--specs=nosys.specs','-o',str(elf)],cwd=WORK,check=True)
symbols={}
for line in subprocess.check_output([ARM+'nm',str(elf)],text=True).splitlines():
    q=line.split()
    if len(q)==3:symbols[q[2]]=int(q[0],16)
end=symbols['_etext']+symbols['_erelocate']-symbols['_srelocate']
assert end<=0x9c00 and symbols['_estack']<=0x20004000
assert not any(n.startswith(('diag_','trail_','factory_servo_','em_arb_')) for n in symbols)
subprocess.run([ARM+'objcopy','-O','binary','--gap-fill=0xff',str(elf),str(WORK/'diagnostic.bin')],check=True)
raw=(WORK/'diagnostic.bin').read_bytes();assert len(raw)<=0x4c00
data=raw+bytes([255])*(0x5000-len(raw));(WORK/'bounded.bin').write_bytes(data)
published=ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin'
if published.exists() and published.read_bytes()!=data:
    raise SystemExit('Rebuild differs from pinned 3.2.0; preserve the release and prepare a new reviewed version.')
assert data[0x4c00:]==bytes([255])*1024
assert int.from_bytes(data[:4],'little')==symbols['_estack']
assert int.from_bytes(data[4:8],'little')==symbols['Reset_Handler']|1
manifest={'upstreamCommit':'d52ed06cc449918f938e0695fbf29a0c4141f2b2',
          'status':'offline-startup-diagnostic-camera-unqualified','loaderVersion':[3,2,0],
          'imageBytes':len(data),'imageSHA256':sha(data),'rawBytes':len(raw),
          'codeAndDataEnd':end,'codeMarginBeforeDiagnostics':0x9c00-end,
          'staticRAMBytes':symbols['_ezero']-0x20000000,
          'reservedStackBytes':symbols['_estack']-symbols['_sstack'],
          'diagnosticRange':[0x9c00,0xa000],'diagnosticPageBytes':64,'diagnosticPages':16,
          'diagnosticErases':0,'lensID':234,'nominalApertureAV':4352,
          'cameraQualified':False,'hardwareReportsSent':0,
          'sources':{str(p.relative_to(WORK)):sha(p.read_bytes()) for p in sorted((WORK/'src').glob('*.[ch]'))},
          'upstreamPatchSHA256':sha((WORK/'upstream-changes.patch').read_bytes()),'flags':flags}
(WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k not in ('sources','flags')},indent=2))
