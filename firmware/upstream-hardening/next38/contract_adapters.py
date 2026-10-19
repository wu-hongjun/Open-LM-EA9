"""Private fixture copies for the two intentional 3.8 contract differences.

Only operand-query liveness during motor inhibition and phase-specific failure
labels change. Earlier-source controls retain their expectations; all session,
shutdown, abort, motor cutoff, read bounds, wire values and queue checks remain.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = json.loads((HERE/'contract-fixtures.json').read_text())

def adapt(case, text, template, directory):
    names = {'query-ownership': 'firmware/upstream-hardening/followup/12-query/test_query.c',
        'query-flow': 'firmware/upstream-hardening/followup/16-query-flow/test_flow.c',
        'query-composition': 'firmware/upstream-hardening/followup/17-composition/test_composition.c',
        'target-time-composition': 'firmware/upstream-hardening/followup/23-composition35/test_composition.c'}
    if case not in names:
        return text
    path = ROOT/names[case]
    original = path.read_text()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == PINS[names[case]]
    fixture = original
    if case == 'query-ownership':
        old = 'if(action>=2 && action<=4){assert(answers==(fixed?0u:1u));}'
        assert fixture.count(old) == 1
        fixture = '#ifndef EA9_OPERAND_QUERIES_LIVE\n#define EA9_OPERAND_QUERIES_LIVE 0\n#endif\n' + fixture.replace(old,
            'if(action>=2 && action<=4){assert(answers==((fixed && !(EA9_OPERAND_QUERIES_LIVE && action==3))?0u:1u));}')
        old = " cmd=[*flags,HERE/'test_query.c'"
        assert text.count(old) == 1
        text = text.replace(old, " if label=='proposal':flags+=['-DEA9_OPERAND_QUERIES_LIVE=1']\n"+old)
    elif case == 'query-flow':
        old = 'tick();assert(conversions==0 && query_pending()==1 && got_n==0);puts("PASS readiness guard");'
        assert fixture.count(old) == 1
        fixture = '#ifndef EA9_OPERAND_QUERIES_LIVE\n#define EA9_OPERAND_QUERIES_LIVE 0\n#endif\n' + fixture.replace(old,
            'tick();if(EA9_OPERAND_QUERIES_LIVE && inhibited){assert(conversions==1 && query_pending()==0 && got_n==1);finish();}\n  else{assert(conversions==0 && query_pending()==1 && got_n==0);puts("PASS readiness guard");}')
        old = " exe=work/'probe';cmd=[*flags,HERE/'test_flow.c'"
        assert text.count(old) == 1
        text = text.replace(old, " if label in ('proposal','mutant-home-gate'):flags+=['-DEA9_OPERAND_QUERIES_LIVE=1']\n"+old)
        old = "case in ['pump-unhomed','homing-stream']"
        assert text.count(old) == 1
        text = text.replace(old, "case in ['pump-unhomed','homing-stream','inhibited']")
    elif case == 'query-composition':
        old = 'assert(r.outcome==SERVO_ABORTED && !mask && wire_answers()==0);'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, 'assert(r.outcome==SERVO_ABORTED && !mask);')
        old = 'assert(inhibited && r.end==ENC_TRACK_LIMIT && conversions==0 && query_pending()==1 && !query_answers());'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, 'assert(inhibited && r.end==ENC_TRACK_LIMIT);')
        old = 'assert(reads==(strstr(mode,"final")?5u:4u));'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, old+'\n   host_frame_sync();pump(r.end);\n   assert(conversions==1 && !query_pending() && !query_answers() && wire_answers()==1);')
        old = '}else{assert(conversions==1 && !query_answers() && !query_pending());}'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, '}else{assert(conversions==1 && !query_answers() && !query_pending() && wire_answers()==0);}')
    else:
        old = 'test_fault()==ST_HOME_FAILED'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, 'test_fault()==(has("drive")?ST_HOME_DRIVE:ST_HOME_SETTLE)')
    output = directory/(case+'-38.c')
    output.write_text(fixture)
    anchor = "HERE/"+repr(path.name)
    assert anchor in text
    text = text.replace(anchor, repr(str(output)))
    return text
