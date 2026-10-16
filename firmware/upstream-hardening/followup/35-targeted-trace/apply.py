"""Apply diagnostic-only v3 and post-UART-disable markers to a private staged tree."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'artifacts/private/handoff36-repeat'

def replace_once(text,old,new):
    assert text.count(old)==1, old
    return text.replace(old,new)

def apply(work):
    work=Path(work).resolve()
    assert work.is_relative_to(ROOT/'artifacts/private') and work!=BASE
    manifest=json.loads((BASE/'manifest.json').read_text())
    # Assert core and hardware writer exact base; main may already contain lane33 hooks.
    for name in ('startup_trace.c','startup_trace.h','startup_trace_flash.c'):
        assert hashlib.sha256((work/'src'/name).read_bytes()).hexdigest()==manifest['sources']['src/'+name], name
    for name in ('startup_trace.c','startup_trace.h','trace_format.h'):
        (work/'src'/name).write_bytes((HERE/name).read_bytes())
    main=work/'src/main.c'
    text=main.read_text()
    text=replace_once(text,'\n\tPORT->Group[0].OUTSET.reg = (1u << 23);\n\tg_pa23_at = millis();',
        '\n\tst_terminal(low >= 2 ? ST_VD_LOW : ST_VD_TIMEOUT, (uint8_t)low, millis());\n'
        '\tPORT->Group[0].OUTSET.reg = (1u << 23);\n\tg_pa23_at = millis();\n'
        '\tst_terminal(ST_PA23, 0, g_pa23_at);')
    text=replace_once(text,'\tdiag_tally_mark(DIAG_MARK_PA23, (uint8_t)low);\n\tdelay_ms(100);\n}',
        '\tdiag_tally_mark(DIAG_MARK_PA23, (uint8_t)low);\n\tdelay_ms(100);\n'
        '\tst_terminal(ST_TAIL_DONE, 0, millis());\n}')
    main.write_text(text)
    flash=work/'src/startup_trace_flash.c'
    text=flash.read_text()
    text=replace_once(text,'    for (;;) __WFI();',
        '    st_terminal(ST_TERMINAL_FAULT,fault,millis());\n    for (;;) __WFI();')
    flash.write_text(text)

if __name__=='__main__':
    import sys
    apply(sys.argv[1])
