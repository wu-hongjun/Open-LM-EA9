#!/usr/bin/env python3
"""Reuse pinned regression fixtures with explicit 3.7 identity/host-ABI bindings.

Only private runner copies change. Test cases, expected outcomes and production
source remain intact. This avoids copying the same regression suite per release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
config = json.loads((HERE / 'test-inputs.json').read_text())
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--case', required=True, choices=config['templates'])
p.add_argument('--build', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
build, out = a.build.resolve(), a.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
manifest = json.loads((build / 'manifest.json').read_text())
assert sha(build / 'manifest.json') == config['manifestSHA256']
assert sha(build / 'contax-zeiss-50-f1-4.bin') == config['imageSHA256']
assert manifest['loaderVersion'] == config['version']
for name, digest in manifest['sources'].items(): assert sha(build / name) == digest, name
assert sha(build / 'tools/hosttest/shim.c') == manifest['hostTestShimSHA256']
out.mkdir(exist_ok=False)
runner_dir = out / 'runners'
runner_dir.mkdir()
rebindings = []

def generate(case):
    spec = config['templates'][case]
    template = ROOT / spec['path']
    assert sha(template) == spec['sha256'], template
    original = template.read_text()
    text = original.replace('__file__', repr(str(template)))
    compatibility = HERE/'compiler_compat.py'
    compat_source = HERE/'trace_compat.c'
    assert sha(compatibility) == config['compilerCompatibilitySHA256']
    assert sha(compat_source) == config['traceCompatibilitySHA256']
    assert sha(HERE/'packet_test_init.c') == config['packetInitializerTestAdapterSHA256']
    text = ('import runpy as _trace_runpy\n_trace_runpy.run_path(' + repr(str(compatibility)) + ')["install"](' + repr(str(compat_source)) + ', ' + repr(str(build/'src')) + ')\n') + text
    edits = ['original fixture location retained', 'weak observation-only ABI mocks on clang executable links; real v3 paths tested separately']
    if '[3,5,0]' in text:
        assert text.count('[3,5,0]') == 1
        text = text.replace('[3,5,0]', '[3,7,0]')
        edits.append('expected input version 3.5 to 3.7')
    if case in ('target-time-composition', 'exact-counter-parity'):
        text = text.replace('04a70e2ccfd08badb90da4bccc2a2ac3c2da793078beefb942b50c093c868632', config['imageSHA256'])
        text = text.replace('a44ec01051f50f2bface355d526c083de385be329dc49e3a648e3a7914cb39de', config['manifestSHA256'])
        edits.append('exact new image and manifest identity')
    if case == 'target-time-composition':
        old = 'unsigned test_fault(void){return fault;}'
        assert text.count(old) == 1
        text = text.replace(old, 'unsigned test_fault(void){return s.fault;}')
        edits.append('test-only first-fault accessor bound to v3 summary storage')
    if case == 'exact-counter-parity':
        fixture = template.with_name('test_counter.c')
        assert sha(fixture) == config['counterFixtureSHA256']
        original_fixture = fixture.read_text()
        old = 'writes>=10 && writes<=13 && writes==1u+(memory[46]+3u)/4u'
        assert original_fixture.count(old) == 1
        rebound_fixture = original_fixture.replace(old,
            'writes>=4 && writes<=12 && writes==1u+memory[49]+(memory[48]+3u)/4u')
        assert rebound_fixture.count('"E9S2"') == 1
        rebound_fixture = rebound_fixture.replace('"E9S2"', '"E9S3"')
        rebound = runner_dir/'test_counter37.c'
        rebound.write_text(rebound_fixture)
        old = "HERE/'test_counter.c'"
        assert text.count(old) == 1
        text = text.replace(old, repr(str(rebound)))
        edits.append('diagnostic assertions use v3 summary/motion/event plan; control/wire/predictor assertions unchanged')
    if case in ('motion-tracing', 'capture-retention'):
        text = 'import sys as _trace_sys\n_trace_sys.path.insert(0, '+repr(str(template.parent))+')\n'+text
        edits.append('original local helper import retained')
    if case == 'motion-tracing':
        old = 'source=a.source.resolve();out=a.output.resolve()'
        assert text.count(old) == 1
        text = text.replace(old, old+'\n    exact=source;source=ROOT/"artifacts/private/handoff36-repeat"')
        old = "w=out/variant;shutil.copytree(source/'src',w/'src');shutil.copytree(source/'tools',w/'tools')"
        assert text.count(old) == 1
        text = text.replace(old, "w=out/variant; selected=exact if variant!='frozen' else source;shutil.copytree(selected/'src',w/'src');shutil.copytree(selected/'tools',w/'tools')")
        assert text.count("if variant!='frozen':apply(w/'src')") == 1
        text = text.replace("if variant!='frozen':apply(w/'src')", "if variant!='frozen':pass # exact composed source, no reapplication")
        old = "if case in ('arrival','deadband'):assert d['completion_state']==1 and d['completion_code']==0x1d"
        assert text.count(old) == 1
        text = text.replace(old, "if case in ('arrival','deadband'):assert d['completion_state']==2 and d['completion_code']==0x1d")
        text = text.replace("    (HERE/'results.json').write_text(json.dumps(report,indent=2)+'\\n')\n", '')
        edits.append('exact final source for proposal/mutations; real lane34 queue hook advances successful attempt to queued; control/wire and guard assertions unchanged')
    if case == 'capture-retention':
        old = "expected=json.loads((HERE/'results.json').read_text())['proposalEmountSHA256']"
        assert text.count(old) == 1
        text = text.replace(old, 'expected='+repr(manifest['sources']['src/emount.c']))
        old = '''old='''+"'''"+'''
        || ((kind==ST_OWNER_CS || kind==ST_OWNER_PHASE) && !(cls&1u))
        || ((kind==ST_TX_START || kind==ST_TX_RETURN) && !(cls&6u))'''+"'''"+''';assert s.count(old)==1;q.write_text(s.replace(old,''))'''
        new = '''old='''+"'''"+'''if (((kind==ST_OWNER_CS || kind==ST_OWNER_PHASE) && !(cls&1u))
        || ((kind==ST_TX_START || kind==ST_TX_RETURN) && !(cls&6u)))'''+"'''"+''';assert s.count(old)==1;q.write_text(s.replace(old,'if ((void)cls, 0)'))'''
        assert text.count(old) == 1
        text = text.replace(old, new)
        text = text.replace("(HERE/'retention-results.json').write_text(json.dumps(report,indent=2)+'\\n');", '')
        edits.append('exact compact emount identity and equivalent relocated core-filter mutant; assertions unchanged')
    if case == 'startup-handoff':
        text = text.replace('d8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f', config['imageSHA256'])
        old = "assert cm['baseImageSHA256'] == m['imageSHA256']"
        assert text.count(old) == 1
        text = text.replace(old, "assert cm['baseImageSHA256'] == 'd8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f'")
        edits.append('new candidate identity and immediate base; original 3.5 frozen/proposal startup controls retained')
    if case == 'query-ownership':
        old = "shutil.copytree(BASE/'tools',work/'tools')"
        assert text.count(old) == 1
        text = text.replace(old, "shutil.copytree((composed if label=='proposal' else BASE)/'tools',work/'tools')")
        edits.append('new EIC host ABI on exact proposal only')
    if case == 'query-flow':
        old = "shutil.copytree(BASE/'tools',work/'tools')"
        assert text.count(old) == 1
        text = text.replace(old, "shutil.copytree((composed if label in ('proposal','mutant-home-gate') else BASE)/'tools',work/'tools')")
        edits.append('new EIC host ABI on exact proposal and its mutant only')
    destination = runner_dir / template.name
    destination.write_text(text)
    rebindings.append(dict(case=case, template=spec, generatedSHA256=sha(destination), changes=edits))
    return destination

if a.case == 'exact-counter-parity':
    # Its original import uses run.py's helpers and exact source identity.
    generate('target-time-composition')
runner = generate(a.case)
arguments = ['--source', str(build)]
if a.case == 'capture-commits': arguments += ['--already-applied']
if a.case == 'startup-handoff': arguments = ['--source', str(ROOT/'artifacts/private/absolute35a'), '--candidate', str(build)]
result = subprocess.run([sys.executable, str(runner), *arguments,
    '--output', str(out / 'results')], capture_output=True, text=True, cwd=ROOT, timeout=180)
(out / 'stdout.txt').write_text(result.stdout)
(out / 'stderr.txt').write_text(result.stderr)
assert result.returncode == 0, (a.case, result.returncode, result.stdout[-1000:], result.stderr[-2000:])
for name, digest in manifest['sources'].items(): assert sha(build / name) == digest, name
report = dict(status='passed-bound-37-regression-replay', case=a.case,
    imageSHA256=config['imageSHA256'], manifestSHA256=config['manifestSHA256'],
    sourceFilesVerified=len(manifest['sources']), templates=rebindings,
    hardwareReportsSent=0, cameraQualified=False)
(out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
