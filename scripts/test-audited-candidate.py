#!/usr/bin/env python3
"""Historical AF 2.6 regressions, opaque stock-query oracle and frozen 2.5 control."""
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
out.mkdir(mode=0o700, parents=True, exist_ok=False)
# Historical 2.6 is immutable even after current motion-wrapper changes.
frozen26 = json.loads((ROOT / 'firmware/candidates/2.6.0/regression-inputs.json').read_text())
snapshot26 = out / 'frozen26'
for name, digest in frozen26['files'].items():
    data = subprocess.run(['git', 'show', frozen26['sourceGitCommit'] + ':' + name],
                          cwd=ROOT, capture_output=True, check=True).stdout
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('Frozen 2.6 source mismatch: ' + name)
    path = snapshot26 / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
base = snapshot26 / 'firmware/ea9'
flags = ['cc', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror',
         '-Wno-over-aligned', '-fsanitize=address,undefined', '-fno-sanitize-recover=all']
transport = ['hosttest/shim.c', 'src/emount.c', 'src/emount_packets.c',
             'src/lens_profile.c', 'src/lens_aperture.c']
probe = snapshot26 / 'firmware/tests/test_stock_query.c'
program = out / 'query26'
subprocess.run(flags + ['-Ihosttest', '-Isrc', str(probe), *transport, '-o', str(program)],
               cwd=base, check=True)
coverage = subprocess.run([str(program)], capture_output=True, text=True, check=True).stdout.strip()

# Frozen 2.5 negative control: original sources from an immutable commit,
# digest checked. Its unsupported override must fail the new stock test.
historical = json.loads((ROOT / 'firmware/candidates/2.5.0/regression-inputs.json').read_text())
snapshot = out / 'frozen25'
for name, digest in historical['files'].items():
    data = subprocess.run(['git', 'show', historical['sourceGitCommit'] + ':' + name],
                          cwd=ROOT, capture_output=True, check=True).stdout
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeError('Frozen 2.5 source mismatch: ' + name)
    path = snapshot / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
negative = out / 'query25'
subprocess.run(flags + ['-Ihosttest', '-Isrc', str(probe), *transport, '-o', str(negative)],
               cwd=snapshot / 'firmware/ea9', check=True)
control = subprocess.run([str(negative), '0xa55a', '0xff', '11'], capture_output=True, text=True)
if control.returncode != 1:
    raise RuntimeError('Frozen 2.5 unsupported override was not detected: ' + control.stderr)

# Compare the COMPLETE 32-byte response from the original handler and sender.
# Final I/O helpers 0x51c8/0x9180 are stubbed, but original framing/checksum
# instructions execute. Do not replace their result or assign aperture meaning.
sys.path.insert(0, str(ROOT / 'research/stock-1.8'))
from config import configure, FIRMWARE_SHA256
configure(output=out / 'original-instructions')
from oracle import Machine
words = [0, 1, 0x0352, 0x1100, 0x1200, 0x1600, 0xa55a, 0xffff]
original_cases = 0
frames = bytearray()
for word in words:
    for sequence in [0, 1, 0x71, 0xff]:
        machine = Machine({0x51c8: 0, 0x9180: 0})
        for off, value, width in [(0x51f, 1, 1), (0x697, 2, 1), (0x698, sequence, 1),
                                  (0x699, 0x34, 1), (0x69a, word, 2)]:
            machine.set(0x20000000 + off, value, width)
        machine.run(0x58a4)
        expected = bytearray(machine.u.mem_read(0x20000308, 32))
        if (expected[1:3] != bytes([32, 0]) or expected[-1] != 0x55 or
                expected[-3:-1] != sum(expected[1:-3]).to_bytes(2, 'little')):
            raise RuntimeError('Original sender framing/checksum assertion failed')
        got = subprocess.run([str(program), str(word), str(sequence), '11'],
                             capture_output=True, text=True, check=True)
        actual = bytes.fromhex(got.stdout.strip())
        if actual != expected:
            raise RuntimeError(f'Original full 0x34 reply mismatch for opaque word {word:#x}')
        frames.extend(actual)
        original_cases += 1

motion_sources = ['../tests/test_refined_camera_limits.c', 'hosttest/sim_motor.c',
                  'src/factory_servo.c', 'src/factory_af.c', 'src/io_guard.c',
                  'src/focus_map.c', 'src/af_control.c', 'src/af_completion.c', 'src/focus_dist.c']
motion = out / 'motion26'
subprocess.run(flags + ['-Ihosttest', '-Isrc', *motion_sources, '-o', str(motion)], cwd=base, check=True)
rows = []
for target in [4, 40, 100, 400, 1000, 3000, 5000, 5952]:
    result = subprocess.run([str(motion), str(target)], capture_output=True, text=True, check=True)
    fields = dict(part.split('=', 1) for part in result.stdout.split())
    rows.append({k: float(v) if '.' in v else int(v) for k, v in fields.items()})

retained = ['factory_af.c', 'factory_servo.c', 'af_control.c', 'af_completion.c',
            'af_reference.c', 'focus_map.c', 'focus_pred.c', 'focus_dist.c', 'main.c']
for name in retained:
    path = 'firmware/ea9/src/' + name
    old = subprocess.run(['git', 'show', historical['sourceGitCommit'] + ':' + path],
                         cwd=ROOT, check=True, capture_output=True).stdout
    if old != (snapshot26 / path).read_bytes(): raise RuntimeError('Retained AF source changed: ' + path)

report = {'firmware': '2.6.0', 'status': 'historical-reproduction-passed-not-current-candidate-qualification',
          'hardwareReportsSent': 0, 'frozen26SourceGitCommit': frozen26['sourceGitCommit'], 'opaqueQueryCoverage': coverage,
          'originalInstructionFullReplyCases': original_cases,
          'originalInstructionImageSHA256': FIRMWARE_SHA256,
          'comparedReplyFramesSHA256': hashlib.sha256(frames).hexdigest(),
          'stockInitReplySequencePreserved': True,
          'originalSenderChecksumExecuted': True,
          'missingOperandRejected': True, 'message34Meaning': 'unknown, opaque transport operand',
          'frozen25NegativeControlDetected': True,
          'frozen25SourceGitCommit': historical['sourceGitCommit'],
          'retainedAFSourcesMatch25': True,
          'simulatedTargets': rows, 'cameraExposureQualified': False, 'cameraAFQualified': False,
          'limitations': ['No live USB, camera, optics, metering or electrical timing',
                          'Mechanical model inherited from upstream, not measured on owner unit',
                          'Final I/O helpers stubbed; original handler and sender checksum instructions execute',
                          'Minimum operand bound is not proof of complete 0x34 request grammar',
                          'Unicorn behavior does not prove ARMv6-M instruction legality'],
          'sources': {str((base / name).resolve().relative_to(snapshot26)):
                      hashlib.sha256((base / name).read_bytes()).hexdigest()
                      for name in transport + motion_sources},
          'probeSHA256': hashlib.sha256(probe.read_bytes()).hexdigest(),
          'scriptSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'frozen25ManifestSHA256': hashlib.sha256((ROOT / 'firmware/candidates/2.5.0/regression-inputs.json').read_bytes()).hexdigest()}
(out / 'regressions.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
