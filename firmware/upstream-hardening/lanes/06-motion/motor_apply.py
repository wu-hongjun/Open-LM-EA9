"""Driver inhibition contract for lane06 review, not release approval.

GPIO cutoff keeps the established pin convention and never waits on TCC.
Only the coherent pin-mux attach is IRQ masked; PWM waits run with IRQs enabled.
"""
from pathlib import Path


def apply(work: Path):
    path=work/'src/motor.c'; text=path.read_text()
    def rep(before,after):
        nonlocal text
        assert text.count(before)==1,before
        text=text.replace(before,after,1)
    rep('#include "delay.h"', '#include "delay.h"\n\n'
        'static volatile uint8_t g_motor_inhibited;\n'
        'uint8_t motor_is_inhibited(void) { return g_motor_inhibited; }\n'
        'void motor_emergency_release(void)\n{\n'
        '\tPORT->Group[0].PINCFG[MOTOR_PIN_WO0].bit.PMUXEN=0;\n'
        '\tPORT->Group[0].PINCFG[MOTOR_PIN_WO1].bit.PMUXEN=0;\n'
        '\tPORT->Group[0].PINCFG[MOTOR_PIN_WO2].bit.PMUXEN=0;\n'
        '\tPORT->Group[0].PINCFG[MOTOR_PIN_WO3].bit.PMUXEN=0;\n'
        '\tPORT->Group[0].DIRCLR.reg=(1u<<MOTOR_PIN_WO0)|(1u<<MOTOR_PIN_WO1)\n'
        '\t                         |(1u<<MOTOR_PIN_WO2)|(1u<<MOTOR_PIN_WO3);\n'
        '\tPORT->Group[0].OUTSET.reg=1u<<MOTOR_PIN_WO3;\n}\n'
        'void motor_inhibit(void)\n{\n'
        '\tg_motor_inhibited=1;\n\tmotor_emergency_release();\n}\n')
    start=text.index('void motor_attach_pins(void)\n{')
    end=text.index('\n}\n',start)
    body=text[start:end]
    body=body.replace('{\n','{\n\tuint32_t key=st_lock();\n'
                      '\tif (g_motor_inhibited) { st_unlock(key); return; }\n',1)
    text=text[:start]+body+'\n\tst_unlock(key);'+text[end:]
    for name,args in [('motor_drive','int16_t duty'),('motor_brake','void')]:
        rep('void '+name+'('+args+')\n{',
            'void '+name+'('+args+')\n{\n\tif (g_motor_inhibited) return;')
    rep('void motor_release(void)\n{',
        'void motor_release(void)\n{\n\tif (g_motor_inhibited) { motor_emergency_release(); return; }')
    path.write_text(text)
    path=work/'src/motor.h'; text=path.read_text()
    text+='\n/* Reset-only shutdown/fault latch. GPIO-only, no PWM/NVM waits. */\n'
    text+='void motor_inhibit(void);\nuint8_t motor_is_inhibited(void);\nvoid motor_emergency_release(void);\n'
    path.write_text(text)
