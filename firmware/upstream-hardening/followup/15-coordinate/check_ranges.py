#!/usr/bin/env python3
"""Offline exact-integer certificate for the proposed coordinate contract.
Not a device test, control-stability test, or exhaustive firmware execution.
Run from any directory. Reads frozen final-33a; writes no production files.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'firmware/upstream-hardening/build/final-33a'
m = json.loads((BASE / 'manifest.json').read_text())
assert len(m['sources']) == 46
for name, expected in m['sources'].items():
    assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == expected, name
main = (BASE / 'src/main.c').read_text()
stock = main.split('static const struct servo_cfg STOCK = {', 1)[1].split('\n};', 1)[0]
expected = dict(stop_ms=30, v_cruise=25000, ff_div=40, ff_offset=134,
                tau_ms=26, kp_div=50, boost_up=12, boost_down=8,
                boost_max=800, duty_floor=200, tolerance=12,
                settle_counts=40, aim_ahead=0, noise=8, stall_ms=300,
                timeout_ms=3000, total_ms=5000, retarget_max=16,
                retarget_min=12, reverse_brake_ms=20, reverse_brake_above=15000)
for name, value in expected.items():
    match = re.search(r'\.' + name + r'\s*=\s*(\d+)', stock)
    assert match and int(match[1]) == value, name
assert '.duty_max   = MOVE_DUTY' in stock
for name, value in dict(MOVE_DUTY=1280, SCAN_V_MIN=4000, SCAN_V_MAX=40000,
                        SCAN_STOP_MS=8, SCAN_RUNUP_COUNTS=300, SCAN_RUNOUT_COUNTS=240).items():
    assert re.search(r'#define\s+' + name + r'\s+' + str(value) + r'\b', main), name
for kind in ('sweep', 'drv'):
    assert f'struct servo_cfg {kind} = STOCK;' in main
    assert re.search(kind + r'\.stop_ms\s*=\s*SCAN_STOP_MS;', main)
headers = (BASE / 'src/emount.h').read_text()
assert re.search(r'#define\s+EM_FRAME_PERIOD_MAX\s+30u', headers)
assert re.search(r'#define\s+EM_FRAME_PERIOD_MIN\s+10u', headers)
assert re.search(r'#define\s+EM_FRAME_PERIOD_DEFAULT\s+17u', headers)
assert re.search(r'#define\s+EM_FOCAL_MM10\s+500u', headers)

L, T, I32 = 65536, 5952, 2**31-1
# Every modular 14-bit raw difference, including asymmetric half-turn +8192.
deltas = [r if r <= 8192 else r-16384 for r in range(16384)]
assert min(deltas) == -8191 and max(deltas) == 8192
checks = 0
for d in deltas:
    lower, upper = -L-d, L-d
    assert -I32 <= lower <= I32 and -I32 <= upper <= I32
    # Both endpoints and points immediately adjacent to every branch threshold.
    for g in {-L, L, 0, lower-1, lower, lower+1, upper-1, upper, upper+1}:
        if not -L <= g <= L:
            continue
        reject = g > upper or g < lower
        assert reject == (not -L <= g+d <= L)
        result = g if reject else g+d
        assert -L <= result <= L
        checks += 1

bounds = {
    'servo_target_abs': 2*L+T,
    'servo_error_abs': 3*L+T,
    'servo_error_times_1000': (3*L+T)*1000,
    'position_difference_times_1000': 2*L*1000,
    # These use |signed dt|>=1, deliberately also covering wrapped negative dt.
    'velocity_abs': 2*L*1000,
    'twice_velocity_abs': 4*L*1000,
    'velocity_error_abs': 40000+2*L*1000,
    'feedforward_numerator_abs': 26*80000,
    'feedforward_abs': 40000+26*80000,
    'duty_before_clamp_abs': (40000+26*80000)//40 + (40000+2*L*1000)//50 + 134+800,
    'predictor_fresh_abs': 2*L*256,
    'predictor_blend_delta_rounded_abs': 4*L*256+1,
    'predictor_frame_product_abs': 2*L*256*30,
    'scan_centred_hi': T+65535*4,
    'drive_speed_product': 32767*(40000-4000),
    'report_difference_abs': 2*L,
    'distance_product': 50*(50000+4500),
    'extension_product_rounded': T*4500+T//2,
}
assert all(0 <= n <= I32 for n in bounds.values())
wide = 32768*65535*4+L
assert wide < 2**63
# Exhaustively certify the scan/drive speed mapping from all operand magnitudes.
assert all(4000 <= 4000+n*36000//127 <= 40000 for n in range(128))
assert all(4000 <= 4000+n*36000//32767 <= 40000 for n in range(32768))
# blend rounds a midpoint toward fresh; it cannot leave the old/fresh interval.
def truncdiv(x, y):
    return (1 if (x >= 0) == (y >= 0) else -1)*(abs(x)//abs(y))
V = 2*L*256
for old in (-V, -V+1, -2048, -1, 0, 1, 2048, V-1, V):
    for fresh in (-V, -V+1, -2048, -1, 0, 1, 2048, V-1, V):
        d = fresh-old
        blended = old+truncdiv(d+(1 if d>=0 else -1), 2)
        assert min(old,fresh) <= blended <= max(old,fresh)
# Unsigned elapsed time wraps normally, preserving a small positive interval.
assert ((3-0xfffffffe) & 0xffffffff) == 5
print(json.dumps({'frozen_hashes_verified':len(m['sources']),
                  'tracker_threshold_cases':checks,
                  'raw_difference_residues':len(deltas),
                  'int32_absolute_bounds':bounds,
                  'int64_defocus_absolute_bound':wide,
                  'result':'PASS: proposed coordinate arithmetic contract'}, indent=2))
