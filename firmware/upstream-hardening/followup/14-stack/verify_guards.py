#!/usr/bin/env python3
"""Negative controls for missing evidence and an insufficient stack budget."""
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    original = json.loads((HERE / 'policy.json').read_text())
    cases = [
        ('insufficient-budget', ['--budget', '1559'], None, 'exceeds budget'),
        ('unconditional-claim', ['--require-unconditional'], None, 'unconditional safety unavailable'),
        ('missing-callback', [], lambda p: p['indirectCalls'].pop('7236'), 'unknown indirect call'),
        ('missing-library-frame', [], lambda p: p['libraryFrames'].pop('memcpy'), 'unknown library frame'),
        ('wrong-elf-pin', [], lambda p: p['pins'].__setitem__('hardened.elf', '0' * 64), 'pin mismatch'),
        ('recursive-callback', [], lambda p: p['indirectCalls']['7236'].__setitem__('targets', ['servo_move_rel']), 'recursive/reentrant'),
    ]
    records = []
    with tempfile.TemporaryDirectory(prefix='astra-14-guards-', dir=ROOT / 'artifacts/private') as scratch:
        for name, args, mutate, diagnostic in cases:
            if mutate:
                policy = json.loads(json.dumps(original))
                mutate(policy)
                path = Path(scratch) / (name + '.json')
                path.write_text(json.dumps(policy))
                args = ['--policy', str(path), *args]
            result = subprocess.run(['python3', str(HERE / 'audit.py'), *args], text=True, capture_output=True, timeout=30)
            if result.returncode != 1 or diagnostic not in result.stderr:
                raise RuntimeError(f'{name} did not reject as expected: {result.stdout} {result.stderr}')
            records.append(dict(case=name, status='rejected', diagnostic=result.stderr.strip()))
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
