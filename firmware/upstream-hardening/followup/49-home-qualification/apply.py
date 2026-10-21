#!/usr/bin/env python3
"""Frozen AF3.9 guarded drive-budget -> released-settle reference qualification.
Only experimental software reference evidence; no physical endpoint assertion.
"""
import hashlib
from pathlib import Path
HOME_SHA256='a437e0106fb6705c649384476073cf04e0bc7b8e70a4a131213cc0b4f36f216a'
PINS={'motor.c':'748c055eaaa822bbbdcf5fe258b9ea4175538a81cb1d88811adcb7a7d8798f4d','motor.h':'6127d9f2d56be4df2decaca735d273b8a2deb85e6edacd81a4b70438907741ee','abs_encoder.c':'0fa218deffe16bdf1ad08c6cf06f34db034742c60f98d27c407960e94cef17c2','abs_encoder.h':'222b4fd167e64def7a9421dfe452c2bddd071c6cd2116c7914c70fab611c31f7'}
def transform(s):
 def replace(a,b):
  nonlocal s
  assert s.count(a)==1,a
  s=s.replace(a,b)
 replace('\tuint8_t drive_ok = 0, settle_ok = 0;','\tuint8_t drive_ok = 0, settle_ok = 0, released = 0;\n\tint32_t cutoff_anchor = 0;')
 replace('\tif (!drive_ok) goto failed;','''\tif (!drive_ok) {
		/* Expiring the active-drive budget is not itself a reference fault.
		 * Detach BEFORE any encoder/protocol/synchronized PWM operation. */
		drive_ms = millis() - t0;
		motor_home_release();
		released = 1;
		int64_t travel = (int64_t)before - still.at;
		/* A stale/UART-crossed deadline, moving last sample, wrong polarity,
		 * or implausible net travel cannot enter the released settle path.
		 * Re-observation of the driven anchor is corroboration, not proof
		 * of an endpoint: mid-travel stiction remains indistinguishable. */
		if (drive_ms != HOME_MS ||
		    (uint32_t)(iteration_ms - still.t) == 0 ||
		    (uint32_t)(iteration_ms - still.t) >= HOME_MS ||
		    travel <= HOME_STILL_COUNTS ||
		    travel > FOCUS_TRAVEL_COUNTS + HOME_STILL_COUNTS)
			goto failed;
		cutoff_anchor = still.at;
		if (home_cancel_requested()) goto cancelled;
	}''')
 replace('\tif (!STOCK.dry) {\n\t\t/* Brake into', '\tif (!STOCK.dry && !released) {\n\t\t/* Brake into')
 replace('\tfailure = ST_HOME_SETTLE;\n\tt0 = millis();\n\titeration_ms = t0;\n\thome_still_init(&still);','''\tfailure = ST_HOME_SETTLE;
	t0 = millis();
	iteration_ms = t0;
	if (released) { still.at = cutoff_anchor; still.t = t0; }
	else home_still_init(&still);''')
 replace('\t\tif ((uint32_t)(millis() - t0) >= HOME_SETTLE_MIN_MS','''\t\t/* Do not turn post-release movement into a fresh successful anchor. */
		if (released) {
			int64_t drift = (int64_t)abs_encoder_track() - cutoff_anchor;
			if (drift > HOME_STILL_COUNTS || drift < -HOME_STILL_COUNTS)
				goto failed;
		}
		if ((uint32_t)(millis() - t0) >= HOME_SETTLE_MIN_MS''')
 replace('\t\t    && home_still_for(&still, HOME_STILL_MS)\n\t\t    && (uint32_t)(millis() - t0) < HOME_SETTLE_MS)', '\t\t    && (released ? (uint32_t)(millis() - t0) >= HOME_STILL_MS\n\t\t                 : home_still_for(&still, HOME_STILL_MS))\n\t\t    && (uint32_t)(millis() - t0) < HOME_SETTLE_MS)')
 replace('\tafter = abs_encoder_track();','''\tafter = abs_encoder_track();
	if (released && ((int64_t)after - cutoff_anchor > HOME_STILL_COUNTS ||
	                 (int64_t)after - cutoff_anchor < -HOME_STILL_COUNTS))
		goto failed;''')
 replace('\tabs_encoder_track_reset();','''\t/* Commit the reference from the same final validated encoder sample. */
	if (!abs_encoder_home_reset(still.at, HOME_STILL_COUNTS)) goto failed;''')
 return s.replace("0x39 tag", "0x40 tag").replace("home[0] = 0x39u", "home[0] = 0x40u")

def apply(work):
 work=Path(work);p=work/'src/main.c';s=p.read_text();lo=s.index('static void motor_home(void)\n{');hi=s.index('\n}',lo)+2;old=s[lo:hi]
 assert hashlib.sha256(old.encode()).hexdigest()==HOME_SHA256,'AF3.9 motor_home pin'
 for n,h in PINS.items():assert hashlib.sha256((work/'src'/n).read_bytes()).hexdigest()==h,n
 s=s[:lo]+transform(old)+s[hi:]
 lo=s.index('static uint8_t home_command(void)\n{');hi=s.index('\n}',lo)+2;old=s[lo:hi]
 assert hashlib.sha256(old.encode()).hexdigest()=='be6aac229c9010da7b3bccb1f1913adce823e5d84de3e421315d2a985848c183','AF3.9 home_command pin'
 p.write_text(s[:lo]+old.replace('home[0] == 0x39','home[0] == 0x40')+s[hi:])
 p=work/'src/motor.h';p.write_text(p.read_text()+'\n/* GPIO detach first, then clear stale PWM while detached. Never remux. */\nvoid motor_home_release(void);\n')
 p=work/'src/motor.c';p.write_text(p.read_text()+'''
void motor_home_release(void)
{
	motor_emergency_release();
	/* Existing bounded waits may inhibit; no path here reattaches pins. */
	pair_a(0, 0);
	pair_b(0, 0);
}
''')
 p=work/'src/abs_encoder.h';p.write_text(p.read_text().replace('void    abs_encoder_track_reset(void);','void    abs_encoder_track_reset(void);\nuint8_t abs_encoder_home_reset(int32_t anchor, uint16_t tolerance);'))
 p=work/'src/abs_encoder.c';p.write_text(p.read_text()+'''
/* One sampled coordinate must both qualify and establish the new reference.
 * track() updates g_track_last; resetting g_track needs no second raw read. */
uint8_t abs_encoder_home_reset(int32_t anchor, uint16_t tolerance)
{
	int64_t delta = (int64_t)abs_encoder_track() - anchor;
	if (motor_is_inhibited() || delta > tolerance || delta < -(int64_t)tolerance)
		return 0;
	g_track = 0;
	return 1;
}
''')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('work',type=Path);apply(p.parse_args().work)
