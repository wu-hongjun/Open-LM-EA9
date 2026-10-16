#!/usr/bin/env python3
"""Exercise the v3 CLI trust boundary using only generated synthetic flash.

Each case runs in an isolated disposable repository. Successful decoding cannot
occur before candidate, manifest, immutable prefix, and native backup checks.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[4]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
rows=[]
with tempfile.TemporaryDirectory(prefix='synthetic-registry-',dir=Path(__file__).parent) as tmp:
    repo=Path(tmp)
    scripts=repo/'scripts';scripts.mkdir()
    for name in ('decode-startup-diagnostics.py','startup_diagnostic_registry.py','startup_diagnostic_cohorts.py','startup_diagnostic_v3.py'):
        shutil.copyfile(ROOT/'scripts'/name,scripts/name)
    target=repo/'firmware/candidates/3.7.0';target.mkdir(parents=True)
    image=target/'contax-zeiss-50-f1-4.bin'
    manifest=image.with_suffix('.manifest.json')
    registry=target.parent/'diagnostic-registry.json'
    original_image=(ROOT/image.relative_to(repo)).read_bytes()
    original_manifest=(ROOT/manifest.relative_to(repo)).read_bytes()
    original_registry=(ROOT/registry.relative_to(repo)).read_bytes()
    assert hashlib.sha256(original_image).hexdigest()=='6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5'
    assert hashlib.sha256(original_manifest).hexdigest()=='15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b'
    flash=bytearray(b'\xff'*0x20000)
    flash[0x4000:0x4003]=bytes((3,7,0));flash[0x5000:0xa000]=original_image
    native=repo/'synthetic.ea9backup';native.mkdir()
    source=native/'flash.bin'
    def reset():
        image.write_bytes(original_image);manifest.write_bytes(original_manifest);registry.write_bytes(original_registry)
        source.write_bytes(flash)
        (native/'manifest.json').write_text(json.dumps({'flashReadPasses':2,'auxiliaryReadPasses':2,
            'files':{'flash.bin':{'bytes':len(flash),'sha256':hashlib.sha256(flash).hexdigest()}}}))
    def check(name,accepted=False,path=None):
        proc=subprocess.run([sys.executable,scripts/'decode-startup-diagnostics.py',path or source],capture_output=True,text=True,timeout=20)
        passed=(proc.returncode==0)==accepted
        if accepted and proc.returncode==0:
            result=json.loads(proc.stdout)
            passed=passed and result['firmwareVersion']=='3.7.0' and not result['installationVerificationPerformed'] and result['hardwareReportsSent']==0
        if not accepted: passed=passed and proc.stdout==''
        rows.append({'case':name,'passed':passed,'expectedAccepted':accepted})
    reset();check('pristine-synthetic-v3',True)
    check('matching-native-manifest',True,native)
    # Arbitrary log tail remains allowed; invalid local records stay invalid.
    b=bytearray(flash);b[0x9c00]=0;source.write_bytes(b);check('mutable-diagnostic-tail',True)
    for offset in (0x5000,0x9bff):
        reset();b=bytearray(flash);b[offset]^=1;source.write_bytes(b);check(f'immutable-prefix-{offset}')
    for key in ('imageSHA256','manifestSHA256','immutablePrefixSHA256'):
        reset();j=json.loads(original_registry);j['versions']['3.7.0'][key]='0'*64;registry.write_text(json.dumps(j));check('registry-'+key)
    reset();registry.write_text(' '*65537);check('registry-size-bound')
    reset();j=json.loads(original_registry);del j['versions']['3.7.0'];registry.write_text(json.dumps(j));check('missing-registry-version')
    reset();j=json.loads(original_registry);j['format']='unknown';registry.write_text(json.dumps(j));check('registry-format')
    reset();manifest.write_bytes(original_manifest+b'\n');check('manifest-byte-pin')
    for field,value in (('loaderVersion',[3,6,0]),('diagnosticRange',[0x9c40,0xa000]),('imageSHA256','0'*64)):
        reset();j=json.loads(original_manifest);j[field]=value;manifest.write_text(json.dumps(j))
        # Repair only manifest digest: independent version/range/image gates remain.
        reg=json.loads(original_registry);reg['versions']['3.7.0']['manifestSHA256']=hashlib.sha256(manifest.read_bytes()).hexdigest();registry.write_text(json.dumps(reg));check('descriptor-'+field)
    for offset in (0,0x4bff,0x4c00,0x4fff):
        reset();b=bytearray(original_image);b[offset]^=1;image.write_bytes(b);check(f'candidate-tamper-{offset}')
    reset();image.write_bytes(original_image[:-1]);check('candidate-length')
    for field,value in (('flashReadPasses',1),('auxiliaryReadPasses',1)):
        reset();j=json.loads((native/'manifest.json').read_text());j[field]=value;(native/'manifest.json').write_text(json.dumps(j));check('native-'+field,path=native)
    for field,value in (('bytes',0),('sha256','0'*64)):
        reset();j=json.loads((native/'manifest.json').read_text());j['files']['flash.bin'][field]=value;(native/'manifest.json').write_text(json.dumps(j));check('native-'+field,path=native)
    for length in (0,0x1ffff,0x20001):
        reset();source.write_bytes(b'\xff'*length);check(f'flash-size-{length}')
report={'checks':len(rows),'passed':sum(r['passed'] for r in rows),'cases':rows,'syntheticDataOnly':True,'hardwareReportsSent':0}
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
assert all(r['passed'] for r in rows),[r for r in rows if not r['passed']]
