#!/usr/bin/env python3
"""Exact 3.7 offline audit; policy pins are immutable inputs, never refreshed here."""
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
import semantics as sem
import composition

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
digest = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
require = sem.require
module = runpy.run_path(str(HERE/'audit.py'))


def inspect(build):
    tool = str(module['TOOL'])
    asm = subprocess.check_output([tool, '-d', str(build/'hardened.elf')], text=True, timeout=30)
    heads = list(re.finditer(r'^([0-9a-f]+) <(.+)>:\n', asm, re.M))
    bodies = {m[2]:asm[m.end():heads[i+1].start() if i+1<len(heads) else len(asm)].strip() for i,m in enumerate(heads)}
    symbols = {l.split()[-1]:int(l.split()[0],16) for l in subprocess.check_output(
        [tool, '-t', str(build/'hardened.elf')],text=True,timeout=30).splitlines()
        if len(l.split())>=5 and re.fullmatch('[0-9a-f]{8}', l.split()[0])}
    return bodies, symbols


def verify_analyzer(policy):
    for path, expected in policy['referencePins'].items():
        require(sha(ROOT/path)==expected, 'reference pin mismatch: '+path)
    base = (HERE.parent/'29-stack36/audit.py').read_text()
    expected = base.replace('artifacts/private/handoff36a','artifacts/private/targeted37c').replace(
        "== 46, 'source inventory changed'", "== 49, 'source inventory changed'").replace(
        'sourceHashesVerified=46','sourceHashesVerified=49').replace('== 3064,','== 3044,').replace(
        'staticRAMBytes=3064,','staticRAMBytes=3044,')
    require((HERE/'audit.py').read_text()==expected, 'unexpected analyzer derivative')
    require(sha(HERE/'audit.py')==policy['analyzerSHA256'], 'analyzer pin mismatch')
    require(sha(HERE/'semantics.py')==policy['semanticsSHA256'], 'semantics pin mismatch')
    require(sha(HERE/'composition.py')==policy['compositionSHA256'], 'composition verifier pin mismatch')


