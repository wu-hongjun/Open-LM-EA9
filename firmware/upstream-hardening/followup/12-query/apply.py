"""Future-version query ownership overlay; apply only to disposable private copies."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def apply(work: Path):
    work = Path(work).resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private'), 'private scratch source required'
    p = work / 'src/main.c'
    s = p.read_text()
    start = s.index('static void focus_answer_queries(void)\n{')
    end = s.index('\n}\n', start) + 3
    old = s[start:end]
    assert 'while (em_take_query(&tag, &operand))' in old
    new = '''static void focus_answer_queries(void)
{
    /* A pass is bounded even when RX replenishes the queue during conversion. */
    for (uint8_t budget = 0; budget < EM_QUERY_Q; budget++) {
        uint8_t tag;
        uint16_t operand, value;
        uint32_t key = st_lock();
        if (!em_handshake_done || g_aborted || em_shutdown_requested() ||
            motor_is_inhibited()) {
            st_unlock(key);
            return;
        }
        /* Capture ownership and dequeue under the same outer interrupt mask. */
        uint32_t session = em_session_generation();
        uint8_t taken = em_take_query(&tag, &operand);
        st_unlock(key);
        if (!taken) return;

        /* The optical conversion is deliberately outside the critical section. */
        if (tag == EM_REC_Q_POS2D) {
            value = focus_distance_code(focus_em06_to_counts(operand),
                                        EM_FOCAL_MM10);
        } else {
            value = focus_counts_to_em06(focus_counts_for_code(operand,
                                                              EM_FOCAL_MM10));
        }
        key = st_lock();
        if (session == em_session_generation() && em_handshake_done &&
            !g_aborted && !em_shutdown_requested() && !motor_is_inhibited()) {
            em_post_query_answer(tag, value);
        }
        st_unlock(key);
    }
}
'''
    p.write_text(s[:start] + new + s[end:])
