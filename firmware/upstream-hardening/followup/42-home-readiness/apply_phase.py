#!/usr/bin/env python3
"""Optional phase attribution, strictly after the AF3.7 query-liveness overlay."""
import hashlib
from pathlib import Path
MAIN_PIN='a5491d071953c51d14c5875ff2018d01adc2d3ba2dbf9972cdb3c7a949c53b68'
HEADER_PIN='7803b5caab6e50c50169aa08ace0c977b1a0f33ea8061cdbe9363dd41abdf9c7'
def apply_phase_labels(work):
    src=Path(work)/'src';main=src/'main.c';header=src/'startup_trace.h'
    assert hashlib.sha256(main.read_bytes()).hexdigest()==MAIN_PIN, 'Expected liveness overlay main'
    assert hashlib.sha256(header.read_bytes()).hexdigest()==HEADER_PIN, 'Expected AF3.7 trace header'
    text=main.read_text()
    old='\tuint8_t drive_ok = 0, settle_ok = 0;'
    assert text.count(old)==1
    text=text.replace(old,old+'\n\tuint8_t failure = ST_HOME_DRIVE;')
    old='if (++polls >= HOME_POLL_LIMIT) goto failed;'
    assert text.count(old)==2
    text=text.replace(old,'if (++polls >= HOME_POLL_LIMIT) goto budget_failed;')
    old='\tt0 = millis();\n\thome_still_init(&still);\n\twhile ((uint32_t)(millis() - t0) < HOME_SETTLE_MS)'
    assert text.count(old)==1
    text=text.replace(old,'\tfailure = ST_HOME_SETTLE;\n'+old)
    old='\treturn;\nfailed:\n\tg_home_state = HOME_FAILED;\n\tst_inhibit_fault(ST_HOME_FAILED);'
    assert text.count(old)==1
    text=text.replace(old,'\treturn;\nbudget_failed:\n\tfailure = ST_HOME_BUDGET;\nfailed:\n\tg_home_state = HOME_FAILED;\n\tst_inhibit_fault(failure);')
    h=header.read_text();old='ST_SERVO_WRONG_WAY=15, ST_ENCODER_OVERFLOW=16'
    assert h.count(old)==1
    h=h.replace(old,old+',\n    ST_HOME_DRIVE=17, ST_HOME_SETTLE=18, ST_HOME_BUDGET=19')
    main.write_text(text);header.write_text(h)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('work',type=Path);a=p.parse_args();apply_phase_labels(a.work)