def reviewed(build, policy, budget):
    result = module['audit'](build, policy, budget)
    manifest = json.loads((build/'manifest.json').read_text())
    require(manifest['imageSHA256']==sha(build/'contax-zeiss-50-f1-4.bin'), 'manifest image mismatch')
    require(sorted(manifest['sources'])==policy['sourceNames'], 'source name inventory mismatch')
    baseline=ROOT/'artifacts/private/handoff36-repeat'
    for name, expected in policy['baseSourcePins'].items():
        require(sha(baseline/name)==expected, 'frozen36 source mismatch: '+name)
    changed=sorted(name for name,expected in manifest['sources'].items() if expected!=policy['baseSourcePins'].get(name))
    require(changed==policy['sourceDeltaFrom36'], 'source delta inventory mismatch')
    result['controlSourceComposition']=composition.verify(build,baseline)
    oldheader=(baseline/'src/emount.h').read_text()
    require((build/'src/emount.h').read_text()==oldheader.replace('#define EM_FW_VERSION_BCD   0x36u','#define EM_FW_VERSION_BCD   0x37u'), 'unexpected wire-version header change')
    result['wireVersionException']='Firmware identity BCD intentionally changes 0x36 to 0x37; other control/transmit expressions compare equal after explicit observer removal.'
    result['sourceDeltaFrom36']=changed
    for key, value in policy['expectedCode'].items():
        require(manifest[key]==value, 'code/log layout mismatch: '+key)
    require(manifest['rawBytes']==len((build/'raw.bin').read_bytes()) and manifest['codeAndDataEnd']==0x5000+manifest['rawBytes'], 'raw size mismatch')
    require(manifest['codeMarginBeforeDiagnostics']==0x9c00-manifest['codeAndDataEnd']>=256, 'code margin insufficient')
    for key, value in policy['expectedLayout'].items():
        require(result[key]==value, 'reviewed layout mismatch: '+key)
    for key, value in policy['expectedInventory'].items():
        require(result[key]==value, 'compiled inventory mismatch: '+key)
    require(digest(result['calls'])==policy['callsSHA256'], 'reviewed call inventory mismatch')
    require(result['unknowns']==policy['requiredPhysicalCaveats'] and len(result['unknowns'])==4, 'physical caveats missing or changed')
    bodies, symbols = inspect(build)
    raw = (build/'raw.bin').read_bytes()
    for address, expected in policy['reviewedRawWords'].items():
        require(struct.unpack_from('<I',raw,int(address,16)-0x5000)[0]==int(expected,16), 'reviewed callback/literal mismatch: '+address)
    require(set(policy['libraryFrames'])==set(policy['libraryFrameEvidence']), 'library evidence inventory mismatch')
    for name, evidence in policy['libraryFrameEvidence'].items():
        require(evidence['localBytes']==policy['libraryFrames'][name], 'reviewed library frame mismatch: '+name)
        require(evidence['start']==hex(symbols[name]) and evidence['bodySHA256']==hashlib.sha256(bodies[name].encode()).hexdigest(), 'reviewed library body mismatch: '+name)
        stack = [line.strip() for line in bodies[name].splitlines() if re.search(r'\b(push|pop)\b|\bsp\b',line)]
        require(stack==evidence['stackInstructions'], 'library stack instruction mismatch: '+name)
    for name, expected in policy['criticalBodySHA256'].items():
        require(hashlib.sha256(bodies[name].encode()).hexdigest()==expected, 'critical compiled body mismatch: '+name)
    require(sem.mask_inventory(bodies)==policy['maskInventory'], 'global mask instruction inventory changed')
    sem.callbacks(raw, symbols)
    setup = sem.instructions(bodies['em_eic_init']); setup.update(sem.instructions(bodies['em_eic_start']))
    sem.setup(setup, raw, symbols)
    sem.terminal_order(bodies)
    result['compiledSemantics'] = dict(vectors=sem.vectors(raw,symbols), handoffPaths=sem.handoff_paths(sem.instructions(bodies['em_init'])),
        sourceGates=sem.source_gates(build), globalMaskInstructions=sem.mask_inventory(bodies), physicalIRQExecutionMeasured=False)
    require(symbols['_sstack']-symbols['_ezero']==4 and symbols['_sstack']%8==0, 'stack alignment gap mismatch')
    edges = {(call['caller'],target) for call in result['calls'] for target in call['targets']}
    callers = lambda target: sorted(a for a,b in edges if b==target)
    for target, owners in {'st_flush':['powerdown_signal','st_fail'], 'st_terminal':['powerdown_signal','st_fail'],
            'append':['st_flush','st_terminal'], 'st_write_page':['append'], 'st_read_page':['append','st_init']}.items():
        require(callers(target)==owners, 'NVM caller gate mismatch: '+target)
    def descendants(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen: return seen
        seen.add(name)
        for a,b in edges:
            if a==name: descendants(b,seen)
        return seen
    forbidden = {'st_flush','st_terminal','st_write_page','st_read_page','append','st_fail'}
    for root in ('EIC_Handler','SERCOM1_Handler','SysTick_Handler','st_summary','st_record','st_motion_completion'):
        require(not descendants(root)&forbidden, 'active-bus trace/IRQ reaches NVM: '+root)
    result['compiledNVMCallerGates'] = {n:callers(n) for n in ('st_flush','st_terminal','append','st_write_page','st_read_page')}
    bounds = result['functionBounds']
    chains = {'startup-packet':['Reset_Handler','ea9_packets_init'], 'startup-libc':['Reset_Handler','__libc_init_array','_init']}
    for kind, prefix in [('servo',['Reset_Handler','main','focus_exec','focus_run.isra.0','servo_move_from','pump']), ('inlined-homing',['Reset_Handler','main','pump'])]:
        for conversion, tail in [('position-to-distance',['focus_answer_queries','focus_distance_code','distance_mm','__udivsi3','__aeabi_idiv0']),
                ('distance-to-position',['focus_answer_queries','focus_counts_for_code','focus_exp2_q6']), ('predictor',['focus_pred_sample','__divsi3','__aeabi_idiv0'])]:
            chains[kind+'/'+conversion] = prefix+tail
    for name, chain in chains.items():
        require(all(pair in edges for pair in zip(chain,chain[1:])), 'reviewed path changed: '+name)
    result['explicitPaths'] = {n:dict(bytes=sum(bounds[f]['frameBytes'] for f in chain),chain=chain) for n,chain in chains.items()}
    require('servo_move_rel' not in bounds, 'relative wrapper unexpectedly linked')
    result['exceptionBudget'] = dict(bytesPerFrame=36, configurablePriorityLevels=4, additionalHardFaultAndNMI=2,totalFrames=6,totalBytes=216)
    result['codeAndDataEnd']=manifest['codeAndDataEnd'];result['codeMarginBeforeDiagnostics']=manifest['codeMarginBeforeDiagnostics']
    result['reviewedLibraryBodies']=len(policy['libraryFrames'])
    return result


def guards(build, policy, result):
    output=[]
    def reject(name, fn, expected):
        try: fn()
        except ValueError as e:
            require(expected in str(e), 'wrong guard diagnostic: '+name+': '+str(e))
            output.append(dict(case=name,status='rejected',diagnostic=str(e)))
        else: raise ValueError('accepted invalid evidence: '+name)
    for name, mutate, expected in [
        ('unknown-indirect',lambda p:p['indirectCalls'].pop('74a8'),'unknown indirect call'),
        ('unknown-library',lambda p:p['libraryFrames'].pop('memcpy'),'unknown library frame'),
        ('wrong-elf-pin',lambda p:p['pins'].__setitem__('hardened.elf','0'*64),'pin mismatch'),
        ('wrong-map-pin',lambda p:p['pins'].__setitem__('hardened.map','0'*64),'pin mismatch'),
        ('recursive-callback',lambda p:p['indirectCalls']['74a8'].__setitem__('targets',['servo_move_from']),'recursive/reentrant'),
        ('wrong-callback-owner',lambda p:p['indirectCalls']['74a8'].__setitem__('caller','main'),'indirect caller mismatch'),
        ('wrong-callback-target',lambda p:p['indirectCalls']['74a8'].__setitem__('targets',['focus_abort']),'reviewed call inventory mismatch'),
        ('understated-library-frame',lambda p:p['libraryFrames'].__setitem__('memcpy',0),'reviewed library frame mismatch'),
        ('wrong-library-body',lambda p:p['libraryFrameEvidence']['memcpy'].__setitem__('bodySHA256','0'*64),'reviewed library body mismatch'),
        ('wrong-stock-word',lambda p:p['reviewedRawWords'].__setitem__('9a70','00000000'),'reviewed callback/literal mismatch'),
        ('wrong-static-ram',lambda p:p['expectedLayout'].__setitem__('staticRAMBytes',3072),'reviewed layout mismatch'),
        ('wrong-call-inventory',lambda p:p['expectedInventory'].__setitem__('callSiteCount',514),'compiled inventory mismatch'),
        ('missing-physical-caveats',lambda p:p.__setitem__('unknowns',[]),'physical caveats missing'),
        ('unresolved-target',lambda p:p['indirectCalls']['74a8'].__setitem__('targets',['unknown_callback']),'unresolved target/frame')]:
        altered=copy.deepcopy(policy);mutate(altered)
        reject(name,lambda:reviewed(build,altered,8192),expected)
    reject('insufficient-budget',lambda:reviewed(build,policy,result['maximumAllVectorPriorityBytes']-1),'exceeds budget')
    for name,filename,edit,refresh,expected in [
        ('changed-source','src/servo.c',lambda b:b+b'\n',False,'source mismatch'),
        ('dynamic-frame','servo.su',lambda b:b.replace(b'\tstatic',b'\tdynamic',1),False,'unbounded/dynamic frame'),
        ('changed-compiler-frame','servo.su',lambda b:b.replace(b'\t128\t',b'\t120\t',1),False,'compiler stack usage differs'),
        ('elf-raw-inner-check','raw.bin',lambda b:bytes([b[0]^1])+b[1:],True,'ELF/raw image mismatch'),
        ('raw-image-inner-check','contax-zeiss-50-f1-4.bin',lambda b:bytes([b[0]^1])+b[1:],True,'raw/published image mismatch')]:
        with tempfile.TemporaryDirectory(prefix='astra38-',dir=ROOT/'artifacts/private') as tmp:
            scratch=Path(tmp)/'build';shutil.copytree(build,scratch)
            path=scratch/filename;path.write_bytes(edit(path.read_bytes()))
            altered=copy.deepcopy(policy)
            if refresh: altered['pins'][filename]=sha(path)
            reject(name,lambda:reviewed(scratch,altered,8192),expected)
    bodies,symbols=inspect(build);raw=(build/'raw.bin').read_bytes()
    setup=sem.instructions(bodies['em_eic_init']);setup.update(sem.instructions(bodies['em_eic_start']))
    for name,pc,expected in [('missing-EIC-disable',0x68c0,'EIC setup'),('missing-DSB',0x68c2,'EIC setup'),('missing-ISB',0x68c6,'EIC setup'),('missing-EIC-enable',0x6988,'EIC setup'),('wrong-EIC-priority',0x6956,'EIC priority')]:
        altered=copy.deepcopy(setup);altered[pc]=('nop','',altered[pc][2])
        reject(name,lambda:sem.setup(altered,raw,symbols),expected)
    paths=sem.instructions(bodies['em_init'])
    altered=copy.deepcopy(paths);altered[0x5fba]=('bls.n','5fd2 <em_init+0x13e>',2)
    reject('rescue-reset-bypass',lambda:sem.handoff_paths(altered),'handoff ordering/path mismatch')
    altered=copy.deepcopy(paths);altered[0x5fd2]=('nop','',4)
    reject('missing-deferred-start',lambda:sem.handoff_paths(altered),'handoff ordering/path mismatch')
    altered=bytearray(raw);struct.pack_into('<I',altered,21*4,symbols['EIC_Handler']|1)
    reject('wrong-NVM-vector',lambda:sem.vectors(altered,symbols),'vector target mismatch')
    altered=bytearray(raw);struct.pack_into('<I',altered,symbols['STOCK']+48-0x5000,symbols['focus_abort']|1)
    reject('STOCK-symbol-misbinding',lambda:sem.callbacks(altered,symbols),'STOCK binding mismatch')
    for name,function,pc,expected in [('missing-emergency-cutoff','st_fail','8e80','emergency cutoff'),('logging-before-cutoff','st_fail','8e64','emergency cutoff'),
            ('UART-disable-omitted','powerdown_signal','7bea','shutdown terminal'),('PA23-write-omitted','powerdown_signal','7c5e','shutdown terminal'),
            ('packet-init-omitted','Reset_Handler','5186','startup packet')]:
        altered=copy.deepcopy(bodies)
        altered[function]=re.sub(r'(?m)^\s*'+pc+r':[^\n]*',pc+':\tbf00      \tnop',altered[function])
        reject(name,lambda:sem.terminal_order(altered),expected)
    # Test source semantic guards directly, beyond the outer file hashes.
    class View:
        def __init__(self, texts, path=''): self.texts,self.path=texts,path
        def __truediv__(self, part): return View(self.texts,self.path+'/'+part)
        def read_text(self): return self.texts[self.path]
    texts={'/src/'+p.name:p.read_text() for p in (build/'src').glob('*') if p.is_file()}
    for name,file,old,new,expected in [
        ('NVM-allowed-gate-removed','startup_trace.c','!allowed || ','','NVM allowed gate'),
        ('PRIMASK-restore-replaced','startup_trace_flash.c','__set_PRIMASK(k);','__enable_irq();','PRIMASK restore'),
        ('mutable-TX-return-identity','emount.c','em_trace(ST_TX_RETURN, trace_identity, trace_flags, trace_session);','em_trace(ST_TX_RETURN, trace_identity, trace_flags, g_session_generation);','immutable TX identity')]:
        altered=texts.copy();altered['/src/'+file]=altered['/src/'+file].replace(old,new)
        reject(name,lambda:sem.source_gates(View(altered)),expected)
    for name,file,old,new in [('changed-motor-control','servo.c','cfg->pump(pos);','cfg->pump(pos + 1);'),
            ('changed-wire-terminator','emount.c','snapshot[len - 1] = EM_FRAME_END;','snapshot[len - 1] = 0;'),
            ('changed-terminal-delay','main.c','delay_ms(100);','delay_ms(101);')]:
        altered=texts.copy();altered['/src/'+file]=altered['/src/'+file].replace(old,new)
        reject(name,lambda:composition.verify(View(altered),ROOT/'artifacts/private/handoff36-repeat'),'non-observation control delta')
    reject('unconditional-safety',lambda:require(not result['unknowns'],'unconditional safety unavailable'),'unconditional safety unavailable')
    exact=reviewed(build,policy,result['maximumAllVectorPriorityBytes'])
    output.append(dict(case='exact-bound-budget',status='accepted',budgetBytes=exact['maximumAllVectorPriorityBytes']))
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,default=ROOT/'artifacts/private/targeted37c')
    parser.add_argument('--policy',type=Path,default=HERE/'policy.json')
    parser.add_argument('--budget',type=int,default=8192)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--guards-output',type=Path)
    parser.add_argument('--require-unconditional',action='store_true')
    args=parser.parse_args();policy=json.loads(args.policy.read_text());verify_analyzer(policy)
    result=reviewed(args.build,policy,args.budget)
    if args.require_unconditional: require(not result['unknowns'],'unconditional safety unavailable')
    if args.guards_output:
        evidence=guards(args.build,policy,result)
        args.guards_output.write_text(json.dumps(evidence,indent=2)+'\n')
        result['guards']=dict(rejected=sum(e['status']=='rejected' for e in evidence),accepted=sum(e['status']=='accepted' for e in evidence))
    reviewed(args.build,policy,args.budget)
    result.update(analyzerSHA256=sha(HERE/'audit.py'),semanticsSHA256=sha(HERE/'semantics.py'),compositionSHA256=sha(HERE/'composition.py'),runnerSHA256=sha(Path(__file__)),policySHA256=sha(args.policy))
    if args.output: args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('calls','functionBounds','inputPins','libraryFramesWithoutSU')},indent=2))


if __name__=='__main__': main()
