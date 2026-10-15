#!/usr/bin/env python3
"""Replay production protocol and motor/homing contracts before/after lane09.

--build is the completed run.py output. No device boundary is opened. Each
subprocess has a deadline. Release legacy-telemetry counters intentionally zero;
wire frames, command/control behavior, and live startup_trace remain checked.
"""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];LANES=HERE.parent
p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);a=p.parse_args();out=a.build.resolve();rows=[]
def run(cmd):
    r=subprocess.run(list(map(str,cmd)),capture_output=True,timeout=30)
    assert r.returncode==0,(cmd,r.stdout[-2000:],r.stderr[-2000:])
    assert not r.stderr or (str(cmd[0])=='clang' and b'reducing alignment' in r.stderr),(cmd,r.stderr)
    return r.stdout
apcases=[['short',i,n,pad] for i in (8,27,52) for n in (9,10) for pad in (0,32)] + [[x] for x in ('deferred','overflow','session','capture','metadata','opaque')]
wire={}
for label in ('before','after'):
    work=out/label;src=work/'src';dest=work/'regression'
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir()
    flags=['clang','-std=gnu99',('-O2' if label=='before' else '-Os'),'-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all']
    # Every actual UART send is serialized including its length, then compared
    # byte for byte across both builds, beyond the fixture's semantic asserts.
    shim=(work/'tools/hosttest/shim.c').read_text();shim=shim.replace('#include <stdint.h>','#include <stdint.h>\n#include <stdio.h>')
    needle='\tif (sent_n < MAX_SENT) {';assert shim.count(needle)==1
    shim=shim.replace(needle,'\textern void host_probe_send(const uint8_t *,uint16_t);\n\thost_probe_send(buf,len);\n\tprintf("WIRE %u:",len);\n\tfor(uint16_t i=0;i<len;i++)printf("%02x",buf[i]);\n\tputchar(10);\n'+needle)
    (dest/'shim.c').write_text(shim)
    fixture=(LANES/'07-aperture/test_aperture.c').read_text()
    # Raw diagnostic counters are not part of the release contract. The same
    # input and all real aperture/wire assertions are retained in both builds.
    fixture=fixture.replace('CHECK(em_m03_aperture==0x1600);', 'CHECK(em_m03_aperture=='+('0' if label=='after' else '0x1600')+');')
    (dest/'aperture.c').write_text(fixture)
    exe=dest/'wire';units=[src/(n+'.c') for n in ['emount','emount_packets','startup_trace','em_frame','em_owner','em_shutdown']]
    run([*flags,'-I'+str(src),'-I'+str(work/'tools/hosttest'),dest/'aperture.c',dest/'shim.c',*units,ROOT/'firmware/upstream-diagnostic/tests/trace_host.c','-o',exe])
    for case in apcases:
        result=run([exe,*case]);key=tuple(case)
        if label=='before':wire[key]=result
        else:assert result==wire[key],case
        rows.append(dict(source=label,suite='wire',case=case,bytes=len(result),sha256=hashlib.sha256(result).hexdigest()))
    # Reuse lane01's actual dispatcher IRQ-cut and immutable request cases.
    capshim=shim.replace('void delay_us(uint32_t us) { (void)us; }','void host_probe_delay(uint32_t);\nvoid delay_us(uint32_t us) {host_probe_delay(us);}')
    capshim=capshim.replace('uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{','extern int host_tx_fail,host_tx_fail_id;\nuint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{\n\tif(host_tx_fail || buf[5]==host_tx_fail_id)return 0;')
    (dest/'capture_shim.c').write_text(capshim)
    trace=(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c').read_text().replace('uint32_t st_lock(void) { return 0; }','extern int host_irq_mask;void host_irq_replay(void);\nuint32_t st_lock(void) {uint32_t old=host_irq_mask;host_irq_mask=1;return old;}').replace('void st_unlock(uint32_t k) { (void)k; }','void st_unlock(uint32_t k) {host_irq_mask=k;host_irq_replay();}')
    (dest/'capture_trace.c').write_text(trace)
    csrc=(src/'emount.c').read_text();anchor='\tfor (k = 0; k < sizeof(*out); k++) {';assert csrc.count(anchor)==1
    (dest/'capture_emount.c').write_text(csrc.replace(anchor,'\textern void host_copy_interrupt(void);host_copy_interrupt();\n'+anchor))
    exe=dest/'capture'
    run([*flags,'-DOWNED','-I'+str(src),'-I'+str(work/'tools/hosttest'),LANES/'01-capture/test_capture.c',dest/'capture_shim.c',dest/'capture_emount.c',*units[1:],dest/'capture_trace.c','-o',exe])
    cases=[[x] for x in ['focus-copy','session-queues','failed-init','failed-tail','failed-raw','baseline','immutable','first-wins','sequence','active','session','failed-shutdown']]
    cases += [['capture',cut,id,11] for cut in range(1,7) for id in (10,11,27,40,25,52)]
    cases += [['normal',cut,3,16] for cut in range(1,7)]
    cases += [['capture',4,52,n] for n in (9,17,64,255,256)]
    for case in cases:
        result=run([exe,*case]);key=('capture',*case)
        if label=='before':wire[key]=result
        else:assert result==wire[key],case
        rows.append(dict(source=label,suite='capture',case=case,sha256=hashlib.sha256(result).hexdigest()))
    exe=dest/'pure'
    run([*flags,'-I'+str(src),HERE/'test_pure.c',*[src/(x+'.c') for x in ('focus_dist','focus_map','focus_pred')],'-o',exe])
    result=run([exe]);key=('pure',)
    if label=='before':wire[key]=result
    else:assert result==wire[key]
    rows.append(dict(source=label,suite='pure',values=65536,predictorSamples=40000,sha256=hashlib.sha256(result).hexdigest()))
    # Actual servo C, fixed scripted encoder values; raw reads have no effect
    # on this synthetic sensor. Compare motor writes/endpoint/fault outcomes.
    for name in ('servo.h','motor.h','abs_encoder.h','delay.h'):shutil.copyfile(src/name,dest/name)
    shutil.copyfile(src/'startup_trace.h',dest/'startup_trace.h')
    shutil.copyfile(LANES/'06-motion/board_host.h',dest/'board.h')
    shutil.copyfile(src/'servo.c',dest/'servo.c');exe=dest/'servo'
    servo_fixture=(LANES/'06-motion/test_servo.c').read_text()
    servo_fixture=servo_fixture.replace('#include "servo.h"', '#include "servo.h"\n#include "startup_trace.h"\nstatic uint8_t fault; void st_inhibit_fault(uint8_t reason) { if(!fault)fault=reason; }')
    servo_fixture=servo_fixture.replace('int good=mode==5?', 'if(mode==0 && fault!=ST_SERVO_BUDGET)return 3;\n    if(mode==5 && fault!=ST_SERVO_RUNAWAY)return 4;\n    if(mode==6 && fault!=ST_SERVO_WRONG_WAY)return 5;\n    int good=mode==5?')
    (dest/'servo_fixture.c').write_text(servo_fixture)
    run([*flags,'-O2','-I'+str(dest),dest/'servo_fixture.c',dest/'servo.c','-o',exe])
    for case in ['freeze','stale','stationary','final-inhibit','retarget','runaway','wrongway']:
        result=run([exe,case]);key=('servo',case)
        if label=='before':wire[key]=result
        else:assert result==wire[key],case
        rows.append(dict(source=label,suite='servo',case=case,output=result.decode().strip()))
    # Extract complete homing policy and actual home function. Park has no
    # production callback in release; symbol absence is checked by run.py.
    text=(src/'main.c').read_text()
    constants='\n'.join(re.findall(r'^#define HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|TRACE_MS)\s+.*$',text,re.M))
    begin=text.index('/* Included in main.c after pump;');end=text.index('\n/* Park to infinity,',begin)
    (dest/'extracted.inc').write_text(constants+'\n'+text[begin:end])
    fixture=(LANES/'03-homing/test_home.c').read_text()
    faults=re.search(r'enum st_fault \{.*?\};',(src/'startup_trace.h').read_text(),re.S)[0]
    fixture=fixture.replace('#define SERVO_TRACE_N 24', faults+'\nstatic uint8_t fault; static void st_inhibit_fault(uint8_t reason) {if(!fault)fault=reason;}\n#define SERVO_TRACE_N 24')
    fixture=fixture.replace('int control=strstr(scenario,"control")!=NULL;', 'if(strstr(scenario,"timeout") || !strcmp(scenario,"frozen-clock"))assert(fault==ST_HOME_FAILED);\n    int control=strstr(scenario,"control")!=NULL;')
    begin=fixture.index('    if (strstr(scenario,"park")) {');end=fixture.index('    if (!strcmp(scenario,"wrap-control"))',begin)
    fixture=fixture[:begin]+fixture[end:]
    fixture=fixture.replace('static unsigned g_park_n, servo_calls;', 'static unsigned g_park_n, servo_calls;\nstatic uint32_t st_lock(void) { return 0; }\nstatic void st_unlock(uint32_t key) {(void)key;}')
    # Assert the only removed pre-home ADC operation directly.
    fixture=fixture.replace('static void vdd_read_burst(', 'static unsigned bursts;\nstatic void vdd_read_burst(').replace('*lo=*hi=3150;', 'bursts++; *lo=*hi=3150;',1)
    fixture=fixture.replace('int control=strstr(scenario,"control")!=NULL;', 'assert(bursts'+('==0' if label=='after' else '>=1')+' || !strcmp(scenario,"pre-stop") || !strcmp(scenario,"pre-shutdown"));\n    int control=strstr(scenario,"control")!=NULL;')
    (dest/'home.c').write_text(fixture);exe=dest/'home'
    # Before uses the same diagnostic macro? It had no gates; after uses it.
    run([*flags,'-Wno-unused-function','-Wno-unused-variable','-I'+str(dest),dest/'home.c','-o',exe])
    cases=['stationary-control','travel-control','wrap-control','move-control','pre-stop','stop','settle-stop','shutdown','settle-shutdown','pre-shutdown','session','settle-session','commit-stop','commit-session','drive-timeout','settle-timeout','frozen-clock','retry','budget']
    for case in cases:
        result=run([exe,case]);rows.append(dict(source=label,suite='home',case=case,output=result.decode().strip()))
report=dict(checks=len(rows),exactWireCases=len(apcases),wireOperandCases=65536,servoOutputComparisons=7,results=rows,hardwareAccess=False,cameraQualified=False)
(out/'regressions.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='results'},indent=2))
