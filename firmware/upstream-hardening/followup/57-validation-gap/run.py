#!/usr/bin/env python3
"""Prospective lane50 replay preserving the production home gate. Offline only."""
import argparse
import hashlib
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUNNER = HERE.parent/'50-readiness-capture/run.py'
NEXT = ROOT/'firmware/upstream-hardening/next41'
PINS = {
    RUNNER: 'f3051fe6fdd7bc127c50b39dfc79d34282abce26474322e59bb8595243348283',
    RUNNER.with_name('test_composed.c'): 'afb99225ec615a2ed2d29fb17cea3c39df2757e9166573c2ab2a6613cfbc3b48',
    HERE.parent/'46-shutter-readiness/run.py': '8ec3dfd3352b6f6e02ece6f48d9ce31c299737c59b24af132890e4034d1fc1a8',
    ROOT/'firmware/upstream-diagnostic/tests/trace_host.c': 'c3b65560600e5334a70e665cc290ea87b341198477230ea8a01e4d22c3b6b4e9',
    NEXT/'compiler_compat.py': 'c7a0197c346ffab8585a85206287ca3243ad143e51368c1e98f69a2e67628afd',
    NEXT/'trace_compat.c': '07f6f30ecb591f76d54522298ad17e9829816b223c1ad17416f9bdf4b1ff45b1',
    NEXT/'packet_test_init.c': '21c84f5f6f62970e37f1398a0bc45f6474d9045a01f22efd1d7bf1293dbe27a9',
}

def gate_constants(source):
    """Keep the complete production conditional, including continued macros."""
    marker = '#define HOME_DELAY_MS'
    assert source.count(marker) == 1, 'ambiguous production home gate'
    start = source.index(marker)
    end = source.index('\n#endif', start) + len('\n#endif')
    block = source[start:end]
    assert block.count('#if HOME_DELAY_MS > 0') == 1
    assert block.count('#else') == 1
    assert block.count('#define HOME_GATE_OPEN()') == 2
    assert block.count('#if') == 1, 'nested home gate requires explicit review'
    constants = re.findall(r'^#define (?:HOME_\w+|MOVE_DUTY|FOCUS_DEADBAND_COUNTS)\s+[^\\\n]+$', source, re.M)
    constants = [line for line in constants if not line.startswith(marker)]
    return '\n'.join(constants) + '\n' + block + '\n'

def main():
    if not __debug__:
        raise SystemExit('optimized Python disables required acceptance checks')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for path, pin in PINS.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin, path
    source = RUNNER.read_text()
    needle = next(line for line in source.splitlines() if line.strip().startswith("constants='\\n'.join(re.findall("))
    assert "#define HOME_GATE_OPEN() 1" in needle
    assert source.count(needle) == 1
    source = source.replace(needle, '  constants=validation57_constants(s)')
    sys.path.insert(0, str(NEXT))
    from compiler_compat import install
    install(NEXT/'trace_compat.c', args.candidate.resolve()/'src')
    sys.argv = [str(RUNNER), '--candidate', str(args.candidate.resolve()), '--output', str(args.output.resolve())]
    # Preserve the historical runner's fixture/module locations. Only its host
    # constants extraction differs; neither the frozen runner nor candidate is edited.
    exec(compile(source, str(RUNNER), 'exec'), {
        '__file__': str(RUNNER), '__name__': '__main__',
        'validation57_constants': gate_constants,
    })

if __name__ == '__main__':
    main()
