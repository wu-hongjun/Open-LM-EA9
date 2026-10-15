#!/usr/bin/env python3
"""Link startup proposals for footprint evidence; never emit a binary image."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from apply import apply, scoped, omit_legacy_snapshot, omit_legacy_close_snapshot

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'artifacts/private/absolute35a'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--design', choices=['global-mask', 'scoped'], required=True)
p.add_argument('--snapshots', choices=['none', 'open', 'both'], required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
work = a.output.resolve()
assert work.is_relative_to(ROOT / 'artifacts/private')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((BASE / 'manifest.json').read_text())
assert sha(BASE / 'manifest.json') == 'a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de'
for name, digest in manifest['sources'].items(): assert sha(BASE / name) == digest, name
work.mkdir(exist_ok=False)
shutil.copytree(BASE / 'src', work / 'src')
(apply if a.design == 'global-mask' else scoped)(work)
if a.snapshots != 'none': omit_legacy_snapshot(work)
if a.snapshots == 'both': omit_legacy_close_snapshot(work)
version = work / 'src/emount.h'
version.write_text(version.read_text().replace('EM_FW_VERSION_BCD   0x35u', 'EM_FW_VERSION_BCD   0x36u'))
deps = ROOT / 'tools/firmware-deps'
arm = str(deps / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
objects = []
for unit in manifest['units']:
    obj = work / (unit + '.o'); objects.append(str(obj))
    subprocess.run([arm + 'gcc', *manifest['flags'], *manifest['unitFlags'].get(unit, []),
        '-Isrc', '-I' + str(deps / 'samd21-dfp-2/samd21a/include'),
        '-I' + str(deps / 'CMSIS_5-5.9.0/CMSIS/Core/Include'),
        '-c', 'src/' + unit + '.c', '-o', str(obj)], cwd=work, check=True)
elf = work / 'analysis-only.elf'
result = subprocess.run([arm + 'gcc', *objects, '-mthumb', '-mcpu=cortex-m0plus',
    '-Tsrc/ea9.ld', '-Wl,--gc-sections,-Map=' + str(work / 'analysis-only.map'),
    '--specs=nano.specs', '--specs=nosys.specs', '-o', str(elf)], cwd=work, capture_output=True, text=True)
(work / 'link.log').write_text(result.stdout + result.stderr)
assert result.returncode == 0, result.stderr
symbols = {}
for line in subprocess.check_output([arm + 'nm', str(elf)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3: symbols[fields[2]] = int(fields[0], 16)
end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
report = dict(status='analysis-only-not-candidate', design=a.design, omittedSnapshots=a.snapshots,
    baseImageSHA256=manifest['imageSHA256'], baseManifestSHA256=sha(BASE / 'manifest.json'),
    codeAndDataEnd=end, marginBeforeDiagnostics=0x9c00-end, meets256ByteMargin=0x9c00-end >= 256,
    staticRAMBytes=symbols['_ezero']-0x20000000, binaryGenerated=False, hardwareReportsSent=0,
    runnerSHA256=sha(Path(__file__)), applicatorSHA256=sha(Path(__file__).with_name('apply.py')),
    sources={str(p.relative_to(work)): sha(p) for p in (work / 'src').iterdir() if p.suffix in ['.c', '.h', '.ld']})
(work / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'sources'}, indent=2))
