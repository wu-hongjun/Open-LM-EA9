"""Offline motion overlay, after frame/TX/02/01/03/05; replaces root apply_motor."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent

def once(s,a,b):
    assert s.count(a)==1,(a[:80],s.count(a))
    return s.replace(a,b,1)

def apply(work: Path):
    work=Path(work).resolve()
    assert work != HERE.parents[3]/'firmware/upstream-diagnostic/build'
    spec=importlib.util.spec_from_file_location('motion_motor_apply',HERE/'motor_apply.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.apply(work)
    p=work/'src/motor.c';s=p.read_text()
    s=once(s,'\tuint32_t start       = millis();','\tuint32_t polls = 0;\n\tuint32_t start       = millis();')
    s=once(s,'\tmotor_drive(dir >= 0 ?', '\tif (duty > MOTOR_DUTY_MAX) duty = MOTOR_DUTY_MAX;\n\tmotor_drive(dir >= 0 ?')
    s=once(s,'\tfor (;;) {','\tfor (;;) {\n\t\tif (motor_is_inhibited()) break;\n\t\tif (++polls >= 1000000u) { motor_inhibit(); break; }')
    p.write_text(s)
    p=work/'src/servo.c';s=p.read_text()
    s=once(s,'\tint32_t  start  = abs_encoder_track();', '\tuint32_t polls = 0;\n\tint32_t  start  = abs_encoder_track();')
    s=once(s,'\t\t/* Read FIRST,', '\t\t/* Finite work fallback independent of a stopped SysTick. */\n'
        '\t\tif (++polls >= 1000000u) { motor_inhibit(); out->outcome = SERVO_TIMEOUT; break; }\n'
        '\t\tif (motor_is_inhibited()) { out->outcome = SERVO_ABORTED; break; }\n\n\t\t/* Read FIRST,')
    s=once(s,'\t\t\t\t\ttarget = nt;', '\t\t\t\t\tn_still = 0; /* A new target needs its own fresh dwell. */\n\t\t\t\t\ttarget = nt;')
    a=s.index('\t\t/* arrived -- IN POSITION');b=s.index('\n\t\t/* gone far past',a)
    s=s[:a]+s[b:]
    a=s.index('\t\t\tif (servo_settled(cfg, aim - pos, v_meas))');b=s.index('\n\n\t\t\tt_ctl',a)
    s=s[:a]+s[b:]
    s=once(s,'\t\t\tv_meas = (pos - pos_ctl) * 1000 / dt;',
        '\t\t\tv_meas = (pos - pos_ctl) * 1000 / dt;\n\n'
        '\t\t\t/* Arrival uses this sample and this interval, never stale velocity. */\n'
        '\t\t\tif (servo_settled(cfg, aim - pos, v_meas)) {\n'
        '\t\t\t\tif (n_still >= cfg->arrive_steps) { out->outcome = SERVO_OK; break; }\n'
        '\t\t\t\tif (n_still < 255) n_still++;\n'
        '\t\t\t} else n_still = 0;')
    s=once(s,'\n\tif (!cfg->dry) {\n\t\t/* Brake, do not release.', '\n\t/* Existing guards identify unsafe feedback, so future commands must not rearm. */\n\tif (out->outcome == SERVO_RUNAWAY || out->outcome == SERVO_WRONG_WAY) motor_inhibit();\n\tif (!cfg->dry) {\n\t\t/* Brake, do not release.')
    # A sensor overflow can inhibit during the first/latest/final sample.
    s=once(s,'\t\tnow = millis();','\t\tnow = millis();\n\t\tif (motor_is_inhibited()) { out->outcome = SERVO_ABORTED; break; }')
    s=once(s,'\tout->end        = abs_encoder_track();','\tout->end        = abs_encoder_track();\n\tif (motor_is_inhibited() && out->outcome == SERVO_OK) out->outcome = SERVO_ABORTED;')
    p.write_text(s)
    p=work/'src/abs_encoder.c';s=p.read_text()
    s=once(s,'#include "abs_encoder.h"','#include "abs_encoder.h"\n#include "motor.h"\n#include <stdint.h>')
    s=once(s,'\tg_track     += d;',
        '\t/* Never wrap the software coordinate into an unrelated target. */\n'
        '\tif ((d > 0 && g_track > INT32_MAX - d) ||\n'
        '\t    (d < 0 && g_track < INT32_MIN - d)) {\n'
        '\t\tmotor_inhibit();\n'
        '\t} else {\n\t\tg_track += d;\n\t}')
    p.write_text(s)
    p=work/'src/main.c';s=p.read_text()
    s=once(s,'static uint8_t  g_abort_pending;', 'static uint32_t g_focus_session;\nstatic uint8_t  g_abort_pending;')
    a=s.index('static uint8_t focus_abort(void)\n{')
    s=s[:a]+'''/* Protocol epoch is part of a motion's ownership, including its final event. */
static uint8_t focus_invalid(void)
{
    return g_aborted || em_shutdown_requested() || motor_is_inhibited() ||
           !em_handshake_done || g_focus_session != em_session_generation();
}
static void focus_event(uint8_t code, uint8_t param)
{
    uint32_t key = st_lock();
    if (!focus_invalid()) em_post_event(code, param);
    st_unlock(key);
}
''' + s[a:]
    s=once(s,'\treturn g_abort_pending;', '\treturn g_abort_pending || focus_invalid();')
    s=once(s,'\tif (!em_take_focus_cmd(&c)) {','\tif (focus_invalid() || !em_take_focus_cmd(&c)) {')
    s=once(s,'\there  = abs_encoder_track();','\tif (focus_invalid()) return SERVO_ABORTED;\n\there  = abs_encoder_track();')
    s=once(s,'\tfocus_pred_end(&g_pred);\n\tfocus_report();','\tfocus_pred_end(&g_pred);\n\tif (focus_invalid()) return SERVO_ABORTED;\n\tfocus_report();')
    s=once(s,'\treturn r.outcome;', '\treturn focus_invalid() ? SERVO_ABORTED : r.outcome;')
    s=once(s,'\tg_last_op       = c->op;', '\tg_focus_session = em_session_generation();\n\tg_last_op       = c->op;')
    # Only focus instruction events use this helper; homing Stop stays independent.
    a=s.index('static void focus_scan(const struct em_focus_cmd *c)\n{')
    b=s.index('/* The last few moves,',a)
    block=s[a:b].replace('em_post_event(', 'focus_event(')
    block=once(block,'\tem_scan_finish();','\tif (focus_invalid()) return;\n\tem_scan_finish();')
    block=once(block,'\tif (outcome == SERVO_ABORTED || g_next_pending) {','\tif (focus_invalid()) return;\n\tif (outcome == SERVO_ABORTED || g_next_pending) {')
    s=s[:a]+block+s[b:]
    s=once(s,'\tif (home_cancel_requested()) goto cancelled;\n\tg_homed = 1;\n\tg_home_state = HOME_READY;',
        '\t/* Serialize only final readiness commit; all encoder I/O is above. */\n'
        '\t{\n\t\tuint32_t key = st_lock();\n'
        '\t\tif (home_cancel_requested()) { st_unlock(key); goto cancelled; }\n'
        '\t\tg_homed = 1;\n\t\tg_home_state = HOME_READY;\n\t\tst_unlock(key);\n\t}')
    p.write_text(s)
    # Carry the dequeue epoch through entry, so a completed new handshake cannot
    # adopt an old locally copied command in the dequeue-to-exec interval.
    s=p.read_text()
    s=s.replace('focus_exec(const struct em_focus_cmd *c)', 'focus_exec(const struct em_focus_cmd *c, uint32_t session)')
    s=once(s,'\tg_focus_session = em_session_generation();','\tg_focus_session = session;\n\tif (focus_invalid()) return;')
    s=once(s,'focus_exec(&g_next);','focus_exec(&g_next, g_next_session);')
    s=once(s,'\t\t\tif (em_take_focus_cmd(&cmd) && !g_aborted) {\n\t\t\t\tfocus_exec(&cmd);\n\t\t\t}',
        '\t\t\t{\n\t\t\t\tuint32_t key = st_lock();\n'
        '\t\t\t\tuint32_t session = em_session_generation();\n'
        '\t\t\t\tuint8_t taken = em_take_focus_cmd(&cmd);\n'
        '\t\t\t\tst_unlock(key);\n'
        '\t\t\t\tif (taken && !g_aborted) focus_exec(&cmd, session);\n\t\t\t}')
    s=once(s,'\tif (focus_invalid() || !em_take_focus_cmd(&c)) {\n\t\treturn 0;\n\t}',
        '\t{\n\t\tuint32_t key = st_lock();\n'
        '\t\tuint8_t taken = !focus_invalid() && em_take_focus_cmd(&c);\n'
        '\t\tst_unlock(key);\n\t\tif (!taken) return 0;\n\t}')
    a=s.index('static uint8_t focus_retarget(int32_t *target)\n{')
    b=s.index('/* Run one leg of motion',a)
    block=s[a:b]
    block=once(block,'g_next_session = em_session_generation();','g_next_session = g_focus_session;')
    s=s[:a]+block+s[b:]
    p.write_text(s)
    p=work/'src/em_uart.c';s=p.read_text()
    s=once(s,'#include "startup_trace.h"','#include "startup_trace.h"\n#include "motor.h"')
    s=once(s,'\t\tg_rx_invalid = g_rx_fault = 1;','\t\tg_rx_invalid = g_rx_fault = 1;\n\t\tmotor_inhibit(); /* Fatal receive loss: GPIO-only cutoff, no peripheral wait. */')
    p.write_text(s)
