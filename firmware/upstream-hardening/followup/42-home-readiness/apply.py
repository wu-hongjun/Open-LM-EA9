#!/usr/bin/env python3
"""Pinned AF3.7 main-only operand-query liveness overlay; no motion policy edits."""
import hashlib
from pathlib import Path
BASE_MAIN = 'bced63a23f968215c554ff2f45c259abd13df85658e8036e28999512195f04c7'
def transform(text):
    old = '            motor_is_inhibited()) {'
    assert text.count(old) == 1
    text = text.replace('if (!em_handshake_done || g_aborted || em_shutdown_requested() ||\n'+old,
                        'if (!em_handshake_done || g_aborted || em_shutdown_requested()) {')
    old = '!g_aborted && !em_shutdown_requested() && !motor_is_inhibited()) {'
    assert text.count(old) == 1
    text = text.replace(old, '!g_aborted && !em_shutdown_requested()) {')
    old = '\tfor (;;) {\n\t\tem_poll();'
    assert text.count(old) == 1
    text = text.replace(old, '\tfor (;;) {\n\t\t/* Operand-only queries remain live after motion inhibition. */\n\t\tfocus_answer_queries();\n\t\tem_poll();')
    old = '\t\t\tfocus_report();\n\t\t\tfocus_answer_queries();'
    assert text.count(old) == 1
    return text.replace(old, '\t\t\tfocus_report();')
def apply(work):
    main = Path(work)/'src/main.c'
    assert hashlib.sha256(main.read_bytes()).hexdigest() == BASE_MAIN, 'AF3.7 main pin mismatch'
    main.write_text(transform(main.read_text()))
if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('work',type=Path);a=p.parse_args();apply(a.work)
