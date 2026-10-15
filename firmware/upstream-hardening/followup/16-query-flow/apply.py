"""Future query flow overlay, after followup/12-query; private scratch only."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def apply(work: Path, pump_service=True):
    work = Path(work).resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private'), 'private scratch required'
    p = work / 'src/main.c'
    s = p.read_text()
    assert 'for (uint8_t budget = 0; budget < EM_QUERY_Q; budget++)' in s, 'apply followup12 first'
    q = work / 'src/emount.c'
    em = q.read_text()
    old = 'if (em_shutdown_requested() || !g_query_n) {'
    new = '''/* The only answer producer is the foreground query worker. Its pure
	 * conversion cannot consume another answer slot before publication. */
	if (em_shutdown_requested() || !g_query_n || g_ans_n >= EM_QUERY_Q) {'''
    assert em.count(old) == 1
    q.write_text(em.replace(old, new))
    if pump_service:
        begin = s.index('static void pump(int32_t pos)\n{')
        end = s.index('\n}', begin) + 2
        body = s[begin:end]
        old = '\tem_poll();'
        assert body.count(old) == 1
        body = body.replace(old, '''	/* Operand-only optical conversions need no encoder origin. Keep the
	 * bounded worker outside g_homed so homing can answer them too. */
	focus_answer_queries();
	em_poll();''')
        p.write_text(s[:begin] + body + s[end:])
