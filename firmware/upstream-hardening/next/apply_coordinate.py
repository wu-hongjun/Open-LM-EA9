"""Arithmetic-domain admission for a future image; operates on private scratch."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PINS={'abs_encoder.h':'271a3812014b3cbb37cc0886c1b109e1d96e1eb40693d35f274665a6e92e6ef0','abs_encoder.c':'5ca6304a138f01bfc5cd757513186f8e170cafd71d2d34d82e65761f0b604777'}
def apply(work):
    work=Path(work).resolve()
    assert work.is_relative_to(ROOT/'artifacts/private'), 'private scratch required'
    src=work/'src'
    for n,h in PINS.items():assert hashlib.sha256((src/n).read_bytes()).hexdigest()==h,n
    p=src/'abs_encoder.h';s=p.read_text();anchor='#include <stdint.h>'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'''

/* Admitted software coordinate capacity, NOT a physical endstop or calibration.
 * This invariant bounds fixed-point differences/products in main/servo/predictor.
 * A reading beyond it latches inhibition and retains the last admitted value.
 * Changing the limit requires repeating the complete arithmetic range proof. */
#define ENC_TRACK_LIMIT 65536
''');p.write_text(s)
    p=src/'abs_encoder.c';s=p.read_text();old='''	/* Never wrap the software coordinate into an unrelated target. */
	if ((d > 0 && g_track > INT32_MAX - d) ||
	    (d < 0 && g_track < INT32_MIN - d)) {'''
    assert s.count(old)==1
    s=s.replace(old,'''	/* Check capacity before addition. Both bounds are representable for
	 * every 14-bit shortest difference, even if g_track is corrupted. */
	if (g_track > ENC_TRACK_LIMIT - d ||
	    g_track < -ENC_TRACK_LIMIT - d) {''');p.write_text(s)
