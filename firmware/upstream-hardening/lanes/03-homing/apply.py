"""Homing overlay only; caller supplies a disposable src-containing build tree.

Requires lane02 em_shutdown_requested and inhibit callback registration, lane01
em_session_generation. Production sources/releases are not edited by this file.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

def once(s, old, new):
    assert s.count(old) == 1, (old[:100], s.count(old))
    return s.replace(old, new, 1)

def apply(work: Path):
    path = work / 'src/main.c'
    s = path.read_text()
    declarations = 'static struct em_focus_cmd g_next;\nstatic uint8_t             g_next_pending;'
    s = once(s, declarations, '')
    s = once(s, 'static int      g_aborted;', 'static volatile int g_aborted;\n' + declarations + '\nstatic uint32_t g_next_session;')
    start = s.index('/* Has the mechanism stopped?')
    s = s[:start] + (HERE / 'home_policy.inc').read_text() + '\n' + s[start:]
    s = once(s, 'int32_t d   = now - st->at;', 'int64_t d   = (int64_t)now - st->at;')
    a = s.index('static void motor_home(void)\n{')
    b = s.index('\n/* Park to infinity,', a)
    h = s[a:b]
    h = once(h, '\tunsigned i;', '\tunsigned i;\n\tuint32_t polls = 0;\n\tuint8_t drive_ok = 0, settle_ok = 0;')
    h = once(h, '\tvdd_read_burst', '\tif (home_cancel_requested()) goto cancelled;\n\tvdd_read_burst')
    h = once(h, '\tbefore = abs_encoder_track();', '\tbefore = abs_encoder_track();\n\tif (home_cancel_requested()) goto cancelled;')
    h = once(h, '\t\tpump(0);\n', '\t\tif (++polls >= HOME_POLL_LIMIT) goto failed;\n\t\tif (home_cancel_requested()) goto cancelled;\n\t\tpump(0);\n\t\tif (home_cancel_requested()) goto cancelled;\n')
    h = once(h, '\t\t\tbreak;\n\t\t}\n\t}\n\tdrive_ms', '\t\t\tdrive_ok = 1;\n\t\t\tbreak;\n\t\t}\n\t}\n\tif (!drive_ok) goto failed;\n\tdrive_ms')
    h = once(h, '\t\tpump(0);                /* still pre-homing; see above */', '\t\tif (++polls >= HOME_POLL_LIMIT) goto failed;\n\t\tif (home_cancel_requested()) goto cancelled;\n\t\tpump(0);\n\t\tif (home_cancel_requested()) goto cancelled;')
    h = once(h, '\t\t\tbreak;\n\t\t}\n\t}\n\tsettle_ms', '\t\t\tsettle_ok = 1;\n\t\t\tbreak;\n\t\t}\n\t}\n\tif (!settle_ok) goto failed;\n\tsettle_ms')
    h = once(h, '\t/* Infinity is now zero. */', '\tif (home_cancel_requested()) goto cancelled;\n\t/* Software reference: stationary feedback alone does not prove infinity. */')
    h = once(h, '\tg_homed = 1;\n}', '\tif (home_cancel_requested()) goto cancelled;\n\tg_homed = 1;\n\tg_home_state = HOME_READY;\n\treturn;\nfailed:\n\tg_home_state = HOME_FAILED;\n\tmotor_inhibit();\n\tg_next_pending = 0;\ncancelled:\n\thome_cutoff();\n}')
    s = s[:a] + h + '\n' + (HERE / 'home_service.inc').read_text() + s[b:]
    s = once(s, '\tem_set_powerdown_handler(powerdown_signal);', '\tem_set_powerdown_handler(powerdown_signal);\n\tem_set_shutdown_inhibit_handler(motion_shutdown_inhibit);')
    s = once(s, '\t\tmotor_home();\n\t\tfocus_report();\n\t\tstep = 1;', '\t\thome_service();\n\t\tif (g_homed) { focus_report(); step = 1; }') if '\t\tmotor_home();\n\t\tfocus_report();\n\t\tstep = 1;' in s else once(s, '\t\t\tmotor_home();\n\t\t\tfocus_report();\n\t\t\tstep = 1;', '\t\t\thome_service();\n\t\t\tif (g_homed) { focus_report(); step = 1; }')
    s = once(s, '\tif (!g_homed || g_park_n >= PARK_ATTEMPTS) {', '\tif (em_shutdown_requested() || motor_is_inhibited()) return;\n\tif (!g_homed || g_park_n >= PARK_ATTEMPTS) {')
    s = once(s, '\t\t\tg_next         = c;', '\t\t\tg_next         = c;\n\t\t\tg_next_session = em_session_generation();')
    s = once(s, '\t\t\t\tif (!g_aborted) {\n\t\t\t\t\tfocus_exec(&g_next);', '\t\t\t\tif (!g_aborted && g_next_session == em_session_generation()) {\n\t\t\t\t\tfocus_exec(&g_next);')
    s = once(s, '\tif (!g_homed) {\n\t\treturn;', '\tif (!g_homed || !em_handshake_done || g_aborted ||\n\t    em_shutdown_requested() || motor_is_inhibited()) {\n\t\treturn;')
    s = once(s, 'static void focus_answer_queries(void)\n{', 'static void focus_answer_queries(void)\n{\n\tif (!em_handshake_done || g_aborted || em_shutdown_requested() || motor_is_inhibited()) return;')
    path.write_text(s)

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('work', type=Path)
    apply(p.parse_args().work)
