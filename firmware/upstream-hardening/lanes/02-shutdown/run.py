#!/usr/bin/env python3
"""Offline bounded sanitized production dispatcher shutdown regressions."""
import argparse,hashlib,importlib.util,json,pathlib,subprocess,shutil
L=pathlib.Path(__file__).resolve().parent
R=L.parents[3]
B=R/'firmware/upstream-diagnostic/build'
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((B/'manifest.json').read_text())
assert manifest['imageSHA256']=='e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df'
for name,digest in manifest['sources'].items(): assert sha(B/name)==digest,name
spec=importlib.util.spec_from_file_location('overlay',L/'apply.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
shim=(B/'tools/hosttest/shim.c').read_text().replace('void delay_us(uint32_t us) { (void)us; }','extern void shutdown_host_delay(uint32_t);\nextern void shutdown_host_tx(void);\nvoid delay_us(uint32_t us) { shutdown_host_delay(us); }')
shim=shim.replace('void em_uart_send(const uint8_t *buf, uint16_t len)\n{','void em_uart_send(const uint8_t *buf, uint16_t len)\n{\n    shutdown_host_tx();')
(out/'shim.c').write_text(shim)
cases=['valid-control','plain','normal-overwrite','init-overwrite','repeat-pending','length9','length64','oversize65','bad-checksum','bad-terminator','truncated','disabled','park-reentry','pending-command','lead','gap','during-status-tx','off-session','repeat-off','padding','park-unresponsive']
results=[]
for label in ['frozen32','proposed']:
    work=out/label;work.mkdir()
    source=(B/'src/emount.c').read_text()
    if label=='proposed':source=m.apply_source(source)
    (work/'emount-under-test.c').write_text(source)
    (work/'emount.h').write_text(m.apply_header((B/'src/emount.h').read_text()) if label=='proposed' else (B/'src/emount.h').read_text())
    exe=work/'test'
    command=['clang','-std=gnu99','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-DST_HOST','-DEA9_NO_LOG',f'-I{work}',f'-I{L}',f'-I{R}/firmware/upstream-hardening/src',f'-I{B}/src',f'-I{B}/tools/hosttest',str(L/'test_shutdown.c'),str(out/'shim.c'),str(B/'src/emount_packets.c'),str(B/'src/startup_trace.c'),str(R/'firmware/upstream-diagnostic/tests/trace_host.c'),'-o',str(exe)]
    if label=='proposed': command+=['-DPROPOSED',str(L/'em_shutdown.c'),str(R/'firmware/upstream-hardening/src/em_frame.c')]
    subprocess.run(command,check=True,capture_output=True,text=True,timeout=60)
    matrix=[[case] for case in cases]+[['plain',str(n),str(seq)] for n in [9,11,16,19,27,32,48,64] for seq in [0,1,0x71,0xff]]
    for args in matrix:
        case='/'.join(args)
        try:
            r=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=1 if case=='park-unresponsive' else 5)
        except subprocess.TimeoutExpired:
            assert label=='frozen32' and case=='park-unresponsive'
            r=subprocess.CompletedProcess([str(exe),*args],1,'Finite harness timeout: legacy park callback never returns.','')
        assert not r.stderr,(label,case,r.stderr)
        assert r.returncode in [0,1],(label,case,r.returncode)
        expected=0 if label=='proposed' or args[0] in ['valid-control','plain','length9','padding'] and (len(args)==1 or int(args[1])<=16) else 1
        assert r.returncode==expected,(label,case,expected,r.stdout)
        results.append(dict(source=label,case=case,exit=r.returncode,stdout=r.stdout.strip()))
report=dict(status='offline-proposal-only',cases=results,frozenFailures=[r['case'] for r in results if r['source']=='frozen32' and r['exit']],hardwareReportsSent=0,publishedFirmwareChanged=False,cameraQualified=False,sourceSHA256={str(p.relative_to(R)):sha(p) for p in [L/'apply.py',L/'run.py',L/'em_shutdown.c',L/'em_shutdown.h',L/'test_shutdown.c',B/'src/emount.c',B/'src/main.c',B/'tools/hosttest/shim.c']},limits='Actual dispatcher and private queue counters; scripted CS/VD at delay/UART boundaries, immediate UART completion, park/powerdown callback cuts. No real IRQ/peripheral/camera timing. main/home/servo cancellation belongs lane03; TX-success signaling belongs transport integration.')
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
