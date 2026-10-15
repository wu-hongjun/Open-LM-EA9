#!/usr/bin/env python3
"""Verify the exact offline 3.6 composition, compiled evidence and decoder."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
NEXT = ROOT / 'firmware/upstream-hardening/next36'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
build, out = a.build.resolve(), a.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
out.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((build / 'manifest.json').read_text())
published = ROOT / 'firmware/candidates/3.6.0'
image = (build / 'contax-zeiss-50-f1-4.bin').read_bytes()
assert manifest['loaderVersion'] == [3, 6, 0]
assert manifest['imageSHA256'] == hashlib.sha256(image).hexdigest() == 'd8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f'
assert (build / 'manifest.json').read_bytes() == (published / 'contax-zeiss-50-f1-4.manifest.json').read_bytes()
assert image == (published / 'contax-zeiss-50-f1-4.bin').read_bytes()
assert image == (ROOT / 'apps/macos/Sources/DeviceKit/Resources/ea9-af-handoff-upstream.bin').read_bytes()
assert len(image) == 20480 and image[0x4c00:] == b'\xff' * 1024
assert manifest['codeMarginBeforeDiagnostics'] >= 256 and not manifest['cameraQualified']
for name, digest in manifest['sources'].items(): assert sha(build / name) == digest, name
assert sha(build / 'tools/hosttest/shim.c') == manifest['hostTestShimSHA256']
rows = []

def run(name, command, expected_success=True):
    result = subprocess.run(list(map(str, command)), cwd=ROOT, capture_output=True, text=True, timeout=180)
    (out / (name + '.stdout')).write_text(result.stdout)
    (out / (name + '.stderr')).write_text(result.stderr)
    assert (result.returncode == 0) == expected_success, (name, result.returncode, result.stderr[-2000:])
    rows.append(dict(name=name, exitCode=result.returncode, expectedSuccess=expected_success))

lane10 = ROOT / 'firmware/upstream-hardening/lanes/10-integration'
for name, script, extra in [('commits', 'run.py', ['--already-applied']),
                           ('capture', 'regression.py', []), ('diagnostics', 'diagnostics.py', [])]:
    run(name, [sys.executable, lane10 / script, '--source', build, '--output', out / name, *extra])
for name in json.loads((NEXT / 'test-inputs.json').read_text())['templates']:
    run(name, [sys.executable, NEXT / 'replay.py', '--case', name, '--build', build, '--output', out / name])
lane17 = ROOT / 'firmware/upstream-hardening/followup/17-composition'
for name, script in [('home-inhibit', 'run_home.py'), ('query-servo-composition', 'run_composition.py')]:
    run(name, [sys.executable, lane17 / script, '--source', build, '--output', out / name])
run('startup-handoff', [sys.executable, ROOT / 'firmware/upstream-hardening/followup/28-startup-handoff-review/run.py',
    '--source', ROOT / 'artifacts/private/absolute35a', '--candidate', build, '--output', out / 'startup-handoff'])
run('snapshot-consumers', [sys.executable, ROOT / 'firmware/upstream-hardening/followup/26-compiled-irq/review_snapshots.py',
    '--source', ROOT / 'artifacts/private/absolute35a', '--output', out / 'snapshot-consumers'])

# Rebind only path-dependent ELF/map containers, after exact executable and
# normalized compiled-metadata equality. Reviewed call/IRQ/library guards stay.
stack = ROOT / 'firmware/upstream-hardening/followup/29-stack36'
policy = json.loads((stack / 'policy.json').read_text())
reference = json.loads((NEXT / 'stack-reproduction.json').read_text())
assert reference['referenceELFSHA256'] == policy['pins']['hardened.elf']
assert reference['reviewedPolicySHA256'] == sha(stack / 'policy.json')
for name in ['contax-zeiss-50-f1-4.bin', 'manifest.json', 'raw.bin']:
    assert sha(build / name) == policy['pins'][name], name
objdump = ROOT / 'tools/firmware-deps/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-objdump'
assert sha(objdump) == reference['objdumpSHA256']
for mode, expected in reference['normalizedOutputSHA256'].items():
    rendered = subprocess.check_output([str(objdump), mode, str(build / 'hardened.elf')], text=True)
    header = str(build / 'hardened.elf') + ':     file format elf32-littlearm'
    assert rendered.count(header) == 1
    assert hashlib.sha256(rendered.replace(header, '<ELF>:     file format elf32-littlearm').encode()).hexdigest() == expected
rebound = {}
for name in ['hardened.elf', 'hardened.map']:
    actual = sha(build / name)
    if actual != policy['pins'][name]:
        rebound[name] = dict(reviewed=policy['pins'][name], reproduced=actual)
        policy['pins'][name] = actual
policy_path = out / 'stack-policy.json'
policy_path.write_text(json.dumps(policy, indent=2) + '\n')
run('stack-and-nvic-order', [sys.executable, stack / 'run.py', '--build', build, '--policy', policy_path,
    '--output', out / 'stack.json', '--guards-output', out / 'stack-guards.json'])
result = json.loads((out / 'stack.json').read_text())
assert result['maximumAllVectorPriorityBytes'] == 1560 and not result['recursiveComponents']
run('decoder-boundaries', [sys.executable, NEXT / 'test_decoder.py', '--output', out / 'decoder-boundaries'])
run('compiled-writer', [ROOT / 'tools/rea-analysis/venv/bin/python', ROOT / 'scripts/test-startup-flash-arm.py',
    '--version', '3.6.0', '--build', build, '--output', out / 'compiled-writer.json'])
for version in ['3.2.0', '3.3.0', '3.4.0', '3.5.0', '3.6.0']:
    pristine = (ROOT / 'firmware/candidates' / version / 'contax-zeiss-50-f1-4.bin').read_bytes()
    flash = bytearray(b'\xff' * 0x20000)
    flash[0x4000:0x4003] = bytes(map(int, version.split('.')))
    flash[0x5000:0xa000] = pristine
    path = out / ('synthetic-' + version + '.bin')
    path.write_bytes(flash)
    decoded_path = out / ('decoded-' + version + '.json')
    run('decode-' + version, [sys.executable, ROOT / 'scripts/decode-startup-diagnostics.py', path, '--output', decoded_path])
    decoded = json.loads(decoded_path.read_text())
    assert decoded['immutableCodePrefixMatches'] and not decoded['installationVerificationPerformed']
    assert decoded['erasedPages'] == 16 and decoded['firmwareVersion'] == version
    flash[0x6000] ^= 1
    path = out / ('bad-prefix-' + version + '.bin')
    path.write_bytes(flash)
    run('reject-prefix-' + version, [sys.executable, ROOT / 'scripts/decode-startup-diagnostics.py', path], False)
for name, digest in manifest['sources'].items(): assert sha(build / name) == digest, name
report = dict(status='passed-exact-36-offline-composition', imageSHA256=manifest['imageSHA256'],
    manifestSHA256=sha(build / 'manifest.json'), sourceFilesVerified=len(manifest['sources']),
    checks=rows, stackContainerPinsRebound=rebound, hardwareReportsSent=0, cameraQualified=False,
    limits='Finite host peripheral/IRQ cuts and compiled contracts do not qualify physical timing, exposure, capture/shutdown or optical AF.')
(out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'checks'}, indent=2))
