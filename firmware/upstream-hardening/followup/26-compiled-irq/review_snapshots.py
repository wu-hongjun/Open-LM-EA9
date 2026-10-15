#!/usr/bin/env python3
"""Prove the two omitted RAM snapshots have no release reader; no hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from apply import omit_legacy_snapshot, omit_legacy_close_snapshot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
source, out = a.source.resolve(), a.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
manifest = json.loads((source / 'manifest.json').read_text())
assert sha(source / 'manifest.json') == 'a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de'
for name, digest in manifest['sources'].items(): assert sha(source / name) == digest, name
out.mkdir(exist_ok=False)
shutil.copytree(source / 'src', out / 'src')
omit_legacy_snapshot(out)
omit_legacy_close_snapshot(out)
deps = ROOT / 'tools/firmware-deps'
gcc = deps / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-gcc'
includes = ['-I' + str(source / 'src'), '-I' + str(deps / 'samd21-dfp-2/samd21a/include'),
    '-I' + str(deps / 'CMSIS_5-5.9.0/CMSIS/Core/Include')]
identifiers = ('em_rx_bytes_at_open', 'em_rx_bytes_at_close')
rows = []
for mode in ('release', 'logging'):
    flags = [f for f in manifest['flags'] if mode == 'release' or f != '-DEA9_NO_LOG']
    hits = []
    for unit in manifest['units']:
        cmd = [str(gcc), *flags, *manifest['unitFlags'].get(unit, []), *includes, '-E', '-P']
        before = subprocess.check_output([*cmd, str(source / 'src' / (unit + '.c'))], text=True)
        for line in before.splitlines():
            if any(re.search(r'\b' + name + r'\b', line) for name in identifiers):
                if not re.fullmatch(r'\s*(extern )?volatile uint32_t em_rx_bytes_at_(open|close);\s*', line):
                    hits.append(dict(unit=unit, line=line.strip()))
        if unit == 'emount':
            after = subprocess.check_output([*cmd, str(out / 'src/emount.c')], text=True)
            expected = before
            if mode == 'release':
                for name in identifiers:
                    assignment = ' ' + name + ' = em_rx_bytes;\n'
                    assert expected.count(assignment) == 1
                    expected = expected.replace(assignment, '')
            assert after == expected, mode
    if mode == 'release':
        assert hits == [dict(unit='emount', line=name + ' = em_rx_bytes;') for name in identifiers], hits
    else:
        assert any(row['unit'] == 'main' and all(name in row['line'] for name in identifiers) for row in hits)
    rows.append(dict(mode=mode, units=len(manifest['units']), expressions=hits,
        tokenParity='only-two-assignments-removed' if mode == 'release' else 'identical'))
result = dict(status='passed-two-legacy-snapshot-consumer-review',
    sourceManifestSHA256=sha(source / 'manifest.json'), sourceHashesVerified=len(manifest['sources']),
    compilerSHA256=sha(gcc), runnerSHA256=sha(Path(__file__)), results=rows,
    hardwareReportsSent=0, limits='RAM snapshot reads only; live RX counters, MMIO and all other tokens are unchanged. No physical timing or camera qualification.')
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(result['status'])
