#!/usr/bin/env python3
"""AF3.8-bound failed-home observation. No changes to readiness/motor policy."""
import hashlib
from pathlib import Path
MAIN_PIN='e2174bc47f5f056b0111b1c9d97912497330ea1da7cdce7b0a3669e28e35c771'
def transform(s):
 old='\tuint8_t failure = ST_HOME_DRIVE;';assert s.count(old)==1
 s=s.replace(old,old+'\n\tuint32_t loop_ms, iteration_ms;')
 old='\ti  = 0;\n\thome_still_init(&still);';assert s.count(old)==1
 s=s.replace(old,'\ti  = 0;\n\titeration_ms = t0;\n\thome_still_init(&still);')
 for cap in ['HOME_MS','HOME_SETTLE_MS']:
  old='while ((uint32_t)(millis() - t0) < '+cap+') {';assert s.count(old)==1
  s=s.replace(old,'while ((uint32_t)((loop_ms = millis()) - t0) < '+cap+') {\n\t\titeration_ms = loop_ms;')
 old='\tfailure = ST_HOME_SETTLE;\n\tt0 = millis();';assert s.count(old)==1
 s=s.replace(old,old+'\n\titeration_ms = t0;')
 old='\tmotor_inhibit();\n\tg_next_pending = 0;\ncancelled:';assert s.count(old)==1
 s=s.replace(old,'''\tmotor_inhibit();
\tg_next_pending = 0;
\t/* motor_inhibit has already detached the drive pins. Record only values
\t * used by homing; no new encoder/ADC read and no live-drive timestamp. */
\t{
\t\t/* The backing member is a byte array; GNU may_alias permits word
\t\t * stores without violating its declared effective type. */
\t\ttypedef uint32_t home_word __attribute__((may_alias));
\t\thome_word *home = (home_word *)(void *)(st_motion_data() + 112u);
\t\thome[1] = t0;
\t\thome[2] = millis();
\t\thome[3] = (uint32_t)before;
\t\thome[4] = (uint32_t)still.at;
\t\thome[5] = still.t;
\t\thome[6] = polls;
\t\thome[7] = iteration_ms;
\t\t/* 0x39 tag, phase, flags bit0=drive qualified, suppressed count=0. */
\t\thome[0] = 0x39u | ((uint32_t)failure << 8) | ((uint32_t)drive_ok << 16);
\t}
cancelled:''')
 return s
def apply(work):
 p=Path(work)/'src/main.c';assert hashlib.sha256(p.read_bytes()).hexdigest()==MAIN_PIN,'Expected frozen AF3.8 main'
 p.write_text(transform(p.read_text()))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('work',type=Path);a=p.parse_args();apply(a.work)
