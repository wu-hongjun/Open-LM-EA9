#!/usr/bin/env python3
"""2.5 regressions and frozen 2.4 negative control, entirely offline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
out.mkdir(parents=True, mode=0o700, exist_ok=False)
base = ROOT / 'firmware/ea9'
flags = ['cc', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror',
         '-fsanitize=address,undefined', '-fno-sanitize-recover=all']
sources = ['../tests/test_refined_camera_limits.c', 'hosttest/sim_motor.c',
           'src/factory_servo.c', 'src/factory_af.c', 'src/io_guard.c',
           'src/focus_map.c', 'src/af_control.c', 'src/af_completion.c', 'src/focus_dist.c']
binary = out / 'motion'
subprocess.run(flags + ['-Ihosttest', '-Isrc', *sources, '-o', str(binary)], cwd=base, check=True)
rows = []
for target in [4, 40, 100, 400, 1000, 3000, 5000, 5952]:
    result = subprocess.run([str(binary), str(target)], capture_output=True, text=True, check=True)
    fields = dict(part.split('=', 1) for part in result.stdout.split())
    rows.append({k: float(v) if '.' in v else int(v) for k, v in fields.items()})

frozen = ROOT / 'firmware/candidates/2.4.0/counterexample-src'
manifest = json.loads((frozen / 'manifest.json').read_text())
for name, digest in manifest['files'].items():
    if hashlib.sha256((frozen / name).read_bytes()).hexdigest() != digest:
        raise RuntimeError('Frozen input changed: ' + name)
probe = ROOT / 'firmware/tests/test_aperture_query.c'
transport = ['hosttest/shim.c', 'src/emount.c', 'src/emount_packets.c', 'src/lens_profile.c']
queries = {}
for name, source_base, extras in [('2.4.0', frozen / 'firmware/ea9', []),
                                  ('2.5.0', base, ['src/lens_aperture.c'])]:
    program = out / ('query-' + name)
    # Inherited mock MMIO deliberately uses alignment > macOS segment alignment.
    # Suppress that compile diagnostic, not runtime sanitizer checks.
    subprocess.run(flags + ['-Wno-over-aligned', '-Ihosttest', '-Isrc', str(probe),
                            *transport, *extras, '-o', str(program)], cwd=source_base, check=True)
    result = subprocess.run([str(program)], capture_output=True, text=True)
    expected = 1 if name == '2.4.0' else 0
    if result.returncode != expected:
        raise RuntimeError('Unexpected query regression result: ' + name + result.stderr)
    queries[name] = {'exitCode': result.returncode, 'output': result.stdout.strip(),
                     'negativeControl': name == '2.4.0'}

# Independent original-instruction assertion: factory 0x34 echoes the parsed
# request payload word at request snapshot 0x694 + header length 6. This does
# not establish an independently sensed or persistent current-aperture state.
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure
configure(output=out / 'original-instructions')
from oracle import Machine
original = []
for av in [0x1100, 0x1200, 0x1600]:
    machine = Machine({0x51c8: 0, 0x9180: 0})
    for off, value, width in [(0x51f, 1, 1), (0x697, 2, 1), (0x699, 0x34, 1), (0x69a, av, 2)]:
        machine.set(0x20000000 + off, value, width)
    machine.run(0x58a4)
    got = machine.get(0x2000030f, 2)
    if got != av: raise RuntimeError('Original query aperture mismatch')
    original.append({'requestSnapshotAV': av, 'replyAV': got, 'passed': True})
report = {'firmware': '2.5.0', 'status': 'passed-offline-regressions-not-camera-qualified',
          'hardwareReportsSent': 0, 'simulatedTargets': rows, 'queryRegression': queries,
          'originalInstructionQueryCases': original,
          'factoryApertureBehavior': 'parsed-request-word echo, intentionally overridden by fixed passive-iris policy',
          'oneUnitCorrectionRequiresDrive': False,
          'healthyDeadlineAllowsNextCommand': True,
          'cameraExposureQualified': False, 'cameraAFQualified': False,
          'limitations': ['Inherited mechanics, not measured on owner unit',
                          'No lens optics, camera metering or live wire timing modeled',
                          'Original transmitter stubbed; Cortex-M0 emulator is not an ISA legality proof'],
          'sources': {str((base / name).resolve().relative_to(ROOT)):
                      hashlib.sha256((base / name).read_bytes()).hexdigest() for name in sources},
          'apertureProbeSHA256': hashlib.sha256(probe.read_bytes()).hexdigest()}
report['scriptSHA256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
report['apertureSources'] = {str((base / name).relative_to(ROOT)):
    hashlib.sha256((base / name).read_bytes()).hexdigest()
    for name in transport + ['src/lens_aperture.c']}
report['frozen24ManifestSHA256'] = hashlib.sha256((frozen / 'manifest.json').read_bytes()).hexdigest()
(out / 'regressions.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
