"""Serialize request ownership and successful readiness publication.

Apply after 07 (08 may follow or precede), before optional 09 footprint gates.
Only operate on disposable source copies. No image or host installation edits.
"""
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def once(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b,1)
def apply(work: Path):
    work=Path(work).resolve()
    assert work != ROOT/'firmware/upstream-diagnostic/build'
    p=work/'src/emount.c';s=p.read_text()
    s=once(s,'if (em_shutdown_accept(&g_shutdown,rx,n)) {',
        'if (em_shutdown_accept(&g_shutdown,rx,n)) {\n\t\tem_handshake_done=0; /* Admission immediately revokes readiness. */')
    s=once(s,'static uint8_t g_control_active;','static uint8_t g_control_active;\nstatic uint32_t g_control_session;')
    s=once(s,'static uint8_t em_send_id(uint8_t id)','static uint8_t em_send_id(uint8_t id, uint16_t request_length)')
    s=once(s,'&& g_retry->length < 11u)', '&& request_length < 11u)')
    s=once(s,'if (generation != em_cs_edges || em_pin_level(EM_PIN_BODY_CS) || em_eic_receive_pending()',
        'if (generation != em_cs_edges || em_pin_level(EM_PIN_BODY_CS) || em_eic_receive_pending()\n'
        '\t    || (g_control_active && g_control_session != g_session_generation)')
    s=once(s,'''        st_unlock(key);
        if (request) {
            uint8_t id = request->bytes[5];
            g_retry = request;
            g_req = request->bytes;
            g_control_active = 1;''', '''        /* Publish the active owner before an IRQ may invalidate its retry. */
        if (request) {
            g_retry = request;
            g_req = request->bytes;
            g_control_session = session;
            g_control_active = 1;
        }
        st_unlock(key);
        if (request) {
            uint8_t id = request->bytes[5];''')
    s=once(s,'''                if (em_transmit((uint8_t *)request->bytes, request->length)) {
                    g_retry = 0;
                    g_owner.status_enabled = 0;
                    g_status_due = 0;
                }''', '''                uint8_t sent = em_transmit((uint8_t *)request->bytes, request->length);
                key = st_lock();
                if (sent || session != g_session_generation) g_retry = 0;
                if (sent && session == g_session_generation) {
                    g_owner.status_enabled = 0;
                    g_status_due = 0;
                }
                st_unlock(key);''')
    s=once(s,'''                uint8_t sent = em_send_id(id);
                if (sent) g_retry = 0;''', '''                uint8_t sent = em_send_id(id, request->length);
                /* Readiness belongs to the successful request's epoch. No
                 * session/shutdown IRQ can split this check and publication. */
                key = st_lock();
                if (sent || session != g_session_generation) g_retry = 0;''')
    s=once(s,'''                }
            }
            g_control_active = 0;''', '''                }
                st_unlock(key);
            }
            g_control_active = 0;''')
    p.write_text(s)
