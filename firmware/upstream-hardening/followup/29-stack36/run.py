#!/usr/bin/env python3
"""Read-only exact 3.6 stack audit; all mutations are private evidence controls."""
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
import handoff

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent / '22-stack35/audit.py'
ANALYZER = HERE / 'audit.py'
BASE_SHA = '799c472f32e6be1b9ac3d7eee46d521b6fb8a5ae8cdfa0775d6eaab4d1a43806'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
canonical_hash = lambda obj: hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_derivative(policy):
    require(sha(BASE) == BASE_SHA == policy['baseAnalyzerSHA256'], 'frozen analyzer changed')
    expected = BASE.read_text().replace(
        "DEFAULT_BUILD = ROOT / 'artifacts/private/absolute35a'",
        "DEFAULT_BUILD = ROOT / 'artifacts/private/handoff36a'").replace(
        '== 3072,', '== 3064,').replace('staticRAMBytes=3072,', 'staticRAMBytes=3064,')
    require(ANALYZER.read_text() == expected, 'unexpected derivative analyzer change')
    require(sha(ANALYZER) == policy['analyzerSHA256'], 'derivative analyzer pin mismatch')
    require(sha(HERE/'handoff.py') == policy['handoffVerifierSHA256'], 'handoff verifier pin mismatch')
    for name,digest in policy['referencePins'].items():
        require(sha(ROOT/name)==digest,'reference pin mismatch: '+name)


def reviewed_audit(build, policy, budget):
    result = audit(build, policy, budget)
    manifest = json.loads((build/'manifest.json').read_text())
    require(manifest['imageSHA256'] == sha(build/'contax-zeiss-50-f1-4.bin'), 'manifest image identity mismatch')
    baseline = json.loads((ROOT/'firmware/candidates/3.5.0/contax-zeiss-50-f1-4.manifest.json').read_text())
    changed = sorted(name for name in manifest['sources'] if manifest['sources'][name] != baseline['sources'].get(name))
    require(changed == ['src/em_eic.c','src/em_eic.h','src/emount.c','src/emount.h'], 'unexpected source delta from frozen35')
    oldframes = {r['function']:r for r in baseline['compilerStackUsage']}
    newframes = {r['function']:r for r in manifest['compilerStackUsage']}
    require({n:r for n,r in newframes.items() if n!='em_eic_start'} == oldframes and
            newframes['em_eic_start'] == dict(function='em_eic_start',bytes=0,kind='static'),
            'unexpected compiler-frame delta from frozen35')
    require(len((build/'raw.bin').read_bytes()) == manifest['rawBytes'] == 19188 and
            manifest['codeAndDataEnd'] == 0x5000+19188 == 39668 and
            manifest['codeMarginBeforeDiagnostics'] == 39936-39668 == 268,
            'code/data footprint mismatch')
    result['frozen35SourceDelta'] = changed
    result['existingCompilerFrameSizesUnchanged'] = len(oldframes)
    result['codeAndDataEnd'] = manifest['codeAndDataEnd']
    result['codeMarginBeforeDiagnostics'] = manifest['codeMarginBeforeDiagnostics']
    for key, value in policy['expectedLayout'].items():
        require(result[key] == value, 'reviewed layout mismatch: '+key)
    for key, value in policy['expectedInventory'].items():
        require(result[key] == value, 'compiled inventory mismatch: '+key)
    require(canonical_hash(result['calls']) == policy['callsSHA256'], 'reviewed call inventory mismatch')
    require(result['unknowns'] == policy['requiredPhysicalCaveats'] and len(result['unknowns']) == 4,
            'physical caveats missing or changed')
    require('servo_move_rel' not in result['functionBounds'], 'relative wrapper unexpectedly linked')
    require('em_frame_period_n' not in subprocess.check_output(
        [str(module['TOOL']), '-t', str(build/'hardened.elf')], text=True, timeout=30),
        'legacy counter unexpectedly linked')
    raw = (build/'raw.bin').read_bytes()
    for address, word in policy['reviewedRawWords'].items():
        actual = struct.unpack_from('<I', raw, int(address,16)-0x5000)[0]
        require(actual == int(word,16), 'reviewed callback/literal mismatch: '+address)
    asm = subprocess.check_output([str(module['TOOL']), '-d', str(build/'hardened.elf')], text=True, timeout=30)
    headers = list(re.finditer(r'^([0-9a-f]+) <(.+)>:\n', asm, re.M))
    bodies = {m[2]: asm[m.end():headers[i+1].start() if i+1<len(headers) else len(asm)].strip()
              for i,m in enumerate(headers)}
    starts = {m[2]: '0x'+m[1] for m in headers}
    require(set(policy['libraryFrameEvidence']) == set(policy['libraryFrames']), 'library evidence inventory mismatch')
    for name, evidence in policy['libraryFrameEvidence'].items():
        require(evidence['localBytes'] == policy['libraryFrames'][name], 'reviewed library frame mismatch: '+name)
        require(evidence['start'] == starts[name] and evidence['bodySHA256'] == hashlib.sha256(bodies[name].encode()).hexdigest(),
                'reviewed library body mismatch: '+name)
        stack = [line.strip() for line in bodies[name].splitlines() if re.search(r'\b(push|pop)\b|\bsp\b',line)]
        require(stack == evidence['stackInstructions'], 'reviewed library stack instructions mismatch: '+name)
    edges = {(r['caller'], t) for r in result['calls'] for t in r['targets']}
    bounds = result['functionBounds']
    servo = ['Reset_Handler','main','focus_exec','focus_run.isra.0','servo_move_from','pump']
    home = ['Reset_Handler','main','pump']
    chains = {}
    for name, prefix in [('servo',servo),('inlined-homing',home)]:
        for conversion, tail in [
            ('position-to-distance',['focus_answer_queries','focus_distance_code','distance_mm','__udivsi3','__aeabi_idiv0']),
            ('distance-to-position',['focus_answer_queries','focus_counts_for_code','focus_exp2_q6']),
            ('predictor',['focus_pred_sample','__divsi3','__aeabi_idiv0'])]:
            chain=prefix+tail
            require(all(e in edges for e in zip(chain,chain[1:])), 'reviewed path changed: '+name+'/'+conversion)
            chains[name+'/'+conversion] = dict(bytes=sum(bounds[n]['frameBytes'] for n in chain),chain=chain)
    result['explicitChangedPaths'] = chains
    result['releasedRelativeWrapperLinked'] = False
    result['relativeWrapperCompilerFrameBytes'] = next(r['bytes'] for r in manifest['compilerStackUsage'] if r['function']=='servo_move_rel')
    result['reviewedLibraryBodies'] = len(policy['libraryFrames'])
    result['reviewedRawWords'] = len(policy['reviewedRawWords'])
    symbols = {line.split()[-1]:int(line.split()[0],16) for line in subprocess.check_output(
        [str(module['TOOL']), '-t', str(build/'hardened.elf')],text=True).splitlines()
        if len(line.split())>=5 and re.fullmatch('[0-9a-f]{8}',line.split()[0])}
    require(all(n not in symbols for n in ('em_rx_bytes_at_open','em_rx_bytes_at_close')),
            'legacy RX snapshot unexpectedly linked')
    require(symbols['_sstack']==symbols['_ezero'] and symbols['_sstack']%8==0,
            'unexpected stack alignment gap')
    result['compiledHandoff'] = handoff.verify(bodies,raw,symbols,policy)
    result['exceptionBudget'] = dict(coreWords=8,alignmentWords=1,bytesPerFrame=36,configurablePriorityLevels=4,
                                     additionalHardFaultAndNMI=2,totalFrames=6,totalBytes=216)
    return result


