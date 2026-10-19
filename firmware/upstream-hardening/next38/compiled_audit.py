#!/usr/bin/env python3
"""Pinned final-image call/stack, callback, composition and NVM-path audit.

Uses the unchanged reviewed 3.7 graph analyzer with explicitly reviewed 3.8
callback addresses. Repeat-build container pins may be rebound only after exact
image/source pins and normalized compiled outputs match the reviewed build.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import runpy
import shutil
import struct
import subprocess
import tempfile

if not __debug__:
    raise SystemExit('Optimized Python disables required audit assertions; use ordinary python3.')

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = HERE.parent/'followup/38-exact37-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--build', type=Path, required=True)
p.add_argument('--policy', type=Path, default=HERE/'compiled-policy.json')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
build = a.build.resolve()
assert build.is_relative_to(ROOT/'artifacts/private') and a.output.resolve().is_relative_to(ROOT/'artifacts/private')
policy = json.loads(a.policy.read_text())
review = json.loads((HERE/'stack-reproduction.json').read_text())
reviewed_path = HERE/'compiled-policy.json'
assert sha(reviewed_path) == review['reviewedPolicySHA256']
reviewed = json.loads(reviewed_path.read_text())
container_names = ('hardened.elf','hardened.map')
# A supplied reproduction policy cannot alter graph edges, frame bounds, source
# pins or any other part of the independently reviewed policy.
comparison = copy.deepcopy(policy)
for name in container_names:
    comparison['pins'][name] = reviewed['pins'][name]
assert comparison == reviewed, 'Only ELF/map container pins may differ'
assert sha(PREVIOUS/'audit.py') == policy['baseAnalyzerSHA256']
module = runpy.run_path(str(PREVIOUS/'audit.py'))
tool = str(module['TOOL'])
assert sha(Path(tool)) == review['objdumpSHA256']
for name,pin in reviewed['pins'].items():
    if name not in container_names:
        assert sha(build/name) == pin, name
normalized = {}
for option,pin in review['normalizedOutputSHA256'].items():
    value = subprocess.check_output([tool,option,str(build/'hardened.elf')],text=True)
    # objdump prints its input path on one header line. No instructions,
    # symbols, addresses, sections or other content are normalized away.
    value = value.replace(str(build/'hardened.elf'),'<ELF>')
    digest = hashlib.sha256(value.encode()).hexdigest()
    assert digest == pin, ('Reviewed compiled output differs',option,digest)
    normalized[option] = digest
rebound = {}
for name in container_names:
    actual = sha(build/name)
    if actual != reviewed['pins'][name]:
        rebound[name] = dict(reviewed=reviewed['pins'][name],reproduced=actual)
    policy['pins'][name] = actual
result = module['audit'](build, policy, 8192)
m = json.loads((build/'manifest.json').read_text())
assert m['loaderVersion'] == [3,8,0] and m['codeAndDataEnd'] == 39600 and m['codeMarginBeforeDiagnostics'] == 336
assert result['maximumAllVectorPriorityBytes'] <= 8192
base = ROOT/'artifacts/private/targeted37-repeat'
bm = json.loads((base/'manifest.json').read_text())
for name,pin in bm['sources'].items():
    assert sha(base/name) == pin, name
changed = sorted(name for name,pin in m['sources'].items() if bm['sources'].get(name) != pin)
assert changed == policy['sourceDeltaFrom37']
plan = json.loads((HERE/'accepted-lanes.json').read_text())
assert sha(HERE/'accepted-lanes.json') == m['acceptedPlanSHA256']
with tempfile.TemporaryDirectory(prefix='readiness38-compose-',dir=ROOT/'artifacts/private') as td:
    work = Path(td)
    shutil.copytree(base/'src',work/'src')
    for entry in plan['applicators']:
        assert sha(ROOT/entry['path']) == plan['inputs'][entry['path']]
        runpy.run_path(str(ROOT/entry['path']))[entry['entry']](work)
    header = work/'src/emount.h'
    header.write_text(header.read_text().replace('0x37u','0x38u'))
    assert sorted('src/'+p.name for p in (work/'src').iterdir() if p.suffix in ('.c','.h','.ld')) == sorted(m['sources'])
    for name in m['sources']:
        assert (work/name).read_bytes() == (build/name).read_bytes(),name

def inspect(folder):
    asm = subprocess.check_output([tool,'-d',str(folder/'hardened.elf')],text=True)
    heads = list(re.finditer(r'^([0-9a-f]+) <(.+)>:\n',asm,re.M))
    bodies = {match[2]:asm[match.end():heads[i+1].start() if i+1<len(heads) else len(asm)].strip() for i,match in enumerate(heads)}
    symbols = {}
    for line in subprocess.check_output([tool,'-t',str(folder/'hardened.elf')],text=True).splitlines():
        f = line.split()
        if len(f)>=5 and re.fullmatch('[0-9a-f]{8}',f[0]):
            symbols[f[-1]] = int(f[0],16)
    return bodies,symbols
bodies,symbols = inspect(build)
old_bodies,old_symbols = inspect(base)
raw = (build/'raw.bin').read_bytes()
word = lambda address:struct.unpack_from('<I',raw,address-0x5000)[0]
for offset,name in ((48,'pump'),(52,'focus_retarget'),(56,'focus_abort')):
    assert word(symbols['STOCK']+offset) == symbols[name]|1
assert symbols['__preinit_array_start'] == symbols['__preinit_array_end'] == symbols['__init_array_start']
assert symbols['__init_array_end']-symbols['__init_array_start'] == 4
assert word(symbols['__init_array_start']) == symbols['frame_dummy']|1
assert all(word(at)==symbols['__TMC_END__'] for at in (0x50c8,0x50cc,0x50f0,0x50f4))
assert word(0x50d0) == word(0x50f8) == 0
for address,name in policy['reviewedMainCallbackLiterals'].items():
    assert word(int(address,16)) == symbols[name]|1
assert word(0x56e0) == word(0x5ab0) == symbols['g_powerdown']
assert word(0x59d4) == word(0x5a98) == symbols['g_shutdown_inhibit']
assert word(0x69d4) == symbols['g_cs_edge'] and word(0x69dc) == symbols['g_vd_edge']

def normalize_stack(lines):
    return [re.sub(r'^\s*[0-9a-f]+:\s+[0-9a-f]+\s+','',line).strip() for line in lines]
for name,old in policy['baselineLibraryStackInstructions'].items():
    new = [line.strip() for line in bodies[name].splitlines() if re.search(r'\b(push|pop)\b|\bsp\b',line)]
    assert normalize_stack(new) == normalize_stack(old),name
def operations(body):
    out = []
    for line in body.splitlines():
        f = line.split('\t')
        if len(f)<3:
            continue
        op = f[-2].strip() if len(f)>=4 else f[2].strip()
        operand = f[-1].strip() if len(f)>=4 else ''
        operand = re.sub(r'\b[0-9a-f]+ (<[^>]+>)',r'\1',operand)
        operand = re.sub(r'@ \([^)]*\)','',operand).strip()
        out.append((op,operand))
    return out
for name in ('powerdown_signal','st_fail','em_uart_disable','delay_ms'):
    assert operations(bodies[name]) == operations(old_bodies[name]),name

sem = runpy.run_path(str(PREVIOUS/'semantics.py'))
vectors = sem['vectors'](raw,symbols)
source_gates = sem['source_gates'](build)
edges = {(call['caller'],target) for call in result['calls'] for target in call['targets']}
callers = lambda target:sorted(caller for caller,callee in edges if callee==target)
expected = {'st_flush':['powerdown_signal','st_fail'],'st_terminal':['powerdown_signal','st_fail'],
    'append':['st_flush','st_terminal'],'st_write_page':['append'],'st_read_page':['append','st_init']}
for name,owners in expected.items():
    assert callers(name)==owners,name
def descendants(name,seen=None):
    seen = set() if seen is None else seen
    if name in seen:
        return seen
    seen.add(name)
    for caller,callee in edges:
        if caller==name:
            descendants(callee,seen)
    return seen
for root in ('EIC_Handler','SERCOM1_Handler','SysTick_Handler','st_summary','st_record','st_motion_completion'):
    assert not descendants(root)&{'st_flush','st_terminal','st_write_page','st_read_page','append','st_fail'},root
controls = []
for name,edit in (('unknown-indirect',lambda q:q['indirectCalls'].pop('74a8')),
    ('unknown-library',lambda q:q['libraryFrames'].pop('memcpy')),
    ('recursive-callback',lambda q:q['indirectCalls']['74a8'].__setitem__('targets',['servo_move_from'])),
    ('wrong-image-pin',lambda q:q['pins'].__setitem__('contax-zeiss-50-f1-4.bin','0'*64))):
    bad = copy.deepcopy(policy)
    edit(bad)
    try:
        module['audit'](build,bad,8192)
    except ValueError as error:
        controls.append(dict(case=name,rejected=True,reason=str(error)))
    else:
        raise AssertionError('Bad compiled policy accepted: '+name)
result.update(status='passed-conditional-final38-composition-bound',productionSourceDelta=changed,
    normalizedCompiledOutputSHA256=normalized,onlyContainerPinsRebound=rebound,
    exactApplicatorCompositionMatches=True,vectors=vectors,sourceGates=source_gates,
    unchangedTerminalAndWaitInstructionOperations=True,reviewedLibraryStackOperationsUnchanged=True,
    compiledNVMCallerGates={name:callers(name) for name in expected},negativeControls=controls,
    hardwareReportsSent=0,cameraQualified=False)
with a.output.open('x') as handle:
    json.dump(result,handle,indent=2)
    handle.write('\n')
print(json.dumps({key:result[key] for key in ('status','maximumAllVectorPriorityBytes','staticRAMBytes','sourceHashesVerified','unresolvedCompiledEdges','recursiveComponents')},indent=2))
