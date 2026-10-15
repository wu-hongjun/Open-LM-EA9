"""Apply only to a fresh source copy; frame admission must already be present."""
from pathlib import Path
import re
import shutil
HERE = Path(__file__).resolve().parent

def apply(work: Path):
    work = Path(work).resolve()
    root = HERE.parents[3]
    assert work != root / 'firmware/upstream-diagnostic/build', 'Never mutate released source inputs'
    p = work/'src/emount.c'
    s = p.read_text()
    assert '#include "em_frame.h"' in s, 'Apply complete frame admission first'
    def rep(a,b):
        nonlocal s
        assert s.count(a)==1, (a, s.count(a))
        s=s.replace(a,b)
    rep('#include "em_frame.h"','#include "em_frame.h"\n#include "em_owner.h"')
    rep('static volatile uint8_t  g_reply_pending;\nstatic volatile uint8_t  g_reply_id;',
        'static struct em_owner g_owner;\nstatic const struct em_owned_request *g_retry;\nstatic uint8_t g_control_active;\nstatic volatile uint32_t g_session_generation;\n'
        'uint32_t em_session_generation(void) { return g_session_generation; }\n'
        'uint16_t em_control_overflow(void) { return g_owner.overflow; }\n'
        'static void em_reset_session_queues(void);')
    rep('static volatile uint8_t  g_req[EM_REQ_SNAP];', 'static const uint8_t *g_req;')
    rep('static void em_transmit(uint8_t *frame, uint16_t len)',
        'static uint8_t em_transmit(uint8_t *frame, uint16_t len)')
    rep('\tem_uart_send(frame, len);',
        '\tif (!em_uart_send(frame, len)) {\n'
        '\t\tPORT->Group[0].OUTCLR.reg = (1u << EM_PIN_LENS_CS);\n'
        '\t\treturn 0;\n\t}')
    rep('\tst_note(ST_TX,frame[5],frame[3],frame[4],len,0,millis());',
        '\tst_note(ST_TX,frame[5],frame[3],frame[4],len,0,millis());\n\treturn 1;')
    start=s.index('static void em_send_id(')
    end=s.index('/* Where message 0x04',start)
    section=s[start:end].replace('static void em_send_id(', 'static uint8_t em_send_id(')
    section=section.replace('return;', 'return 1;')
    section=section.replace('em_transmit(frame, p->len);', 'return em_transmit(frame, p->len);')
    s=s[:start]+section+s[end:]

    # Existing admission overlay changes this loop to view.length.
    s,n=re.subn(r'\tfor \(uint16_t i = 0; i < EM_REQ_SNAP; i\+\+\) \{\n\t\tg_req\[i\] = \(i < (?:n|view.length)\) \? rx\[i\] : 0;\n\t\}\n','',s)
    assert n==1
    rep('\tif (level) {\n\t\tem_uart_rx_reset();',
        '\tem_owner_cs(&g_owner, level);\n\tif (level) {\n\t\tg_status_due = 0;\n\t\tem_uart_rx_reset();')
    rep('\t\tg_reply_id      = rx[5];\n\t\tg_reply_pending = 1;',
        '\t\tif (em_owner_offer(&g_owner, rx, view.length)\n'
        '\t\t    && !g_owner.capture && rx[5] == EM_ID_SESSION) {\n'
        '\t\t\tg_session_generation++;\n\t\t\tem_reset_session_queues();\n'
        '\t\t\tg_retry = 0;\n\t\t\tem_handshake_done = 0;\n'
        '\t\t\tem_t_handshake = 0;\n\t\t\tg_status_due = 0;\n'
        '\t\t\tg_owner.status_enabled = 0;\n\t\t}')
    rep('\tif (em_handshake_done) {\n\t\tg_status_due = 1;',
        '\tem_owner_vd(&g_owner);\n\tif (g_owner.status_enabled && !g_owner.receiving) {\n\t\tg_status_due = 1;')
    # Ordinary stored replies retain their template sequence, matching the
    # factory 0x58a4 handler. Only status carries sampled request sequence+1;
    # raw capture echoes retain the incoming request sequence exactly.
    rep('void em_pump_status(void)\n{', 'void em_pump_status(void)\n{\n\tif (g_control_active || g_retry) return;')
    rep('\tg_status_due = 0;\n\n\tea9_data[EA9_OFF_05 + 4] = g_reply_seq;\n\tea9_data[EA9_OFF_06 + 4] = g_reply_seq;',
        '\t{\n\t\tuint32_t key = st_lock();\n'
        '\t\tint ready = em_owner_status_begin(&g_owner);\n'
        '\t\tuint8_t sequence = g_reply_seq;\n'
        '\t\tif (ready) g_status_due = 0;\n'
        '\t\tst_unlock(key);\n\t\tif (!ready) return;\n'
        '\t\tea9_data[EA9_OFF_05 + 4] = sequence;\n'
        '\t\tea9_data[EA9_OFF_06 + 4] = sequence;\n\t}')
    rep('\tdelay_us(EM_LEAD_US);',
        '\tdelay_us(EM_LEAD_US);\n'
        '\tif (!em_owner_status_valid(&g_owner)) goto status_done;')
    rep('\tdelay_us(EM_STATUS_GAP_US);',
        '\tif (!em_owner_status_valid(&g_owner)) goto status_done;\n'
        '\tdelay_us(EM_STATUS_GAP_US);\n'
        '\tif (!em_owner_status_valid(&g_owner)) goto status_done;')
    rep('\t\tem_transmit(&ea9_data[EA9_OFF_06], len);',
        '\t\tif (!em_owner_status_valid(&g_owner)) goto status_done;\n'
        '\t\tem_transmit(&ea9_data[EA9_OFF_06], len);')
    rep('\tem_transmit(&ea9_data[EA9_OFF_05], EA9_LEN_05);',
        '\tif (!em_transmit(&ea9_data[EA9_OFF_05], EA9_LEN_05)) goto status_done;')
    rep('\t\tem_transmit(&ea9_data[EA9_OFF_06], len);',
        '\t\tif (!em_transmit(&ea9_data[EA9_OFF_06], len)) goto status_done;')
    rep('\tif (!em_t_first_status) {\n\t\tem_t_first_status = millis();\n\t}\n}',
        '\tif (!em_t_first_status) {\n\t\tem_t_first_status = millis();\n\t}\n'
        'status_done:\n\tg_owner.phase = 0;\n}')
    begin=s.index('\tif (g_reply_pending) {',s.index('void em_poll(void)'))
    end=s.index('\n\tem_pump_status();',begin)
    s=s[:begin]+'''\t{
        uint32_t key = st_lock();
        uint32_t session = g_session_generation;
        const struct em_owned_request *request = g_retry ? g_retry : em_owner_take(&g_owner);
        st_unlock(key);
        if (request) {
            uint8_t id = request->bytes[5];
            g_retry = request;
            g_req = request->bytes;
            g_control_active = 1;
            if (request->raw) {
                delay_us(EM_LEAD_US);
                if (em_transmit((uint8_t *)request->bytes, request->length)) {
                    g_retry = 0;
                    g_owner.status_enabled = 0;
                    g_status_due = 0;
                }
            } else {
                uint8_t sent = em_send_id(id);
                if (sent) g_retry = 0;
                if (sent && id == 0x0au && session == g_session_generation) {
                    g_owner.status_enabled = 1;
                    if (!em_handshake_done) {
                        em_handshake_done = 1;
                        st_note(ST_HANDSHAKE,id,0,0,0,0,millis());
                        em_t_handshake = millis();
                    }
                }
            }
            g_control_active = 0;
        }
    }
''' + s[end:]
    # All returns introduced by lane02 inside an active status phase must
    # release that phase. Its pre-entry guard can also safely clear phase.
    if 'em_shutdown_requested()' in s:
        s=s.replace('g_reply_pending=0;', 'em_owner_cancel(&g_owner);')
        rep('if (sent && id == 0x0au && session == g_session_generation) {', 'if (sent && id == 0x0au && session == g_session_generation && !em_shutdown_requested()) {')
        rep('\tPORT->Group[0].OUTSET.reg = (1u << EM_PIN_LENS_CS);\n\tif (!em_uart_send(frame, len)) {',
            '\tif (em_shutdown_requested() && !(g_shutdown.state == EM_SD_ACTIVE\n'
            '\t    && frame == g_shutdown.request)) return 0;\n'
            '\tPORT->Group[0].OUTSET.reg = (1u << EM_PIN_LENS_CS);\n\tif (!em_uart_send(frame, len)) {')
        rep('em_transmit(g_shutdown.request,g_shutdown.length);',
            'if (!em_transmit(g_shutdown.request,g_shutdown.length)) {\n'
            '        g_shutdown.state=EM_SD_PENDING; return;\n    }')
        a=s.index('void em_pump_status(void)')
        b=s.index('\nvoid em_poll(void)',a)
        section=s[a:b]
        section=section.replace('if (em_shutdown_requested()) return;',
                                'if (em_shutdown_requested()) goto status_done;')
        s=s[:a]+section+s[b:]
        # The shutdown lane owns its latch; discard ordinary pending work
        # before its dedicated dispatcher runs, never replace its snapshot.
        rep('\tg_in_poll = 1;', '\tg_in_poll = 1;\n'
            '\tif (em_shutdown_requested()) {\n'
            '\t\tuint32_t key = st_lock();\n'
            '\t\tem_owner_cancel(&g_owner);\n\t\tg_retry = 0;\n'
            '\t\tst_unlock(key);\n\t}')
    rep('static volatile uint8_t  g_ans_n;',
        'static volatile uint8_t  g_ans_n;\n'
        'static void em_reset_session_queues(void)\n{\n'
        '    em_focus_pending = 0;\n    g_query_n = 0;\n'
        '    g_event_n = 0;\n    g_ans_n = 0;\n}\n')
    # ISR publication cannot overwrite a command while foreground copies it,
    # nor can a session reset race query-pop's count decrement.
    for name, following in [('em_take_focus_cmd','uint8_t em_take_query'),
                            ('em_take_query','void em_init')]:
        start=s.index('uint8_t '+name+'(')
        end=s.index(following,start)
        section=s[start:end]
        section=section.replace('\tuint8_t k;', '\tuint8_t k;\n\tuint32_t key = st_lock();')
        section=section.replace('return 0;', 'st_unlock(key); return 0;')
        section=section.replace('return 1;', 'st_unlock(key); return 1;')
        s=s[:start]+section+s[end:]
    for name, following in [('em_post_event','/* The answers waiting'),
                            ('em_post_query_answer','void em_scan_finish')]:
        start=s.index('void '+name+'(')
        end=s.index(following,start)
        section=s[start:end]
        section=section.replace('\n{\n', '\n{\n\tuint32_t key = st_lock();\n',1)
        pos=section.rfind('}')
        section=section[:pos]+'\tst_unlock(key);\n'+section[pos:]
        s=s[:start]+section+s[end:]
    p.write_text(s)
    for name in ('em_owner.c','em_owner.h'):
        shutil.copyfile(HERE/name,work/'src'/name)
    h=work/'src/emount.h'
    h.write_text(h.read_text()+'\n/* Accepted ordinary session identity; capture return-to-init is distinct. */\n'
                 'uint32_t em_session_generation(void);\nuint16_t em_control_overflow(void);\n')
