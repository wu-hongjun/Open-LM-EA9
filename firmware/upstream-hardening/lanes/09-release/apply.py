"""Apply last: remove legacy diagnostic-only work from EA9_NO_LOG builds.

The independent startup_trace recorder remains active. Non-release compilation
retains the legacy instrumentation and park test entry; lane02 never calls park.
"""
from pathlib import Path
HERE=Path(__file__).resolve().parent

def once(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b,1)

def gate(s,a,b):
    start=s.index(a); end=s.index(b,start)
    return s[:start]+'#ifndef EA9_NO_LOG\n'+s[start:end]+'\n#endif\n'+s[end:]

def apply(work: Path):
    work=Path(work).resolve()
    assert work != HERE.parents[3]/'firmware/upstream-diagnostic/build'
    p=work/'src/emount.c';s=p.read_text()
    assert 'em_shutdown_begin(&g_shutdown)' in s and 'static const struct em_owned_request *g_retry;' in s
    # All variables written here feed legacy trail.c, excluded by EA9_NO_LOG.
    s=gate(s,'\tif (!em_handshake_done && em_pre_used < EM_PRE_SLOTS)', '\n\tif (!em_t_first_frame)')
    s=gate(s,'\t/* Genuine truncation only', '\t/* Message 0x1B,')
    # Lane07 moves actual negotiation to consumed ordinary requests. Without it,
    # this range also contains behavior, so explicitly require its new anchor.
    assert 'Only an owned ordinary request commits negotiation.' in s
    s=gate(s,'\tif (rx[3] == EM_CLASS_INIT && rx[5] == 0x08u', '\t/* THE RECORD STREAM.')
    s=gate(s,'\tif (rx[3] == EM_CLASS_INIT && rx[5] == EM_ID_SESSION && view.length >= 17)', '\n\tif (rx[3] == EM_CLASS_INIT)')
    s=gate(s,'\t\tif (rx[5] < 32)', '\n\t}\n}')
    s=once(s,'\t\t\tem_tgt_ring[em_tgt_ring_n % EM_TGT_RING] = v;\n\t\t\tem_tgt_ring_n++;', '#ifndef EA9_NO_LOG\n\t\t\tem_tgt_ring[em_tgt_ring_n % EM_TGT_RING] = v;\n\t\t\tem_tgt_ring_n++;\n#endif')
    s=once(s, 'static void rec_count(uint8_t slot)\n{', 'static void rec_count(uint8_t slot)\n{\n#ifdef EA9_NO_LOG\n\t(void)slot;\n#else')
    s=once(s, '\t\tem_rec_n[slot]++;\n\t}\n}', '\t\tem_rec_n[slot]++;\n\t}\n#endif\n}')
    s=gate(s, '\t\t\tif (em_rec_unknown != 0xFFFFu)', '\t\t\treturn;')
    s=gate(s, '\t\t\tif (em_stop_n != 0xFFFFu)', '\t\t\tc.op = EM_OP_STOP;')
    s=gate(s, '\t\t\tem_t04_target = v;', '\n\t\t\tswitch (r[4]')
    # This post-lane08 branch only marks the disabled legacy tally.
    s=once(s, '\t\tuint8_t  marked = 0;', '#ifndef EA9_NO_LOG\n\t\tuint8_t  marked = 0;\n#endif')
    s=gate(s, '\t\t\tif (!marked && em_vd_edges == 0', '\n\t\t}\n\t}')
    p.write_text(s)
    p=work/'src/main.c';s=p.read_text()
    s=gate(s,'static const uint8_t  FOCUS_PAGE[]', '\n/* The LAST few moves,')
    s=gate(s,'static uint8_t g_norm_written;', '\n/* THE EXPERIMENT')
    for decl in ('static void focus_hist_page(uint32_t page);','static void build_marker_page(uint32_t page);','static void trace_page(uint32_t page, unsigned k, const struct servo_result *r);'):
        s=once(s,decl,'#ifndef EA9_NO_LOG\n'+decl+'\n#endif')
    s=gate(s,'static unsigned g_park_n;', 'static uint32_t g_pa23_at;')
    s=gate(s,'static void build_marker_page(uint32_t page)\n{', '/* Everything the servo loop')
    s=gate(s,'static const struct servo_cfg PARK =', '/* The tail of the stock shutdown')
    s=gate(s,'static void park_to_infinity(void)\n{', '/* Focus: drive')
    s=gate(s,'static void focus_hist_page(uint32_t page)\n{', 'int main(void)')
    s=once(s,'\tem_set_park_handler(park_to_infinity);', '''#ifndef EA9_NO_LOG
\tem_set_park_handler(park_to_infinity);
#endif
\t/* Lane02 never calls park: release retains no legacy callback/address. */''')
    s=once(s,'\ttrail_chk(18);\n\tbuild_marker_page(19);', '#ifndef EA9_NO_LOG\n\ttrail_chk(18);\n\tbuild_marker_page(19);\n#endif')
    s=gate(s,'\tint      hs_marked = 0;', '\tunsigned step = 0;')
    s=once(s,'\tint      quiet = 0;', '#ifndef EA9_NO_LOG\n\tint      quiet = 0;\n#endif')
    s=gate(s,'\t\t/* If the handshake has not completed', '\t\t/* Home once,')
    # The idle voltage burst only supplies legacy MOTR words 5/6. Preserve ADC
    # initialization and pump sampling, which also retain guarded fault waits.
    s=once(s,'\tvdd_read_burst(&idle_lo, &idle_hi, 20);', '#ifndef EA9_NO_LOG\n\tvdd_read_burst(&idle_lo, &idle_hi, 20);\n#else\n\tidle_lo = idle_hi = 0;\n#endif')
    # Legacy home pages read volatile protocol counters even with no sink.
    # This block removes only page packing and its local variables. The burst
    # above and diagnostic raw sampling below are explicit I/O/cadence changes;
    # control sensor reads, timer bounds, and pump ADC sampling remain.
    start=s.index('static void motor_home(void)\n{');end=s.index('/* No unsolicited retry',start)
    part=s[start:end]
    part=once(part, '\tuint32_t w[16];', '')
    part=gate(part, '\tfor (i = 0; i < 16; i++)', '\tif (home_cancel_requested()) goto cancelled;\n\t/* Software reference:')
    part=once(part, '#ifndef EA9_NO_LOG\n\tfor', '#ifndef EA9_NO_LOG\n\tuint32_t w[16];\n\tfor')
    part=once(part, '\tafter = abs_encoder_track();', '\tafter = abs_encoder_track();\n\t(void)before; (void)after; (void)drive_ms; (void)settle_ms; (void)idle_lo; (void)idle_hi;')
    s=s[:start]+part+s[end:]
    # focus_run constructs a diagnostic page and rolling ring with no consumer.
    start=s.index('static uint8_t focus_run(');end=s.index('/* ------------------------------------------------------------------------',start)
    part=s[start:end]
    part=once(part,'\tuint32_t w[16];','')
    part=once(part,'\tunsigned i;','')
    part=gate(part,'\tfor (i = 0; i < 16; i++)', '\treturn focus_invalid()' if 'return focus_invalid()' in part else '\treturn r.outcome;')
    part=once(part,'#ifndef EA9_NO_LOG\n\tfor', '#ifndef EA9_NO_LOG\n\tuint32_t w[16];\n\tunsigned i;\n\tfor')
    # target_u becomes diagnostic-only once the trace/ring is removed.
    part=once(part,'\tstruct servo_result r;', '\t(void)target_u;\n\tstruct servo_result r;')
    s=s[:start]+part+s[end:]
    # No remaining release reader exists for these static records.
    s=gate(s,'static struct focus_rec g_focus_ring[FOCUS_LAST_N];', '\n/* Publish where we are,')
    s=once(s, 'static uint16_t g_focus_moves;', '#ifndef EA9_NO_LOG\nstatic uint16_t g_focus_moves;\n#endif')
    # The raw home samples feed only the old MOTR trace page. Control still
    # reads abs_encoder_track in home_still and preserves its independent bounds.
    s=gate(s, 'static uint16_t g_home_trace[SERVO_TRACE_N];', '\n/* Set once homing')
    s=gate(s, '\t\tif (i < SERVO_TRACE_N', '\t\t/* Against the stop')
    s=once(s, '\tg_home_trace_n = (uint8_t)i;', '#ifndef EA9_NO_LOG\n\tg_home_trace_n = (uint8_t)i;\n#endif\n\t(void)i;')
    p.write_text(s)
    p=work/'src/servo.c';s=p.read_text()
    # Retain target, endpoint, outcome, retarget accounting and every motor/
    # abort predicate. Only raw trace and extrema for legacy pages are gated.
    s=once(s, '\tuint16_t duty_first = 0;', '#ifndef EA9_NO_LOG\n\tuint16_t duty_first = 0;\n#endif')
    s=gate(s, '\t\t\tif (!duty_first && duty)', '\t\t\tlast        = pos;')
    s=once(s, '\tout->duty_first = duty_first;', '#ifndef EA9_NO_LOG\n\tout->duty_first = duty_first;\n#endif')
    s=once(s, '\tuint32_t t_trace = t0;', '#ifndef EA9_NO_LOG\n\tuint32_t t_trace = t0;\n#endif')
    s=gate(s, '\t\tif (out->trace_n < SERVO_TRACE_N', '\t\tif (pos > last + cfg->noise')
    s=gate(s, '\t\t/* How far past the target', '\t\t/* --- the body may move')
    s=gate(s, '\t\t\tif (mag > (int32_t)out->duty_peak)', '\n\t\t\tif (!cfg->dry)')
    s=gate(s, '\t{\n\t\tint32_t past = (leg_sign > 0) ? out->end', '\n\tif (cfg->pump)')
    p.write_text(s)
