#!/usr/bin/env python3
"""Stage RAM-only emount ownership observations on exact AF3.6 private source."""
import argparse
import hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE_SHA = '57fe9dfe08068db6a2f4596faf27371b74881f84573b79facca4d728cd349d41'
def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)
def apply(src):
    src = src.resolve()
    assert src.is_relative_to(ROOT/'artifacts/private') and src.name == 'src'
    assert src.parent.name != 'handoff36-repeat', 'never mutate frozen base'
    p = src/'emount.c'
    assert hashlib.sha256(p.read_bytes()).hexdigest() == BASE_SHA, 'exact AF3.6 emount required'
    s = p.read_text()
    s = replace(s, '#include "em_owner.h"', '#include "em_owner.h"\n#include "motion_trace.h"')
    s = replace(s, 'static const uint8_t *g_req;', 'static const uint8_t *g_req;\n\n'+(HERE/'trace.inc').read_text())
    s = replace(s, '\tuint32_t key, generation;', '\tuint32_t key, generation, trace_session;\n\tuint16_t trace_identity;\n\tuint8_t trace_flags;')
    s = replace(s, '\tPORT->Group[0].OUTSET.reg = (1u << EM_PIN_LENS_CS);\n\tst_unlock(key);', '''\t/* Capture once inside the existing admission mask. RX may run during
\t * em_uart_send: RETURN must keep this identity, never reread the owner. */
\ttrace_session = g_control_active ? g_control_session : g_session_generation;
\ttrace_identity = em_trace_identity(snapshot);
\ttrace_flags = em_trace_flags();
\tif (g_control_active) {
\t    trace_identity = (uint16_t)((trace_identity & 0xff00u) | g_req[4]);
\t    trace_flags |= ET_CONTROL | (g_owner.slot[g_owner.active].raw ? ET_RAW : 0);
\t}
\tem_trace(ST_TX_START, trace_identity, trace_flags, trace_session);
\tPORT->Group[0].OUTSET.reg = (1u << EM_PIN_LENS_CS);
\tst_unlock(key);''')
    s = replace(s, '\tem_frames_tx++;', '\tem_frames_tx++;\n\tem_trace(ST_TX_RETURN, trace_identity, trace_flags, trace_session);')
    s = replace(s, '\tem_owner_cs(&g_owner, level);', '''\tem_owner_cs(&g_owner, level);
\tif (level) em_trace(ST_OWNER_CS, 0,
\t    em_trace_flags() | (g_owner.capture ? ET_RAW : 0), g_session_generation);''')
    s = replace(s, '\t\tif (g_shutdown_inhibit) g_shutdown_inhibit();', '''\t\tif (g_shutdown_inhibit) g_shutdown_inhibit();
\t\tem_trace(ST_SHUTDOWN_ADMIT, em_trace_identity(rx),
\t\t    ET_SHUTDOWN | ET_RESULT, g_session_generation);''')
    s = replace(s, '''\t\tif (em_owner_offer(&g_owner, rx, view.length)
\t\t    && !g_owner.capture && rx[5] == EM_ID_SESSION) {''', '''\t\tint admitted = em_owner_offer(&g_owner, rx, view.length);
\t\tif (admitted && !g_owner.capture && rx[5] == EM_ID_SESSION) {''')
    s = replace(s, '''\t\t\tg_owner.status_enabled = 0;
\t\t}
#ifndef EA9_NO_LOG''', '''\t\t\tg_owner.status_enabled = 0;
\t\t}
\t\tem_trace(ST_OWNER_OFFER, em_trace_identity(rx), em_trace_flags()
\t\t    | (g_owner.capture ? ET_RAW : 0) | (admitted ? ET_RESULT : 0),
\t\t    g_session_generation);
#ifndef EA9_NO_LOG''')
    s = replace(s, '''\tif (g_event_n < EM_EVENT_Q) {''', '''\tst_motion_completion(g_event_n < EM_EVENT_Q ? ST_MC_QUEUED : ST_MC_QUEUE_FULL,
\t    (uint16_t)(code | ((uint16_t)param << 8)));
\tif (g_event_n < EM_EVENT_Q) {''')
    s = replace(s, '\t\tif (ready) g_status_due = 0;', '''\t\tif (ready) {
\t\t    g_status_due = 0;
\t\t    em_trace(ST_OWNER_PHASE, 0, ET_PHASE | ET_STATUS, g_session_generation);
\t\t}''')
    s = replace(s, '\t\tuint8_t  k, sent_ans;', '\t\tuint8_t  k, sent_ans;\n\t\tuint16_t trace_event = 0;')
    s = replace(s, '''\t\tif (g_event_n) {
\t\t\tea9_data''', '''\t\tif (g_event_n) {
\t\t\ttrace_event = (uint16_t)(g_event_code[0] | ((uint16_t)g_event_param[0] << 8));
\t\t\tea9_data''')
    s = replace(s, '''\t\tif (!em_transmit(&ea9_data[EA9_OFF_06], len)) goto status_done;''', '''\t\tif (!em_transmit(&ea9_data[EA9_OFF_06], len)) goto status_done;
\t\tif (trace_event) st_motion_completion(ST_MC_TX_RETURN, trace_event);''')
    s = replace(s, 'status_done:\n\tg_owner.phase = 0;', '''status_done:
\tg_owner.phase = 0;
\t/* This is the local phase end boundary, not an atomic current-owner snapshot. */
\tem_trace(ST_OWNER_PHASE, 0, g_owner.capture ? ET_RAW : 0, g_session_generation);''')
    s = replace(s, '''            g_control_active = 1;
''', '''            g_control_active = 1;
            em_trace(ST_OWNER_TAKE, em_trace_identity(request->bytes),
                em_trace_flags() | ET_CONTROL | (request->raw ? ET_RAW : 0), session);
''')
    s = replace(s, '''                st_unlock(key);
            } else {''', '''                em_trace(ST_OWNER_COMPLETE, em_trace_identity(request->bytes),
                    em_trace_flags() | ET_RAW | (sent ? ET_RESULT : 0)
                    | (session == g_session_generation ? ET_CONTROL : 0), session);
                st_unlock(key);
            } else {''')
    s = replace(s, '''                st_unlock(key);
            }
            g_control_active = 0;''', '''                em_trace(ST_OWNER_COMPLETE, em_trace_identity(request->bytes),
                    em_trace_flags() | (sent ? ET_RESULT : 0)
                    | (session == g_session_generation ? ET_CONTROL : 0), session);
                st_unlock(key);
            }
            g_control_active = 0;''')
    p.write_text(s)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('source', type=Path)
    apply(parser.parse_args().source)
