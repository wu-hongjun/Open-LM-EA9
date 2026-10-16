#!/usr/bin/env python3
"""Exercise lane34 production calls with actual lane35 storage and lane33 motion."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from apply import apply
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path);a=p.parse_args();out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
    base=ROOT/'artifacts/private/handoff36-repeat';source=a.source.resolve() if a.source else base
    assert source.is_relative_to(ROOT/'artifacts/private')
    core=source/'src' if a.source else HERE.parent/'35-targeted-trace';motion=source/'src' if a.source else HERE.parent/'33-motion-tracing'
    if a.source:
        expected=json.loads((HERE/'results.json').read_text())['proposalEmountSHA256']
        assert sha(source/'src/emount.c')==expected, 'candidate emount differs from tested proposal'
        if (source/'manifest.json').exists():
            manifest=json.loads((source/'manifest.json').read_text())
            for n,h in manifest['sources'].items():assert sha(source/n)==h,n
    pins={str(p.relative_to(ROOT)):sha(p) for p in [core/'startup_trace.c',core/'startup_trace.h',core/'trace_format.h',motion/'motion_trace.c',motion/'motion_trace.h',source/'src/emount.c',source/'src/em_owner.c',source/'src/em_frame.c',source/'src/em_shutdown.c',HERE/'apply.py',HERE/'trace.inc',HERE/'test_retention.c']}
    results={}
    for variant in ['proposal','unfiltered-mutant']:
        work=out/variant;shutil.copytree(source/'src',work/'src');src=work/'src'
        if not a.source:apply(src)
        for n in ['startup_trace.c','startup_trace.h','trace_format.h']:shutil.copyfile(core/n,src/n)
        for n in ['motion_trace.c','motion_trace.h']:shutil.copyfile(motion/n,src/n)
        if variant=='unfiltered-mutant':
            q=src/'startup_trace.c';s=q.read_text();old='''
        || ((kind==ST_OWNER_CS || kind==ST_OWNER_PHASE) && !(cls&1u))
        || ((kind==ST_TX_START || kind==ST_TX_RETURN) && !(cls&6u))''';assert s.count(old)==1;q.write_text(s.replace(old,''))
        shim=(base/'tools/hosttest/shim.c').read_text().replace('uint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{', 'void host_probe_send(const uint8_t *,uint16_t);\nuint8_t em_uart_send(const uint8_t *buf, uint16_t len)\n{\n host_probe_send(buf,len);');(work/'shim.c').write_text(shim)
        cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(base/'tools/hosttest'),HERE/'test_retention.c',work/'shim.c',*[src/(n+'.c') for n in ['emount','emount_packets','em_frame','em_owner','em_shutdown','startup_trace','motion_trace']],'-o',work/'probe']
        r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=40);assert r.returncode==0,r.stderr
        r=subprocess.run([str(work/'probe')],capture_output=True,text=True,timeout=10)
        assert r.returncode==(0 if variant=='proposal' else 1),(variant,r.returncode,r.stdout,r.stderr)
        assert 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr,r.stderr
        results[variant]={'exit':r.returncode,'output':r.stdout.strip(),'assertion':r.stderr.strip()}
    for name,h in pins.items():assert sha(ROOT/name)==h,name
    report={'sourceHashes':pins,'results':results,'scope':'production emount + real focused ring/writer + real motion storage; synthetic frames only','hardwareAccess':False}
    (HERE/'retention-results.json').write_text(json.dumps(report,indent=2)+'\n');(out/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(results,indent=2))
if __name__=='__main__':main()
