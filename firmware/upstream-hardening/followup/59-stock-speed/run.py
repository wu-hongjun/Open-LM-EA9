#!/usr/bin/env python3
"""Compare exact production sources of 4.2.0 and 4.4.0 using synthetic requests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compile_trial(build, version, image, binary):
    candidate = ROOT / 'firmware/candidates' / version
    manifest = json.loads((candidate / 'manifest.json').read_text())
    assert (candidate / 'manifest.json').read_bytes() == (build / 'manifest.json').read_bytes()
    assert digest(candidate / image) == digest(build / image) == manifest['imageSHA256']
    for name, expected in manifest['builtSourceSHA256'].items():
        assert digest(build / 'src' / name) == expected, name
    shim = build / 'tools/hosttest'
    source = build / 'src'
    subprocess.run(['clang', '-std=gnu99', '-Os', '-DNDEBUG', '-DEA9_NO_LOG', '-Wall', '-Wextra',
                    '-Werror', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                    f'-I{shim}', f'-I{source}', str(HERE / 'compare.c'), str(shim / 'shim.c'),
                    *(str(source / name) for name in ('emount.c', 'emount_packets.c', 'optical_file.c')),
                    '-o', str(binary)], check=True, timeout=40)


def replay(binary, case):
    r = subprocess.run([binary, case], capture_output=True, text=True, timeout=10, check=True)
    assert not r.stderr, r.stderr
    return json.loads(r.stdout)


def main():
    if not __debug__:
        raise SystemExit('Run without Python optimization.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(ROOT / 'artifacts/private')
    out.mkdir(exist_ok=False)
    control, candidate = out / 'control', out / 'candidate'
    compile_trial(args.control.resolve(), '4.2.0', 'upstream-november-trial.bin', control)
    compile_trial(args.candidate.resolve(), '4.4.0', 'upstream-stock-speed.bin', candidate)
    result = {}
    for case in ('pulse', 'no-rise', 'no-fall'):
        a, b = replay(control, case), replay(candidate, case)
        assert (a['baud'], a['changes'], a['switchAfterReply']) == (0x8000, 1, 3)
        assert (b['baud'], b['changes'], b['switchAfterReply'], b['pulseReads']) == (0xc000, 0, -1, 0)
        assert a['pulseReads'] == (4 if case == 'pulse' else 0)
        a_frames, b_frames = [[bytes.fromhex(f) for f in run['frames']] for run in (a, b)]
        assert len(a_frames) == len(b_frames) == 13
        differences = [i for i, (x, y) in enumerate(zip(a_frames, b_frames)) if x != y]
        assert differences == [2]
        x, y = a_frames[2], b_frames[2]
        assert x[5:7] == b'\x0c\x01' and y[5:7] == b'\x0c\x00'
        assert [i for i, (old, new) in enumerate(zip(x, y)) if old != new] == [6, 7]
        assert x[7] == y[7] + 1
        result[case] = {'identicalReplies': 12, 'changedReply': '0x0c', 'controlBaud': 1500000,
                        'candidateBaud': 750000, 'candidateSwitchPulseReads': 0}
    for case in ('opener-buffered-at-open', 'invalid-readiness'):
        result[case] = replay(control, case)
        assert result[case] == replay(candidate, case)
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
