#!/usr/bin/env python3
"""Reuse pinned regression fixtures with explicit 3.6 identity/host-ABI bindings.

Only private runner copies change. Test cases, expected outcomes and production
source remain intact. This avoids copying the same regression suite per release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
config = json.loads((HERE / 'test-inputs.json').read_text())
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--case', required=True, choices=config['templates'])
p.add_argument('--build', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
build, out = a.build.resolve(), a.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
manifest = json.loads((build / 'manifest.json').read_text())
assert sha(build / 'manifest.json') == config['manifestSHA256']
assert sha(build / 'contax-zeiss-50-f1-4.bin') == config['imageSHA256']
assert manifest['loaderVersion'] == config['version']
for name, digest in manifest['sources'].items(): assert sha(build / name) == digest, name
assert sha(build / 'tools/hosttest/shim.c') == manifest['hostTestShimSHA256']
out.mkdir(exist_ok=False)
runner_dir = out / 'runners'
runner_dir.mkdir()
rebindings = []

def generate(case):
    spec = config['templates'][case]
    template = ROOT / spec['path']
    assert sha(template) == spec['sha256'], template
    original = template.read_text()
    text = original.replace('__file__', repr(str(template)))
    edits = ['original fixture location retained']
    if '[3,5,0]' in text:
        assert text.count('[3,5,0]') == 1
        text = text.replace('[3,5,0]', '[3,6,0]')
        edits.append('expected input version 3.5 to 3.6')
    if case in ('target-time-composition', 'exact-counter-parity'):
        text = text.replace('04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632', config['imageSHA256'])
        text = text.replace('a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de', config['manifestSHA256'])
        edits.append('exact new image and manifest identity')
    if case == 'query-ownership':
        old = "shutil.copytree(BASE/'tools',work/'tools')"
        assert text.count(old) == 1
        text = text.replace(old, "shutil.copytree((composed if label=='proposal' else BASE)/'tools',work/'tools')")
        edits.append('new EIC host ABI on exact proposal only')
    if case == 'query-flow':
        old = "shutil.copytree(BASE/'tools',work/'tools')"
        assert text.count(old) == 1
        text = text.replace(old, "shutil.copytree((composed if label in ('proposal','mutant-home-gate') else BASE)/'tools',work/'tools')")
        edits.append('new EIC host ABI on exact proposal and its mutant only')
    destination = runner_dir / template.name
    destination.write_text(text)
    rebindings.append(dict(case=case, template=spec, generatedSHA256=sha(destination), changes=edits))
    return destination

if a.case == 'exact-counter-parity':
    # Its original import uses run.py's helpers and exact source identity.
    generate('target-time-composition')
runner = generate(a.case)
result = subprocess.run([sys.executable, str(runner), '--source', str(build),
    '--output', str(out / 'results')], capture_output=True, text=True, cwd=ROOT, timeout=180)
(out / 'stdout.txt').write_text(result.stdout)
(out / 'stderr.txt').write_text(result.stderr)
assert result.returncode == 0, (a.case, result.returncode, result.stdout[-1000:], result.stderr[-2000:])
for name, digest in manifest['sources'].items(): assert sha(build / name) == digest, name
report = dict(status='passed-bound-36-regression-replay', case=a.case,
    imageSHA256=config['imageSHA256'], manifestSHA256=config['manifestSHA256'],
    sourceFilesVerified=len(manifest['sources']), templates=rebindings,
    hardwareReportsSent=0, cameraQualified=False)
(out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
