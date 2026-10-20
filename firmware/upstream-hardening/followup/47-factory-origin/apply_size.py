#!/usr/bin/env python3
"""Optional full-int32-domain stillness arithmetic reduction; not a homing remedy."""
from pathlib import Path
import hashlib
TRACK_PIN='0fa218deffe16bdf1ad08c6cf06f34db034742c60f98d27c407960e94cef17c2'
OLD='''int64_t d   = (int64_t)now - st->at;

	if (d > HOME_STILL_COUNTS || d < -HOME_STILL_COUNTS)'''
NEW='''uint32_t d = now >= st->at ? (uint32_t)now - (uint32_t)st->at
	                          : (uint32_t)st->at - (uint32_t)now;
	if (d > HOME_STILL_COUNTS)'''
def apply(work):
 if not __debug__:raise SystemExit('Assertions required')
 src=Path(work)/'src'
 assert hashlib.sha256((src/'abs_encoder.c').read_bytes()).hexdigest()==TRACK_PIN,'tracker changed'
 p=src/'main.c';s=p.read_text();assert s.count(OLD)==1,'stillness arithmetic anchor changed'
 assert 'st->at = abs_encoder_track();' in s and 'int32_t now = abs_encoder_track();' in s
 p.write_text(s.replace(OLD,NEW))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('work',type=Path);a=p.parse_args();apply(a.work)
