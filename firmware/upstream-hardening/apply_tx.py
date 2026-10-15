"""Give the staged upstream transmitter an explicit completion result."""
from pathlib import Path


def apply(work: Path):
    for name in ('em_uart.c','em_uart.h'):
        path=work/'src'/name; text=path.read_text()
        # Some archived header formatting is single-spaced; require exactly
        # one semantic declaration rather than silently missing it.
        import re
        text,n=re.subn(r'void\s+em_uart_send\(', 'uint8_t em_uart_send(',text)
        assert n==1,(name,n)
        if name.endswith('.c'):
            start=text.index('uint8_t em_uart_send(')
            prefix,body=text[:start],text[start:]
            assert body.count('\t\treturn;')==1
            body=body.replace('\t\treturn;','\t\treturn 0;',1)
            needle='\tST_WAIT_WHILE(!EMSERCOM->USART.INTFLAG.bit.TXC, ST_UART_WAIT);\n}'
            assert body.count(needle)==1
            body=body.replace(needle,needle[:-1]+'\treturn 1;\n}')
            text=prefix+body
        else:
            text=text.replace('/* Blocking: shifts every byte out and returns once the last one has left the\n'
                              ' * shift register, so the caller can time the chip-select release from it. */',
                              '/* Blocking: returns 1 after the final byte leaves the shift register\n'
                              ' * (TXC), or 0 when disabled. The caller owns chip-select release. */')
        path.write_text(text)
    path=work/'tools/hosttest/shim.c'; text=path.read_text()
    assert text.count('void em_uart_send(')==1
    text=text.replace('void em_uart_send(','uint8_t em_uart_send(',1)
    start=text.index('uint8_t em_uart_send('); end=text.index('\n}\n',start)
    body=text[start:end]
    # A full host capture is a failed synthetic send, not a successful one.
    assert body.count('sent_overflow++;')==1
    body=body.replace('sent_overflow++;','sent_overflow++;\n\t\treturn 0;')+'\n\treturn 1;'
    path.write_text(text[:start]+body+text[end:])