def guards(build, policy, budget, result):
    site='721c'
    cases = [
        ('insufficient-budget',None,result['maximumAllVectorPriorityBytes']-1,'exceeds budget'),
        ('missing-pump-callback',lambda p:p['indirectCalls'].pop(site),budget,'unknown indirect call'),
        ('missing-library-frame',lambda p:p['libraryFrames'].pop('memcpy'),budget,'unknown library frame'),
        ('wrong-elf-pin',lambda p:p['pins'].__setitem__('hardened.elf','0'*64),budget,'pin mismatch'),
        ('wrong-map-pin',lambda p:p['pins'].__setitem__('hardened.map','0'*64),budget,'pin mismatch'),
        ('recursive-servo-callback',lambda p:p['indirectCalls'][site].__setitem__('targets',['servo_move_from']),budget,'recursive/reentrant'),
        ('wrong-callback-caller',lambda p:p['indirectCalls'][site].__setitem__('caller','main'),budget,'indirect caller mismatch'),
        ('wrong-callback-target',lambda p:p['indirectCalls'][site].__setitem__('targets',['focus_abort']),budget,'reviewed call inventory mismatch'),
        ('understated-library-frame',lambda p:p['libraryFrames'].__setitem__('memcpy',0),budget,'reviewed library frame mismatch'),
        ('wrong-library-body',lambda p:p['libraryFrameEvidence']['memcpy'].__setitem__('bodySHA256','0'*64),budget,'reviewed library body mismatch'),
        ('wrong-stock-pointer',lambda p:p['reviewedRawWords'].__setitem__('95ac','00000000'),budget,'reviewed callback/literal mismatch'),
        ('wrong-static-ram',lambda p:p['expectedLayout'].__setitem__('staticRAMBytes',3076),budget,'reviewed layout mismatch'),
        ('wrong-call-count',lambda p:p['expectedInventory'].__setitem__('callSiteCount',462),budget,'compiled inventory mismatch'),
        ('cleared-physical-caveats',lambda p:p.__setitem__('unknowns',[]),budget,'physical caveats missing or changed'),
    ]
    output=[]
    def reject(name, fn, diagnostic):
        try: fn()
        except ValueError as error:
            require(diagnostic in str(error),'wrong guard failure: '+name+': '+str(error))
            output.append(dict(case=name,status='rejected',diagnostic=str(error)))
        else: raise ValueError('guard accepted invalid evidence: '+name)
    for name, mutate, limit, diagnostic in cases:
        altered=copy.deepcopy(policy)
        if mutate: mutate(altered)
        reject(name,lambda:reviewed_audit(build,altered,limit),diagnostic)
    # Each private copy is disposable. Outer pins are refreshed only in the
    # raw/image mismatch controls so that they reach the inner byte checks.
    for name,filename,edit,refresh,diagnostic in [
        ('source-content','src/servo.c',lambda b:b+b'\n',False,'source mismatch'),
        ('dynamic-compiler-frame','servo.su',lambda b:b.replace(b'\tstatic',b'\tdynamic',1),False,'unbounded/dynamic frame'),
        ('compiler-frame-size','servo.su',lambda b:b.replace(b'\t136\t',b'\t128\t',1),False,'compiler stack usage differs'),
        ('elf-raw-byte-mismatch','raw.bin',lambda b:bytes([b[0]^1])+b[1:],True,'ELF/raw image mismatch'),
        ('raw-image-byte-mismatch','contax-zeiss-50-f1-4.bin',lambda b:bytes([b[0]^1])+b[1:],True,'raw/published image mismatch'),
    ]:
        with tempfile.TemporaryDirectory(prefix='astra-29-guard-',dir=ROOT/'artifacts/private') as temp:
            scratch=Path(temp)/'build';shutil.copytree(build,scratch)
            target=scratch/filename;target.write_bytes(edit(target.read_bytes()))
            altered=copy.deepcopy(policy)
            if refresh:altered['pins'][filename]=sha(target)
            reject(name,lambda:reviewed_audit(scratch,altered,budget),diagnostic)
    reject('unconditional-claim',lambda:require(not result['unknowns'],'unconditional safety unavailable'),'unconditional safety unavailable')
    exact=reviewed_audit(build,policy,result['maximumAllVectorPriorityBytes'])
    require(exact['maximumAllVectorPriorityBytes']==result['maximumAllVectorPriorityBytes'],'exact-budget control failed')
    output.append(dict(case='exact-bound-budget',status='accepted',budgetBytes=exact['maximumAllVectorPriorityBytes']))
    asm = subprocess.check_output([str(module['TOOL']),'-d',str(build/'hardened.elf')],text=True)
    headers=list(re.finditer(r'^([0-9a-f]+) <(.+)>:\n',asm,re.M))
    bodies={m[2]:asm[m.end():headers[i+1].start() if i+1<len(headers) else len(asm)].strip() for i,m in enumerate(headers)}
    symbols={line.split()[-1]:int(line.split()[0],16) for line in subprocess.check_output(
        [str(module['TOOL']),'-t',str(build/'hardened.elf')],text=True).splitlines()
        if len(line.split())>=5 and re.fullmatch('[0-9a-f]{8}',line.split()[0])}
    output.extend(handoff.guards(bodies,(build/'raw.bin').read_bytes(),symbols,policy))
    return output


