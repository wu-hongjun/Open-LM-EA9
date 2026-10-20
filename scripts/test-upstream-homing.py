#!/usr/bin/env python3
"""Final 3.9 offline acceptance. Supplied schedules never qualify a camera."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if not __debug__:
    raise SystemExit('Optimized Python disables required acceptance assertions; use ordinary python3.')

ROOT = Path(__file__).resolve().parents[1]
NEXT = ROOT/'firmware/upstream-hardening/next39'
FOLLOW = ROOT/'firmware/upstream-hardening/followup'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--skip-compiled',action='store_true',help='Explicit partial run while compiled policy is being reviewed; never final acceptance')
a = p.parse_args()
build,out = a.build.resolve(),a.output.resolve()
assert build.is_relative_to(ROOT/'artifacts/private') and out.is_relative_to(ROOT/'artifacts/private')
out.mkdir(exist_ok=False)
sha = lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
test_paths = [Path(__file__).resolve(), NEXT/'accepted-lanes.json', NEXT/'test-inputs.json',
    NEXT/'contract-fixtures.json', NEXT/'compiled-policy.json', NEXT/'stack-reproduction.json']
test_paths += [path for path in NEXT.iterdir() if path.suffix in ('.py','.c')]
for lane in ('45-home-drive','46-shutter-readiness','48-release-adc','43-capture-status','44-shutdown-liveness'):
    test_paths += [path for path in (FOLLOW/lane).iterdir() if path.suffix in ('.py','.c','.inc')]
test_paths += [ROOT/'scripts'/name for name in ('decode-startup-diagnostics.py','startup_diagnostic_registry.py','startup_diagnostic_v3.py')]
test_pins = {str(path.relative_to(ROOT)):sha(path) for path in test_paths}
m = json.loads((build/'manifest.json').read_text())
cfg = json.loads((NEXT/'test-inputs.json').read_text())
assert m['loaderVersion'] == cfg['version'] == [3,9,0]
assert m['imageSHA256'] == cfg['imageSHA256'] == '87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44'
assert sha(build/'manifest.json') == cfg['manifestSHA256'] == '9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a'
published = ROOT/'firmware/candidates/3.9.0'
assert (build/'manifest.json').read_bytes() == (published/'contax-zeiss-50-f1-4.manifest.json').read_bytes()
image = (build/'contax-zeiss-50-f1-4.bin').read_bytes()
assert image == (published/'contax-zeiss-50-f1-4.bin').read_bytes() == (ROOT/'apps/macos/Sources/DeviceKit/Resources/ea9-af-homing-upstream.bin').read_bytes()
assert len(image)==20480 and image[0x4c00:]==b'\xff'*1024
assert hashlib.sha256(image).hexdigest()==m['imageSHA256']
assert sha(build/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
for name,pin in m['sources'].items():
    assert sha(build/name)==pin,name
rows=[]
def run(name,command,timeout=240):
    r=subprocess.run(list(map(str,command)),cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    (out/(name+'.stdout')).write_text(r.stdout)
    (out/(name+'.stderr')).write_text(r.stderr)
    assert r.returncode==0,(name,r.returncode,r.stdout[-800:],r.stderr[-1800:])
    rows.append(dict(name=name,exitCode=0))
    print(name+': PASS',flush=True)
py=sys.executable
for case in cfg['templates']:
    run(case,[py,NEXT/'replay.py','--case',case,'--build',build,'--output',out/case])
run('home-drive',[py,FOLLOW/'45-home-drive/run.py','--candidate',build,'--output',out/'astra45-home'])
run('shutter-readiness',[py,FOLLOW/'46-shutter-readiness/run.py','--candidate',build,'--output',out/'astra46-readiness'])
run('release-adc',[py,FOLLOW/'48-release-adc/run.py','--candidate',build,'--output',out/'release-adc'])
run('capture-status',[py,FOLLOW/'43-capture-status/run.py','--candidate',build,'--output',out/'astra43-capture'])
shutdown=FOLLOW/'44-shutdown-liveness/run.py'
text=shutdown.read_text()
assert text.count('[[3,7,0],[3,8,0]]')==1
text=text.replace('[[3,7,0],[3,8,0]]','[[3,7,0],[3,8,0],[3,9,0]]').replace('__file__',repr(str(shutdown)))
shutdown_copy=out/'shutdown39.py';shutdown_copy.write_text(text)
run('shutdown-liveness',[py,shutdown_copy,'--source',build,'--manifest',published/'contax-zeiss-50-f1-4.manifest.json','--output',out/'astra44-shutdown'])
# Preserve the historical public receipt: only its duplicate write is removed.
# The pinned original-instruction replay, controls and private output remain.
factory=FOLLOW/'43-capture-status/factory_replay.py'
assert sha(factory)=='127dd4256ea316091d432e98272d162e4629d305cbab2721ee11b4bc31b63a31'
text=factory.read_text()
duplicate="(HERE/'factory-results.json').write_text(json.dumps(result,indent=2)+'\\n')"
assert text.count(duplicate)==1
text=text.replace(duplicate,'').replace('__file__',repr(str(factory)))
factory_copy=out/'factory39.py'
factory_copy.write_text(text)
run('factory-capture-rearm',[ROOT/'tools/rea-analysis/venv/bin/python',factory_copy,'--output',out/'factory-capture-rearm'])
run('trace-core',[py,FOLLOW/'35-targeted-trace/run.py','--source',build,'--output',out/'trace-core'])
# The frozen historical runner also writes its own public baseline receipt.
# A private copy suppresses only that duplicate write; its private receipt and
# every production replay, byte comparison and negative control remain intact.
compact=FOLLOW/'36-trace-footprint/run.py'
assert sha(compact)=='2a5a9c895c6099b5a9f0fc6be12c0dd85f48daad3ba6b6f938b48886df68ff31'
text=compact.read_text()
duplicate=";(HERE/'results.json').write_text(json.dumps(report,indent=2)+'\\n')"
assert text.count(duplicate)==1
text=text.replace(duplicate,'').replace('__file__',repr(str(compact)))
text='import sys\nsys.path.insert(0,'+repr(str(compact.parent))+')\n'+text
compact_copy=out/'compaction39.py'
compact_copy.write_text(text)
run('capture-compaction',[py,compact_copy,'--source',build,'--output',out/'capture-compaction'])
arm_py=ROOT/'tools/rea-analysis/venv/bin/python'
run('packet-reset',[arm_py,FOLLOW/'37-packet-initializer/run.py','--source',build,'--output',out/'packet-reset.json'])

# Private copies add only the admitted new version to a frozen instruction test
# and bind the registry test to new candidate identity. Original checks stay.
writer=ROOT/'scripts/test-startup-flash-arm.py'
text=writer.read_text()
old="'3.6.0','3.7.0']"
assert text.count(old)==1
text=text.replace(old,"'3.6.0','3.7.0','3.8.0','3.9.0']").replace('__file__',repr(str(writer)))
writer_copy=out/'writer39.py'
writer_copy.write_text(text)
run('compiled-writer',[arm_py,writer_copy,'--version','3.9.0','--build',build,'--output',out/'compiled-writer.json'])
run('decoder-v3',[py,ROOT/'firmware/upstream-hardening/next37/test_decoder.py','--fixture',out/'trace-core/synthetic.bin','--output',out/'decoder-v3'])
run('decoder-adversarial',[py,FOLLOW/'39-decoder-host-review/test_adversarial.py','--fixture',out/'trace-core/synthetic.bin','--output',out/'decoder-adversarial.json'])
run('decoder-phase',[py,NEXT.with_name('next38')/'test_phase_decoder.py','--output',out/'decoder-phase.json'])
run('decoder-homing',[py,NEXT/'test_homing_decoder.py','--output',out/'decoder-homing.json'])
registry=FOLLOW/'39-decoder-host-review/test_registry.py'
text=registry.read_text().replace('__file__',repr(str(registry)))
text=text.replace('3.7.0','3.9.0').replace('(3,7,0)','(3,9,0)')
text=text.replace('6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5',m['imageSHA256'])
text=text.replace('15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b',sha(build/'manifest.json'))
registry_copy=out/'registry39.py'
registry_copy.write_text(text)
run('decoder-registry39',[py,registry_copy,'--output',out/'decoder-registry39.json'])
text38=registry.read_text().replace('__file__',repr(str(registry))).replace('3.7.0','3.8.0').replace('(3,7,0)','(3,8,0)').replace('6a7faa368ecd83a6af530bba0b8574c70342350313d590329cb0176cca946ba5','8864577453c93e4b0eb4d4d29d0d7de80656cbe075a4c7a1090e8083eff299b9').replace('15a3a59c5f5f75553f69f5bcd23f8ecc23178cb50700eeef2b19b18a46ac801b','be9211016ec96539a79389e1d7ef4381a8e61c91a408d66d74dbb8a0ab6a35f0')
registry38=out/'registry38.py';registry38.write_text(text38)
run('decoder-registry38',[py,registry38,'--output',out/'decoder-registry38.json'])
run('decoder-registry37',[py,registry,'--output',out/'decoder-registry37.json'])
run('decoder-legacy',[py,ROOT/'firmware/upstream-hardening/next36/test_decoder.py','--output',out/'decoder-legacy'])
if not a.skip_compiled:
    run('compiled-composition',[py,NEXT/'compiled_audit.py','--build',build,'--output',out/'compiled-composition.json'])

ledger=json.loads((ROOT/'docs/evidence/upstream-39-preserved-2026-10-20.json').read_text())
for pin in ledger['artifacts']:
    value=(ROOT/pin['path']).read_bytes()
    assert len(value)==pin['bytes'] and hashlib.sha256(value).hexdigest()==pin['sha256'],pin['path']
registry_values=json.loads((ROOT/'firmware/candidates/diagnostic-registry.json').read_text())['versions']
for version,value in ledger['historicalDiagnosticRegistryEntries'].items():
    assert registry_values[version]==value,version
assert sha(build/'manifest.json')==cfg['manifestSHA256']
assert (build/'manifest.json').read_bytes()==(published/'contax-zeiss-50-f1-4.manifest.json').read_bytes()
image=(build/'contax-zeiss-50-f1-4.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()==m['imageSHA256']
assert len(image)==20480 and image[0x4c00:]==b'\xff'*1024
assert image==(published/'contax-zeiss-50-f1-4.bin').read_bytes()==(ROOT/'apps/macos/Sources/DeviceKit/Resources/ea9-af-homing-upstream.bin').read_bytes()
assert sha(build/'tools/hosttest/shim.c')==m['hostTestShimSHA256']
for name,pin in m['sources'].items():
    assert sha(build/name)==pin,name
for name,pin in test_pins.items():
    assert sha(ROOT/name)==pin,name
report=dict(status=('partial39-offline-compiled-audit-skipped' if a.skip_compiled else 'passed-final39-offline-acceptance-camera-unqualified'),compiledAuditSkipped=a.skip_compiled,imageSHA256=m['imageSHA256'],manifestSHA256=sha(build/'manifest.json'),sourceFilesVerified=len(m['sources']),checks=rows,preservedArtifacts=ledger['checkedArtifacts'],historicalRegistryEntriesUnchanged=True,testInputSHA256=test_pins,hardwareReportsSent=0,cameraQualified=False,physicalHomingFailureFixed=False,cameraFreezeFixEstablished=False,limits='Supplied I/O and schedules; no measured motor/IRQ/NVM timing, focus accuracy or camera capture/shutdown acceptance.')
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='checks'},indent=2))
