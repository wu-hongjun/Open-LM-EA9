#!/usr/bin/env python3
"""Read-only exact-ELF 3.4 stack review using frozen lane14's analyzer."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ANALYZER = HERE.parent / '14-stack/audit.py'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--policy', type=Path, default=HERE/'policy.json')
    p.add_argument('--budget', type=int, default=8192)
    p.add_argument('--require-unconditional', action='store_true')
    p.add_argument('--output', type=Path)
    p.add_argument('--guards-output', type=Path)
    a = p.parse_args()
    policy = json.loads(a.policy.read_text())
    assert hashlib.sha256(ANALYZER.read_bytes()).hexdigest() == policy['analyzerSHA256'], 'frozen analyzer changed'
    module = runpy.run_path(str(ANALYZER))
    audit, require = module['audit'], module['require']
    result = audit(a.build.resolve(), policy, a.budget)
    edges = {(r['caller'], target) for r in result['calls'] for target in r['targets']}
    bounds = result['functionBounds']
    servo_prefix = ['Reset_Handler', 'main', 'focus_exec', 'focus_run.isra.0',
                    'servo_move_rel', 'pump', 'focus_answer_queries']
    home_prefix = ['Reset_Handler', 'main', 'pump', 'focus_answer_queries']
    chains = {}
    for name, prefix in [('servo', servo_prefix), ('inlined-homing', home_prefix)]:
        for conversion, tail in [
            ('position-to-distance', ['focus_distance_code', 'distance_mm', '__udivsi3', '__aeabi_idiv0']),
            ('distance-to-position', ['focus_counts_for_code', 'focus_exp2_q6'])]:
            chain = prefix + tail
            require(all(edge in edges for edge in zip(chain, chain[1:])), 'query path changed: '+name+'/'+conversion)
            chains[name+'/'+conversion] = dict(bytes=sum(bounds[n]['frameBytes'] for n in chain), chain=chain)
    result['explicitQueryChains'] = chains
    result['analyzerSHA256'] = policy['analyzerSHA256']
    result['policySHA256'] = hashlib.sha256(a.policy.read_bytes()).hexdigest()
    if a.require_unconditional:
        require(not result['unknowns'], 'unconditional safety unavailable: '+'; '.join(result['unknowns']))
    if a.output:
        a.output.write_text(json.dumps(result, indent=2)+'\n')
    if a.guards_output:
        site = next(k for k,v in policy['indirectCalls'].items()
                    if v['caller']=='servo_move_rel' and v['targets']==['pump'])
        cases = [
            ('insufficient-budget', None, result['maximumAllVectorPriorityBytes']-1, 'exceeds budget'),
            ('missing-pump-callback', lambda p:p['indirectCalls'].pop(site), a.budget, 'unknown indirect call'),
            ('missing-library-frame', lambda p:p['libraryFrames'].pop('memcpy'), a.budget, 'unknown library frame'),
            ('wrong-elf-pin', lambda p:p['pins'].__setitem__('hardened.elf','0'*64), a.budget, 'pin mismatch'),
            ('recursive-servo-callback', lambda p:p['indirectCalls'][site].__setitem__('targets',['servo_move_rel']), a.budget, 'recursive/reentrant'),
            ('wrong-callback-caller', lambda p:p['indirectCalls'][site].__setitem__('caller','main'), a.budget, 'indirect caller mismatch'),
        ]
        guards = []
        for name, mutate, budget, diagnostic in cases:
            altered = copy.deepcopy(policy)
            if mutate:mutate(altered)
            try:
                audit(a.build.resolve(), altered, budget)
            except ValueError as error:
                require(diagnostic in str(error), 'wrong guard failure: '+name+': '+str(error))
                guards.append(dict(case=name,status='rejected',diagnostic=str(error)))
            else:
                raise ValueError('guard accepted invalid evidence: '+name)
        try:
            require(not result['unknowns'], 'unconditional safety unavailable')
        except ValueError as error:
            guards.append(dict(case='unconditional-claim',status='rejected',diagnostic=str(error)))
        else:
            raise ValueError('unconditional-claim guard failed')
        exact = audit(a.build.resolve(), policy, result['maximumAllVectorPriorityBytes'])
        require(exact['maximumAllVectorPriorityBytes']==result['maximumAllVectorPriorityBytes'], 'exact-budget positive control failed')
        guards.append(dict(case='exact-bound-budget',status='accepted',budgetBytes=result['maximumAllVectorPriorityBytes']))
        a.guards_output.write_text(json.dumps(guards,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['calls','functionBounds','inputPins','libraryFramesWithoutSU']},indent=2))


if __name__ == '__main__':
    main()