def main():
    global module, audit
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,default=ROOT/'artifacts/private/handoff36a')
    parser.add_argument('--policy',type=Path,default=HERE/'policy.json')
    parser.add_argument('--budget',type=int,default=8192)
    parser.add_argument('--require-unconditional',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--guards-output',type=Path)
    args=parser.parse_args();policy=json.loads(args.policy.read_text());verify_derivative(policy)
    module=runpy.run_path(str(ANALYZER));audit=module['audit']
    build=args.build.resolve();result=reviewed_audit(build,policy,args.budget)
    if args.require_unconditional:require(not result['unknowns'],'unconditional safety unavailable: '+'; '.join(result['unknowns']))
    result.update(analyzerSHA256=sha(ANALYZER),baseAnalyzerSHA256=BASE_SHA,policySHA256=sha(args.policy),runnerSHA256=sha(Path(__file__)))
    if args.guards_output:
        evidence=guards(build,policy,args.budget,result)
        args.guards_output.write_text(json.dumps(evidence,indent=2)+'\n')
        result['guards']={'rejected':sum(x['status']=='rejected' for x in evidence),'accepted':sum(x['status']=='accepted' for x in evidence)}
    # Recheck pristine inputs after scratch controls.
    reviewed_audit(build,policy,args.budget)
    if args.output:args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['calls','functionBounds','inputPins','libraryFramesWithoutSU']},indent=2))


if __name__=='__main__': main()
