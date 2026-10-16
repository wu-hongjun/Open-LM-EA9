#!/usr/bin/env python3
"""Stage observation-only motion instrumentation into an exact private 3.6 source copy."""
import argparse, hashlib, json, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json'
def once(s, a, b):
    assert s.count(a)==1, a
    return s.replace(a,b)
def apply(src):
    src=Path(src).resolve()
    assert src.is_relative_to(ROOT/'artifacts/private') and src.name=='src'
    pins=json.loads(BASE.read_text())['sources']
    for name in ('main.c','servo.c'):
        assert hashlib.sha256((src/name).read_bytes()).hexdigest()==pins['src/'+name], name
    p=src/'servo.c';s=p.read_text()
    s=once(s, '#include "startup_trace.h"', '#include "startup_trace.h"\n#include "motion_trace.h"')
    s=once(s, '\taim = target +', '\tst_motion_begin(start, target, t0, cfg->dry);\n\n\taim = target +')
    s=once(s, '\t\tnow = millis();', '\t\tnow = millis();\n\t\tst_motion_sample(now, pos);')
    s=once(s, '\t\t/* --- the body may call the whole thing off', '\t\tst_motion_leg(target, leg_start, ((unsigned)n_retarget << 8)\n\t\t    | (unsigned)rebase | ((unsigned)holding << 1)\n\t\t    | ((unsigned)(leg_sign < 0) << 2));\n\n\t\t/* --- the body may call the whole thing off')
    s=once(s, '\t/* Existing guards identify unsafe feedback', '\tst_motion_finish(out->outcome);\n\n\t/* Existing guards identify unsafe feedback')
    # Observe actual call arguments, including the reversal brake. Never issue a drive.
    for marker in ('\t\t\t\t\t\t\tmotor_drive(0);','\t\t\t\tmotor_drive((int16_t)duty);','\t\tmotor_drive(0);'):
        arg='(int16_t)duty' if 'duty' in marker else '0'
        indent=marker[:len(marker)-len(marker.lstrip())]
        s=once(s, '\n'+marker+'\n', '\n'+marker+'\n'+indent+'st_motion_drive('+arg+');\n')
    # Reuse existing duration read; final encoder read is not part of guard snapshot.
    s=once(s, '\tout->ms         = (uint16_t)(millis() - t0);', '\tout->ms         = (uint16_t)(millis() - t0);\n\tst_motion_finish(out->outcome);')
    p.write_text(s)
    p=src/'main.c';s=p.read_text()
    s=once(s, '#include "startup_trace.h"', '#include "startup_trace.h"\n#include "motion_trace.h"')
    s=once(s, '    if (!focus_invalid()) em_post_event(code, param);', '''    if (!focus_invalid()) {
        st_motion_completion(ST_MC_ATTEMPT, code | ((uint16_t)param << 8));
        em_post_event(code, param);
    } else st_motion_completion(ST_MC_SUPPRESSED, code | ((uint16_t)param << 8));''')
    s=once(s, '\tg_last_op       = c->op;', '''\tst_motion_command(c->op, (c->op == EM_OP_MOVE_REL || c->op == EM_OP_MOVE_DEFOCUS)
\t    ? (uint16_t)c->delta : c->target);
\tg_last_op       = c->op;''')
    s=once(s, '\tg_last_target = c.target;', '''\tst_motion_command(c.op, (c.op == EM_OP_MOVE_REL || c.op == EM_OP_MOVE_DEFOCUS)
\t    ? (uint16_t)c.delta : c.target);
\tg_last_target = c.target;''')
    # Localize both invalid returns to focus_run, retaining the exact predicate calls.
    lo=s.index('static uint8_t focus_run(int32_t want, uint16_t target_u,\n');hi=s.index('\n}\n',lo)+3
    body=s[lo:hi]
    assert body.count('if (focus_invalid()) return SERVO_ABORTED;')==2
    body=body.replace('if (focus_invalid()) return SERVO_ABORTED;', 'if (focus_invalid()) { st_motion_completion(ST_MC_SUPPRESSED, 0); return SERVO_ABORTED; }')
    body=once(body, '\t\treturn SERVO_OK;', '\t\tst_motion_begin(here, want, millis(), cfg->dry);\n\t\tst_motion_finish(SERVO_OK);\n\t\treturn SERVO_OK;')
    body=once(body, '\treturn focus_invalid() ? SERVO_ABORTED : r.outcome;', '\tif (focus_invalid()) { st_motion_completion(ST_MC_SUPPRESSED, 0); return SERVO_ABORTED; }\n\treturn r.outcome;')
    s=s[:lo]+body+s[hi:]
    s=once(s, '\t\tg_focus_aborts++;', '\t\tst_motion_completion(ST_MC_ABORTED, EM_REC_MOVE);\n\t\tg_focus_aborts++;')
    p.write_text(s)
    for name in ('motion_trace.c','motion_trace.h'):shutil.copyfile(HERE/name,src/name)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);a=p.parse_args();apply(a.source)
