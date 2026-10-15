"""Terminal-only trace v2 overlay; modifies only caller's staged build tree.

Apply after lanes 01/02/03/05. No writer changes, no erases, no quiet-window
flush. First 24 + latest 24 events use the existing 576-byte event allocation.
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def once(s, old, new):
    assert s.count(old) == 1, (old[:100], s.count(old))
    return s.replace(old, new, 1)

def apply(work: Path):
    work = Path(work).resolve()
    assert work != ROOT/'firmware/upstream-diagnostic/build'
    p = work/'src/main.c'; s = p.read_text()
    a = s.index('\t\t/* Persist once only after an incomplete handshake goes quiet. */')
    b = s.index('\n\n', a)
    s = s[:a] + '\t\t/* Trace stays in RAM until terminal shutdown or fail-stop. */' + s[b:]
    p.write_text(s)
    p = work/'src/emount.c'; s = p.read_text()
    flush = '\t\t\tst_flush(1,millis(),em_rx_bytes,(uint16_t)em_rx_errors,em_rx_status,(uint8_t)(em_pin_level(EM_PIN_BODY_CS)|(em_pin_level(EM_PIN_BODY_VD)<<1)));'
    s = once(s, flush, '\t\t\t/* No flash write on inferred bus silence: a late body may arrive. */')
    p.write_text(s)
    p = work/'src/startup_trace.c'; s = p.read_text()
    s = once(s, 'static uint32_t last_rx_ms;', 'static uint32_t last_rx_ms;\nstatic uint8_t tail, sealed, shutdown;')
    s = once(s, 'last_rx_ms=0;', 'last_rx_ms=0; tail=sealed=shutdown=0;')
    s = once(s, 'if (kind==ST_FAULT) fault=id;', 'if (kind==ST_FAULT) fault=id;\n    if (kind==ST_SHUTDOWN) shutdown=1;')
    s = once(s, 'else if (dropped!=65535) dropped++;', '''else {
        /* Keep initial breadcrumbs and the most recent 24 events. No shift,
         * allocation or division on the IRQ path. dropped counts eviction. */
        events[24u+tail]=(struct event){ms,kind,id,cls,seq,length,operand};
        if (++tail==24u) tail=0;
        if (dropped!=65535) dropped++;
    }''')
    s = once(s, 'p[4]=1;', 'p[4]=2;')
    a=s.index('void st_flush('); b=s.index('int st_preserve_first_window(',a)
    s=s[:a]+(HERE/'flush.inc').read_text()+s[b:]
    s = once(s, '        if (id==8 && cls==2 && length>7) { capability=(uint8_t)(operand>>8); capability_seen=1; }', '')
    s = once(s, '    if (kind==ST_TX) {', '    if (kind==ST_CAPABILITY) { capability=id; capability_seen=1; }\n    if (kind==ST_TX) {')
    s += '\n/* First nonterminal inhibit reason; summary only, no NVM or timing guess. */\nvoid st_inhibit_fault(uint8_t reason) {\n    uint32_t key=st_lock(); if (!fault) fault=reason; st_unlock(key);\n}\n'
    p.write_text(s)
    p=work/'src/startup_trace.h';s=p.read_text()
    s=once(s,'ST_WINDOW_PRESERVED=7, ST_BAD_RX=8, ST_SHUTDOWN=9','ST_WINDOW_PRESERVED=7, ST_BAD_RX=8, ST_SHUTDOWN=9, ST_CAPABILITY=10')
    s=once(s,'ST_CS_FALL_WAIT=9','ST_CS_FALL_WAIT=9, ST_RX_DRAIN_FAULT=10, ST_HOME_FAILED=11,\n    ST_MOTOR_BUDGET=12, ST_SERVO_BUDGET=13, ST_SERVO_RUNAWAY=14,\n    ST_SERVO_WRONG_WAY=15, ST_ENCODER_OVERFLOW=16')
    s += '\n/* RAM-only first inhibit reason, never a flush. */\nvoid st_inhibit_fault(uint8_t reason);\n'
    p.write_text(s)
    p=work/'src/emount.c';s=p.read_text()
    old='\tst_note(ST_RX,rx[5],rx[3],rx[4],n,n>7 ? (uint16_t)(rx[6]|((uint16_t)rx[7]<<8)) : 0,millis());'
    new=old.replace('n>7 ?', 'view.length>=11u ?')+'\n\t/* Observed complete payload only; this is not committed negotiation. */\n\tif (rx[3]==EM_CLASS_INIT && rx[5]==0x08u && view.length>=11u)\n\t\tst_note(ST_CAPABILITY,rx[7],rx[3],rx[4],n,0,millis());'
    s=once(s,old,new);p.write_text(s)
    # Low-cost RAM-only fault facts at the reviewed motion-inhibit reasons.
    edits={
        'main.c': [('\tg_home_state = HOME_FAILED;', '\tg_home_state = HOME_FAILED;\n\tst_inhibit_fault(ST_HOME_FAILED);')],
        'em_uart.c': [('\t\tg_rx_invalid = g_rx_fault = 1;', '\t\tg_rx_invalid = g_rx_fault = 1;\n\t\tst_inhibit_fault(ST_RX_DRAIN_FAULT);')],
        'motor.c': [('if (++polls >= 1000000u) { motor_inhibit();', 'if (++polls >= 1000000u) { st_inhibit_fault(ST_MOTOR_BUDGET); motor_inhibit();')],
        'servo.c': [('#include "servo.h"', '#include "servo.h"\n#include "startup_trace.h"'),
            ('if (++polls >= 1000000u) { motor_inhibit();', 'if (++polls >= 1000000u) { st_inhibit_fault(ST_SERVO_BUDGET); motor_inhibit();'),
            ('if (out->outcome == SERVO_RUNAWAY || out->outcome == SERVO_WRONG_WAY) motor_inhibit();', 'if (out->outcome == SERVO_RUNAWAY || out->outcome == SERVO_WRONG_WAY) {\n\t\tst_inhibit_fault(out->outcome == SERVO_RUNAWAY ? ST_SERVO_RUNAWAY : ST_SERVO_WRONG_WAY);\n\t\tmotor_inhibit();\n\t}')],
        'abs_encoder.c': [('\t\tmotor_inhibit();', '\t\tst_inhibit_fault(ST_ENCODER_OVERFLOW);\n\t\tmotor_inhibit();')],
    }
    for name, replacements in edits.items():
        p=work/'src'/name;s=p.read_text()
        for old,new in replacements:s=once(s,old,new)
        p.write_text(s)
