#!/usr/bin/env python3
"""Run actual watchdog C with inert registers; independently kill bad clear guards."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--candidate', type=Path)
args=p.parse_args()
assert __debug__, 'Assertions must remain enabled'
out=args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
module=(HERE/'watchdog.inc').read_text()
binding=None
if args.candidate:
    candidate=args.candidate.resolve()
    manifest=json.loads((candidate/'manifest.json').read_text())
    for name, pin in manifest['sources'].items():
        assert hashlib.sha256((candidate/name).read_bytes()).hexdigest()==pin, name
    image=candidate/'contax-zeiss-50-f1-4.bin'
    assert hashlib.sha256(image.read_bytes()).hexdigest()==manifest['imageSHA256']
    actual=(candidate/'src/startup_trace_flash.c').read_text()
    assert actual.count(module)==1, 'Candidate watchdog implementation differs'
    module=actual[actual.index(module):]
    binding={'manifestSHA256':hashlib.sha256((candidate/'manifest.json').read_bytes()).hexdigest(), 'imageSHA256':manifest['imageSHA256'], 'sources':manifest['sources']}
source=module.split('/* No C prologue,')[0]
variants={
    'proposal': source,
    'pet-while-busy': source.replace(' || WDT->STATUS.bit.SYNCBUSY', ''),
    'pet-frozen-tick': source.replace('(uint32_t)(now-last)<250u || ', ''),
    'ignore-crash-latch': source.replace('if (st_boot_record(cause)) st_halt();', '(void)st_boot_record(cause);'),
}
results={}
for name, code in variants.items():
    directory=out/name; directory.mkdir()
    (directory/'watchdog_host.inc').write_text(code)
    exe=directory/'probe'
    subprocess.run(['clang','-std=c11','-O1','-g','-UNDEBUG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(directory),str(HERE/'test_watchdog.c'),'-o',str(exe)],check=True,timeout=60)
    result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=20)
    assert (result.returncode==0)==(name=='proposal'), (name,result.stdout,result.stderr)
    results[name]={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
receipt={'offline':True,'hardwareAccess':False,'candidate':binding,'tests':results,'inputs':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in HERE.iterdir() if f.is_file()}}
(out/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({n:r['returncode'] for n,r in results.items()}))
