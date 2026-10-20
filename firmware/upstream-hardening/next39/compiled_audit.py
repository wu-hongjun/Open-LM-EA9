#!/usr/bin/env python3
"""Pinned final-image call/stack, callback, composition and NVM-path audit.

Uses the frozen reviewed 3.7 graph analyzer, adapted only for RAM3040, with 3.9
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
original = (PREVIOUS/'audit.py').read_text()
assert original.count('== 3044,') == 1 and original.count('staticRAMBytes=3044,') == 1
adapted = original.replace('== 3044,','== 3040,').replace('staticRAMBytes=3044,','staticRAMBytes=3040,')
assert hashlib.sha256(adapted.encode()).hexdigest() == policy['adaptedAnalyzerSHA256']
# Only the exact reviewed static-RAM constant changes. All unknown edges,
# recursion, image/source/.su bindings and architectural assumptions remain.
with tempfile.TemporaryDirectory(prefix='astra39-analyzer-',dir=ROOT/'artifacts/private') as td:
    adapter = Path(td)/'audit.py'
    adapter.write_text(adapted)
    assert sha(adapter) == policy['adaptedAnalyzerSHA256']
    module = {'__file__':str(PREVIOUS/'audit.py'),'__name__':'astra39_private_analyzer'}
    exec(compile(adapter.read_text(),str(adapter),'exec'),module)
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
assert m['loaderVersion'] == [3,9,0] and m['codeAndDataEnd'] == 39304 and m['codeMarginBeforeDiagnostics'] == 632
assert result['maximumAllVectorPriorityBytes'] <= 8192
assert m['staticRAMBytes'] == 3040 and m['diagnosticPages'] == 16
image = (build/'contax-zeiss-50-f1-4.bin').read_bytes()
assert len(image) == 0x5000 and image[len((build/'raw.bin').read_bytes()):] == b'\xff' * (0x5000-len((build/'raw.bin').read_bytes()))
assert m['imageSHA256'] == sha(build/'contax-zeiss-50-f1-4.bin')
assert 0x5000+len((build/'raw.bin').read_bytes()) == m['codeAndDataEnd']
base = ROOT/'artifacts/private/readiness38-repeat'
assert sha(base/'manifest.json') == policy['base38ManifestSHA256']
bm = json.loads((base/'manifest.json').read_text())
for name,pin in bm['sources'].items():
    assert sha(base/name) == pin, name
changed = sorted(name for name,pin in m['sources'].items() if bm['sources'].get(name) != pin)
assert changed == policy['sourceDeltaFrom38']
plan = json.loads((HERE/'accepted-lanes.json').read_text())
assert sha(HERE/'accepted-lanes.json') == m['acceptedPlanSHA256']
with tempfile.TemporaryDirectory(prefix='homing39-compose-',dir=ROOT/'artifacts/private') as td:
    work = Path(td)
    shutil.copytree(base/'src',work/'src')
    for entry in plan['applicators']:
        assert sha(ROOT/entry['path']) == plan['inputs'][entry['path']]
        runpy.run_path(str(ROOT/entry['path']))[entry['entry']](work)
    header = work/'src/emount.h'
    header.write_text(header.read_text().replace('0x38u','0x39u'))
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
assert not any(name in symbols for name in ('vdd_init','vdd_track_sample','vdd_track_reset','vdd_track_result','convert'))
assert symbols['trace'] % 4 == 0, 'snapshot word alignment'

assert sha(base/'hardened.elf') == policy['base38ELFSHA256']
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
def operations(body, relocations):
    out = []
    for line in body.splitlines():
        f = line.split('\t')
        if len(f)<3:
            continue
        op = f[-2].strip() if len(f)>=4 else f[2].strip()
        operand = f[-1].strip() if len(f)>=4 else ''
        operand = re.sub(r'\b[0-9a-f]+ (<[^>]+>)',r'\1',operand)
        operand = re.sub(r'@ \([^)]*\)','',operand).strip()
        if op == '.word' and operand in relocations:
            operand = '<'+relocations[operand]+'>'
        out.append((op,operand))
    return out
for name in ('powerdown_signal','st_fail','em_uart_disable','delay_ms'):
    old_literals = policy['reviewedRelocatedLiterals'][name]
    for address,symbol in old_literals.items():
        assert int(address,16) == old_symbols[symbol],(name,symbol)
    old_map = {'0x'+address:symbol for address,symbol in old_literals.items()}
    new_map = {f'0x{symbols[symbol]:08x}':symbol for symbol in old_literals.values()}
    assert operations(bodies[name],new_map) == operations(old_bodies[name],old_map),name

assert sha(PREVIOUS/'semantics.py') == policy['baseSemanticsSHA256']
sem = runpy.run_path(str(PREVIOUS/'semantics.py'))
vectors = sem['vectors'](raw,symbols)
irq_setup = {**sem['instructions'](bodies['em_eic_init']),**sem['instructions'](bodies['em_eic_start'])}
sem['setup'](irq_setup,raw,symbols)
handoff = sem['handoff_paths'](sem['instructions'](bodies['em_init']))
# Exact emitted failure-only snapshot: cutoff precedes every newly added
# collector write; all stores are aligned inside existing bytes112..143.
main_insns = sem['instructions'](bodies['main'])
for address,op,arg in (
    (0x852a,'bl','6be8 <motor_inhibit>'),
    (0x8536,'bl','9254 <st_motion_data>'),
    (0x853a,'movs','r6, r0'),(0x853c,'str','r4, [r0, #116]'),
    (0x853e,'bl','5368 <millis>'),(0x8546,'str','r3, [r6, #124]'),
    (0x8548,'adds','r3, r6, #4'),(0x854a,'str','r0, [r6, #120]'),
    (0x854c,'str','r2, [r3, #124]'),(0x8550,'adds','r3, #4'),
    (0x8552,'str','r2, [r3, #124]'),(0x8556,'adds','r3, #128'),
    (0x8558,'str','r5, [r3, #0]'),(0x855a,'str','r2, [r3, #4]'),
    (0x8566,'str','r3, [r6, #112]')):
    sem['expect'](main_insns,address,op,arg,'failed-home emitted snapshot')
assert not any(op.startswith('b') for pc,(op,arg,_) in main_insns.items() if 0x852e<=pc<0x8536)
assert symbols['trace'] + 144 == symbols['_ezero'], 'reviewed collector extent'

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
result.update(status='passed-conditional-final39-composition-bound',productionSourceDelta=changed,
    normalizedCompiledOutputSHA256=normalized,onlyContainerPinsRebound=rebound,
    exactApplicatorCompositionMatches=True,vectors=vectors,sourceGates=source_gates,
    unchangedIRQSetupAndHandoff=True,handoffPaths=handoff,failedHomeCompiledStoresAfterCutoff=True,releaseADCCodeDiscarded=True,
    unchangedTerminalAndWaitInstructionOperations=True,
    baseAnalyzerSHA256=policy['baseAnalyzerSHA256'],adaptedAnalyzerSHA256=policy['adaptedAnalyzerSHA256'],
    auditRunnerSHA256=sha(Path(__file__)),reviewedPolicySHA256=sha(reviewed_path),
    reproductionContractSHA256=sha(HERE/'stack-reproduction.json'),reviewedLibraryStackOperationsUnchanged=True,
    compiledNVMCallerGates={name:callers(name) for name in expected},negativeControls=controls,
    hardwareReportsSent=0,cameraQualified=False)
with a.output.open('x') as handle:
    json.dump(result,handle,indent=2)
    handle.write('\n')
print(json.dumps({key:result[key] for key in ('status','maximumAllVectorPriorityBytes','staticRAMBytes','sourceHashesVerified','unresolvedCompiledEdges','recursiveComponents')},indent=2))
