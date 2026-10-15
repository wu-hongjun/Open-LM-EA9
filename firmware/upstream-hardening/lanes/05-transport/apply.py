"""Transport overlay after frame, explicit TX result, lanes 02, 01 and 03.

Only a caller-owned staging directory is modified. Never patches frozen inputs.
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent

def once(s, a, b):
    assert s.count(a) == 1, (a[:100], s.count(a))
    return s.replace(a, b, 1)

def apply(work: Path):
    work = Path(work).resolve()
    assert work != HERE.parents[3] / 'firmware/upstream-diagnostic/build'
    p = work/'src/emount.c'; s = p.read_text()
    s = once(s, '#include "em_owner.h"', '#include "em_owner.h"\n#include <string.h>')
    a = s.index('static uint8_t em_transmit(')
    b = s.index('\n/* The shutdown acknowledgement:', a)
    s = s[:a] + (HERE/'transmit.inc').read_text() + s[b:]
    p.write_text(s)
    p = work/'src/em_eic.h'
    p.write_text(once(p.read_text(), '#endif /* EM_EIC_H */',
        '/* CS edge latched but not yet dispatched; read under the TX admission lock. */\n'
        'int em_eic_receive_pending(void);\n\n#endif /* EM_EIC_H */'))
    p = work/'src/em_eic.c'
    p.write_text(p.read_text() + '\nint em_eic_receive_pending(void)\n{\n'
        '\treturn (EIC->INTFLAG.reg & (1u << EM_EXTINT_BODY_CS)) != 0;\n}\n')
    p = work/'src/em_uart.c'; s = p.read_text()
    s = once(s, 'static volatile uint8_t  g_disabled;',
        'static volatile uint8_t  g_disabled;\nstatic volatile uint8_t g_rx_invalid;\nstatic volatile uint8_t g_rx_fault;')
    s = once(s, '\twhile (EMSERCOM->USART.INTFLAG.bit.RXC) {',
        '\t/* At most four FIFO reads per entry, including a stuck RXC fault. */\n'
        '\tunsigned budget = 4;\n'
        '\twhile (budget-- && EMSERCOM->USART.INTFLAG.bit.RXC) {')
    s = once(s, '\t\t\tg_rx[g_rx_len++] = b;\n\t\t}',
        '\t\t\tg_rx[g_rx_len++] = b;\n\t\t} else {\n\t\t\tg_rx_invalid = 1;\n\t\t}')
    s = once(s, '\t/* An overrun or framing error',
        '\tif (EMSERCOM->USART.INTFLAG.bit.RXC) {\n'
        '\t\t/* Prevent unbounded priority-zero tail chaining on a stuck source.\n'
        '\t\t * Fail closed until physical reset; do not reuse a stale FIFO. */\n'
        '\t\tg_rx_invalid = g_rx_fault = 1;\n'
        '\t\tEMSERCOM->USART.INTENCLR.reg = SERCOM_USART_INTENCLR_RXC;\n'
        '\t}\n\t/* An overrun or framing error')
    s = once(s, '\t\tem_rx_errors++;', '\t\tg_rx_invalid = 1;\n\t\tem_rx_errors++;')
    s = once(s, 'void em_uart_rx_reset(void)\n{',
        'void em_uart_rx_reset(void)\n{\n'
        '\t/* SERCOM priority zero must not append midway through this reset. */\n'
        '\tuint32_t key = st_lock();')
    s = once(s, '\tg_rx_len = 0;\n}', '\tg_rx_len = 0;\n'
        '\t/* A disabled RXC interrupt marks a fatal drain fault; only reset heals it. */\n'
        '\tif (!g_rx_fault) g_rx_invalid = 0;\n'
        '\tst_unlock(key);\n}')
    s = once(s, '\treturn g_rx_len;', '\treturn g_rx_invalid ? 0 : g_rx_len;')
    p.write_text(s)
    p=work/'tools/hosttest/shim.c'
    if p.exists():
        s=p.read_text()
        assert 'em_eic_receive_pending' not in s
        p.write_text(s+'\nint em_eic_receive_pending(void) { return 0; }\n')
