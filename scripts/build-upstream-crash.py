#!/usr/bin/env python3
"""Build AF 4.1 offline from pinned 4.0 and reviewed, hash-bound applicators.

Outputs must be fresh private directories. Never touches a device, published
release, canonical host state, or existing build. Workbench status is not release
acceptance and no synthetic result establishes camera compatibility.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

if not __debug__:
    raise SystemExit('Optimized Python disables required build assertions.')

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'firmware/upstream-hardening'
BASE = ROOT / 'artifacts/private/reference40-repeat'
DEPS = ROOT / 'tools/firmware-deps'
ARM = str(DEPS / 'arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
work = a.output.resolve()
plan_path = LANE / 'next41/accepted-lanes.json'
plan = json.loads(plan_path.read_text())
manifest_path = ROOT / 'firmware/candidates/4.0.0/contax-zeiss-50-f1-4.manifest.json'
frozen = json.loads(manifest_path.read_text())
assert plan['baseVersion'] == '4.0.0' and plan['nextVersion'] == '4.1.0'
assert plan['baseImageSHA256'] == frozen['imageSHA256'] == '06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae'
assert sha(manifest_path) == '8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc'
assert frozen == json.loads((BASE / 'manifest.json').read_text()), 'Reproduce pinned 4.0 first'
for name, pin in frozen['sources'].items():
    assert sha(BASE / name) == pin, name
assert sha(BASE / 'tools/hosttest/shim.c') == frozen['hostTestShimSHA256']
assert sha(BASE / 'from-39.patch') == frozen['from39PatchSHA256']
assert sha(ROOT / 'firmware/candidates/4.0.0/contax-zeiss-50-f1-4.bin') == frozen['imageSHA256']
assert work.is_relative_to(ROOT / 'artifacts/private') and work.parent.exists()
work.mkdir(exist_ok=False)
shutil.copytree(BASE / 'src', work / 'src')
shutil.copytree(BASE / 'tools/hosttest', work / 'tools/hosttest')
for name, pin in plan['inputs'].items():
    path = (ROOT / name).resolve()
    assert path.is_relative_to(LANE) and sha(path) == pin, name
for entry in plan['applicators']:
    assert entry['path'] in plan['inputs']
    runpy.run_path(str(ROOT / entry['path']))[entry['entry']](work / 'src' if entry['argument'] == 'src' else work)
header = work / 'src/emount.h'
text = header.read_text()
assert text.count('#define EM_FW_VERSION_BCD   0x40u') == 1
header.write_text(text.replace('#define EM_FW_VERSION_BCD   0x40u', '#define EM_FW_VERSION_BCD   0x41u'))

units = frozen['units'] + plan['additionalUnits']
assert len(set(units)) == len(units)
flags = frozen['flags']
unit_flags = {**frozen['unitFlags'], **plan['additionalUnitFlags']}
assert all(value == ['-Os'] for value in unit_flags.values())
includes = ['-Isrc', '-I' + str(DEPS / 'samd21-dfp-2/samd21a/include'), '-I' + str(DEPS / 'CMSIS_5-5.9.0/CMSIS/Core/Include')]
objects = []
for name in units:
    obj = work / (name + '.o')
    objects.append(str(obj))
    subprocess.run([ARM+'gcc', *flags, *unit_flags.get(name, []), *includes, '-c', 'src/'+name+'.c', '-o', str(obj)], cwd=work, check=True)
elf = work / 'hardened.elf'
subprocess.run([ARM+'gcc', *objects, '-mthumb', '-mcpu=cortex-m0plus', '-Tsrc/ea9.ld', '-Wl,--gc-sections,-Map='+str(work/'hardened.map'), '--specs=nano.specs', '--specs=nosys.specs', '-o', str(elf)], cwd=work, check=True)
symbols = {}
for line in subprocess.check_output([ARM+'nm', str(elf)], text=True).splitlines():
    fields = line.split()
    if len(fields) == 3:
        symbols[fields[2]] = int(fields[0], 16)
end = symbols['_etext'] + symbols['_erelocate'] - symbols['_srelocate']
assert 0x9c00 - end >= 256, 'Code/data must retain 256-byte margin and complete diagnostic region'
assert symbols['_estack'] <= 0x20003fc0
assert symbols['retained'] == 0x20003fc0
subprocess.run([ARM+'objcopy', '-O', 'binary', '--gap-fill=0xff', str(elf), str(work/'raw.bin')], check=True)
raw = (work/'raw.bin').read_bytes()
assert len(raw) <= 0x4c00 and 0x5000 + len(raw) == end
image = raw + b'\xff' * (0x5000-len(raw))
(work/'contax-zeiss-50-f1-4.bin').write_bytes(image)
assert image[0x4c00:] == b'\xff' * 1024
assert int.from_bytes(image[:4], 'little') == symbols['_estack']
assert int.from_bytes(image[4:8], 'little') == symbols['Reset_Handler'] | 1
published = ROOT / 'firmware/candidates/4.1.0/contax-zeiss-50-f1-4.bin'
if published.exists():
    assert published.read_bytes() == image, 'Frozen release differs: use a new candidate version'
patch = []
for path in sorted((work/'src').iterdir()):
    if path.suffix not in ('.c', '.h', '.ld'):
        continue
    previous = BASE / 'src' / path.name
    old = previous.read_text() if previous.exists() else ''
    if old != path.read_text():
        patch.extend(difflib.unified_diff(old.splitlines(True), path.read_text().splitlines(True), fromfile='frozen40/src/'+path.name if previous.exists() else '/dev/null', tofile='crash41/src/'+path.name, n=0))
(work/'from-40.patch').write_text(''.join(patch))
result = {key: frozen[key] for key in ('upstreamCommit', 'diagnosticRange', 'diagnosticPageBytes', 'diagnosticPages', 'diagnosticFormatVersion', 'diagnosticEventRetention', 'diagnosticMotionBytes', 'diagnosticTerminalReservePages', 'lensID', 'nominalApertureAV', 'runtimeLensProfilesSupported')}
result.update(status=plan['status'], baseImageSHA256=frozen['imageSHA256'], loaderVersion=[4,1,0], imageSHA256=sha(work/'contax-zeiss-50-f1-4.bin'), imageBytes=len(image), rawBytes=len(raw), codeAndDataEnd=end, codeMarginBeforeDiagnostics=0x9c00-end, staticRAMBytes=symbols['_ezero']-0x20000000, reservedStackBytes=symbols['_estack']-symbols['_sstack'], cameraQualified=False, hardwareReportsSent=0, publishedFirmwareChanged=False, acceptedPlanSHA256=sha(plan_path), baseManifestSHA256=sha(manifest_path), buildScriptSHA256=sha(Path(__file__).resolve()), laneInputs=plan['inputs'], units=units, flags=flags, unitFlags=unit_flags, sources={str(path.relative_to(work)):sha(path) for path in sorted((work/'src').iterdir()) if path.suffix in ('.c','.h','.ld')}, from40PatchSHA256=sha(work/'from-40.patch'), hostTestShimSHA256=sha(work/'tools/hosttest/shim.c'), stackHighWaterMeasured=False)
stack = []
for path in sorted(work.glob('*.su')):
    for line in path.read_text().splitlines():
        fields = line.split('\t')
        if len(fields) == 3:
            stack.append(dict(function=fields[0].rsplit(':',1)[-1], bytes=int(fields[1]), kind=fields[2]))
result['compilerStackUsage'] = stack
result['homingDiagnosticTail'] = {**frozen['homingDiagnosticTail'], 'versionScope':'4.1.0', 'tagInheritedFrom':'4.0.0'}
result['releaseADCTelemetryOmitted'] = True
result['referenceQualification'] = frozen['referenceQualification']
result['crashDiagnostics'] = dict(recordType=5, pageBytes=64, checkpointBytes=48,
    retainedAddress=0x20003fc0, retainedBytes=56, noRuntimeErase=True,
    crashRecordWritesBeforeProtocolOnly=True, watchdogNominalSeconds=4,
    healthCheckpointIntervalTicks=250, foregroundHealthOnly=True,
    coldPowerLossBeforePersistenceCovered=False, physicalRetentionQualified=False,
    resetLatchBeforeMotorAndProtocol=True, hardFaultExactCrashFrameCaptured=False)
(work/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key not in ('sources','laneInputs','compilerStackUsage','units','flags')}, indent=2))
