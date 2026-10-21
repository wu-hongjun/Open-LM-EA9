"""Private4.0 fixtures: retained query contracts plus validated reference reset.

Historical source pins remain exact; new helper extraction and explicitly
identified mutant/injection changes are documented in README.md.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = json.loads((HERE/'contract-fixtures.json').read_text())

def adapt(case, text, template, directory):
    names = {'time-contract': 'firmware/upstream-hardening/next35/test_time.c',
        'home-inhibit': 'firmware/upstream-hardening/followup/17-composition/test_home.c',
        'query-ownership': 'firmware/upstream-hardening/followup/12-query/test_query.c',
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
    elif case == 'target-time-composition':
        old = 'test_fault()==ST_HOME_FAILED'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, 'test_fault()==(has("drive")?ST_HOME_DRIVE:ST_HOME_SETTLE)')
    # Scheduling is a private harness operation, independent of release ADC.
    # Preserve the historical scheduler body and all assertions, invoking once
    # at the same pump exit for both frozen controls and candidate variants.
    if case in ('query-flow', 'query-composition', 'target-time-composition', 'time-contract'):
        old = 'static void vdd_track_sample(void)'
        assert fixture.count(old) == 1
        fixture = fixture.replace(old, 'static void fixture_after_pump(void)')
        fixture = 'static void __attribute__((unused)) vdd_track_sample(void) {}\n' + fixture
        if case == 'query-flow':
            old = " pump=pump.replace('\\tvdd_track_sample();','\\tvdd_track_sample();\\n    pump_depth--;')"
            assert text.count(old) == 1
            text = text.replace(old, " pump=pump[:-2]+'    fixture_after_pump();pump_depth--;\\n}\\n'")
        elif case == 'query-composition':
            old = "function(s,'static void pump(int32_t pos)')"
            assert text.count(old) == 1
            text = text.replace(old, "function(s,'static void pump(int32_t pos)')[:-2]+'    fixture_after_pump();\\n}\\n'")
        elif case == 'time-contract':
            old = 'body += function(s, name)'
            assert text.count(old) == 2
            text = text.replace(old, "body += (function(s,name)[:-2]+'    fixture_after_pump();\\n}\\n') if name=='static void pump(int32_t pos)' else function(s,name)")
        else:
            old = "body=''.join(function(s,n) for n in names)"
            assert text.count(old) == 1
            text = text.replace(old, "body=''.join((function(s,n)[:-2]+'    fixture_after_pump();\\n}\\n') if n=='static void pump(int32_t pos)' else function(s,n) for n in names)")
            fixture = fixture.replace('static void vdd_track_reset', 'static void __attribute__((unused)) vdd_track_reset').replace('static void vdd_track_result', 'static void __attribute__((unused)) vdd_track_result')
    if case in ('time-contract', 'home-inhibit'):
        fixture = fixture.replace('static void vdd_track_reset', 'static void __attribute__((unused)) vdd_track_reset').replace('static void vdd_track_result', 'static void __attribute__((unused)) vdd_track_result')
    # The new reset validates and commits one sampled coordinate. Include that
    # production helper in extracted tracker fixtures rather than substituting
    # the old second-read reset, which would undo the contract under test.
    if case in ('time-contract', 'home-inhibit', 'target-time-composition'):
        candidates = ["(work / 'tracker.inc').write_text(tracker)", "(work/'tracker.inc').write_text(tracker)"]
        marker = next(x for x in candidates if x in text)
        indent = '    ' if case == 'time-contract' else ' ' if case == 'home-inhibit' else '    '
        helper = "if 'uint8_t abs_encoder_home_reset(' in encoder:tracker+=function(encoder,'uint8_t abs_encoder_home_reset(int32_t anchor, uint16_t tolerance)').replace('g_track = 0;','resets++; g_track = 0;')"
        if case == 'target-time-composition':
            helper = helper.replace("resets++; g_track = 0;", "resets++; g_track = 0; fixture_reference_commit();")
            fixture = fixture.replace('#include "tracker.inc"', 'static void fixture_reference_commit(void){if(has("home-reset-session") && !injected){injected=1;frame(1);}}\n#include "tracker.inc"')
        if case == 'home-inhibit':
            # The new helper is a second independent sticky-inhibition guard.
            # The historical single-guard removal no longer reproduces unsafe
            # readiness; its negative control must remove BOTH guards.
            helper += "\n"+indent+"if variant=='composed':tracker=tracker.replace('motor_is_inhibited() || delta','delta')"
        text = text.replace(marker, helper+'\n'+indent+marker)
        fixture = fixture.replace('void motor_emergency_release(void) {}', 'void motor_emergency_release(void) {}\nvoid motor_home_release(void){motor_emergency_release();}')
        fixture = fixture.replace('void motor_emergency_release(void){}', 'void motor_emergency_release(void){}\nvoid motor_home_release(void){motor_emergency_release();}')
        if case == 'home-inhibit':
            fixture = '#include "focus_map.h"\nvoid motor_home_release(void){}\n' + fixture
    output = directory/(case+'-40.c')
    output.write_text(fixture)
    anchor = "HERE/"+repr(path.name)
    if case == 'time-contract':
        anchor = "Path("+repr(str(ROOT/'firmware/upstream-hardening/next35/test_time.py'))+").resolve().parent / 'test_time.c'"
    assert anchor in text, (case,anchor)
    text = text.replace(anchor, repr(str(output)))
    return text
