#!/usr/bin/env python3
"""Reject optimized Python and mismatched candidate identities before replay."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
if not __debug__:raise SystemExit('Assertions required')
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('--build',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
build=a.build.resolve();out=a.output.resolve();assert out.is_relative_to(ROOT/'artifacts/private');out.mkdir(exist_ok=False)
master=ROOT/'scripts/test-upstream-reference.py';rows=[]
for case in ('optimized-python','wrong-manifest','wrong-image'):
 work=out/case;work.mkdir();candidate=work/'candidate';candidate.mkdir()
 m=(build/'manifest.json').read_bytes();image=bytearray((build/'contax-zeiss-50-f1-4.bin').read_bytes())
 if case=='wrong-manifest':
  doc=json.loads(m);doc['loaderVersion']=[9,9,9];m=json.dumps(doc).encode()
 if case=='wrong-image':image[128]^=1
 (candidate/'manifest.json').write_bytes(m);(candidate/'contax-zeiss-50-f1-4.bin').write_bytes(image)
 cmd=[sys.executable]+(['-O'] if case=='optimized-python' else [])+[str(master),'--build',str(candidate),'--output',str(work/'result')]
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
 assert r.returncode!=0 and not (work/'result/result.json').exists(),(case,r.stdout,r.stderr)
 assert ('Optimized Python disables required acceptance assertions' if case=='optimized-python' else 'AssertionError') in r.stderr
 rows.append({'case':case,'exitCode':r.returncode,'noAcceptanceReceipt':True})
report={'status':'passed-acceptance-identity-guards','masterSHA256':hashlib.sha256(master.read_bytes()).hexdigest(),'cases':rows,'hardwareReportsSent':0}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
