#!/usr/bin/env python3
"""Replay synthetic bring-up boundaries of the pinned November upstream trial."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CANDIDATE = ROOT / 'firmware/candidates/4.2.0'
COMMIT = 'e054db90cfae5d67fac67a7e0db4bb100f5893ae'
IMAGE_SHA = '2a11822d47672355455dc4415db95f1487527e4f9865270ea368f24fc0ceaa7b'
CASES = ('opener-buffered-at-open', 'opener-after-reset', 'baud-no-rise',
         'baud-no-fall', 'declared-init', 'invalid-readiness')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization; checks require assertions.')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    build, out = a.build.resolve(), a.output.resolve()
    assert out.is_relative_to(ROOT / 'artifacts/private')
    manifest = CANDIDATE / 'manifest.json'
    assert sha(build / 'manifest.json') == sha(manifest)
    m = json.loads(manifest.read_text())
    assert m['upstreamCommit'] == COMMIT and m['imageSHA256'] == IMAGE_SHA
    assert sha(build / 'upstream-november-trial.bin') == sha(CANDIDATE / 'upstream-november-trial.bin') == IMAGE_SHA
    for name, digest in m['builtSourceSHA256'].items():
        assert sha(build / 'src' / name) == digest, name
    host = build / 'tools/hosttest'
    host_pins = {}
    for name in ('sam.h', 'shim.c'):
        value = subprocess.check_output(['git', '-C', str(a.checkout.resolve()), 'show',
                                         f'{COMMIT}:tools/hosttest/{name}'])
        assert (host / name).read_bytes() == value, name
        host_pins[name] = sha(host / name)
    out.mkdir(exist_ok=False)
    flags = ['-std=gnu99', '-Os', '-DNDEBUG', '-DEA9_NO_LOG', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-sanitize-recover=all']
    source = build / 'src'
    binary = out / 'probe'
    subprocess.run(['clang', *flags, '-I'+str(host), '-I'+str(source), str(HERE/'probe.c'),
                    str(host/'shim.c'), *map(str, (source/n for n in
                    ('emount.c', 'emount_packets.c', 'optical_file.c'))), '-o', str(binary)],
                   check=True, timeout=40)
    cases = {}
    for case in CASES:
        r = subprocess.run([binary, case], capture_output=True, text=True, timeout=10, check=True)
        assert not r.stderr, r.stderr
        cases[case] = json.loads(r.stdout)
    result = {'upstreamCommit': COMMIT, 'imageSHA256': IMAGE_SHA, 'manifestSHA256': sha(manifest),
              'boundSourceFiles': len(m['builtSourceSHA256']), 'hostInputSHA256': host_pins,
              'runnerSHA256': sha(Path(__file__)), 'fixtureSHA256': sha(HERE/'probe.c'),
              'hostFlags': flags, 'cases': cases, 'cameraTrafficReplayed': False,
              'rootCauseEstablishedOnCamera': False, 'usbReportsSent': 0,
              'scope': 'Exact protocol C, synthetic input, stubbed pins/UART/time; not a camera acceptance or electrical timing model.'}
    (out/'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(cases, indent=2))


if __name__ == '__main__':
    main()
