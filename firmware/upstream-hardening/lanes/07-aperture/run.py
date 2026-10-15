#!/usr/bin/env python3
"""Compile actual dispatcher and packet table offline; never open hardware."""
import argparse,hashlib,json,runpy,shutil,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=ROOT/'firmware/upstream-diagnostic/build';HARD=ROOT/'firmware/upstream-hardening'
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();out.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((BASE/'manifest.json').read_text())
assert m['imageSHA256']=='e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df'
for n,h in m['sources'].items():assert sha(BASE/n)==h,n
cases=[['short',str(i),str(n),str(pad)] for i in (8,0x1b,0x34) for n in (9,10) for pad in (0,32)]
cases += [[x] for x in ('deferred','overflow','session','capture','metadata','opaque')]
results=[]
for label in ('frozen32','composed','aperture'):
    work=out/label;shutil.copytree(BASE/'src',work/'src');shutil.copytree(BASE/'tools/hosttest',work/'tools/hosttest')
    if label!='frozen32':
        for app in ('apply_frame.py','apply_tx.py','lanes/02-shutdown/apply.py','lanes/01-capture/apply.py','lanes/05-transport/apply.py'):
            runpy.run_path(str(HARD/app))['apply'](work)
    if label=='aperture':runpy.run_path(str(HERE/'apply.py'))['apply'](work)
    shim=work/'tools/hosttest/shim.c';s=shim.read_text()
    needle='\tif (sent_n < MAX_SENT) {'
    assert s.count(needle)==1
    s=s.replace(needle,'\textern void host_probe_send(const uint8_t *, uint16_t);\n\thost_probe_send(buf,len);\n'+needle)
    shim.write_text(s)
    src=work/'src';exe=work/'probe'
    units=[src/x for x in ('emount.c','emount_packets.c','startup_trace.c')]
    if label!='frozen32':units += [src/x for x in ('em_frame.c','em_owner.c','em_shutdown.c')]
    cmd=['clang','-std=gnu99','-O1','-Wall','-Wextra','-Werror','-DST_HOST','-DEA9_NO_LOG','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(work/'tools/hosttest'),str(HERE/'test_aperture.c'),str(shim),*map(str,units),str(ROOT/'firmware/upstream-diagnostic/tests/trace_host.c'),'-o',str(exe)]
    r=subprocess.run(cmd,text=True,capture_output=True);assert r.returncode==0,r.stderr
    for case in cases:
        r=subprocess.run([str(exe),*case],text=True,capture_output=True,timeout=10)
        expected=0 if label=='aperture' or case[0] in ('metadata','opaque') else 1
        assert r.returncode==expected,(label,case,r.returncode,r.stdout,r.stderr)
        assert not r.stderr,r.stderr
        results.append(dict(source=label,case=case,exitCode=r.returncode,result=r.stdout.strip()))
report=dict(frozenImageSHA256=m['imageSHA256'],casesPerSource=len(cases),results=results,hardwareAccess=False,cameraQualified=False,inputs={str(f.relative_to(ROOT)):sha(f) for f in HERE.iterdir() if f.is_file()})
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('results','inputs')},indent=2))
