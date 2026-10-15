#!/usr/bin/env python3
"""Offline time-contract probes against pinned 3.4 production bodies/modules."""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path
from apply import home, predictor
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
src = ROOT / 'artifacts/private/bounded34b'
out = a.output.resolve()
assert out.is_relative_to(ROOT / 'artifacts/private')
out.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((src / 'manifest.json').read_text())
assert sha(src / 'manifest.json') == '8e358720a959a79a4636e1a9310fc23c08af9fa50539396d6946be6194c25a9a'
for name, digest in manifest['sources'].items():
    assert sha(src / name) == digest, name
guards = []
for fn in [home, predictor]:
    for denied in [ROOT, ROOT / 'firmware/candidates/3.4.0', src, ROOT / 'artifacts/private']:
        try:
            fn(denied)
        except AssertionError as e:
            guards.append(dict(applicator=fn.__name__, path=str(denied), rejected=str(e)))
        else:
            raise AssertionError('applicator did not reject protected path')

def function(s, name):
    start = s.index(name + '\n{')
    start = s.rfind('\n', 0, start) + 1
    end = s.index('\n}', start) + 2
    return s[start:end] + '\n'

cases = ['home-normal', 'home-wrap', 'home-freeze', 'home-drive-pump-cap',
         'home-settle-pump-cap', 'home-drive-read-cap', 'home-settle-read-cap',
         'home-drive-pump-before', 'home-settle-pump-before',
         'home-drive-read-before', 'home-settle-read-before',
         'home-drive-read-over', 'home-settle-read-over',
         'home-wrap-drive-pump-cap', 'home-wrap-settle-pump-cap',
         'home-drive-pump-over', 'home-settle-pump-over',
         'servo-wrap', 'servo-freeze', 'servo-freeze-driven', 'servo-gap-half', 'servo-gap-max',
         'servo-full-wrap-alias', 'predictor-zero', 'predictor-boundaries']
rows = []
for variant in ['frozen', 'proposal']:
    work = out / variant
    shutil.copytree(src / 'src', work / 'src')
    shutil.copytree(src / 'tools', work / 'tools')
    if variant == 'proposal':
        home(work)
        predictor(work)
    s = (work / 'src/main.c').read_text()
    constants = '\n'.join(re.findall(r'^#define (?:HOME_(?:DUTY|MS|MIN_MS|SETTLE_MS|SETTLE_MIN_MS|STILL_MS|STILL_COUNTS|POLL_LIMIT)|FOCUS_DEADBAND_COUNTS|MOVE_DUTY)\s+.*$', s, re.M)) + '\n'
    stock = s[s.index('static const struct servo_cfg STOCK = {'):]
    stock = stock[:stock.index('\n};') + 4]
    (work / 'config.inc').write_text(constants + stock)
    body = ''
    for name in ['static void focus_report_at(int32_t counts)',
                 'static void focus_answer_queries(void)',
                 'static void focus_report(void)',
                 'static void pump(int32_t pos)',
                 'static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)',
                 'static uint8_t focus_invalid(void)',
                 'static uint8_t focus_abort(void)',
                 'static uint8_t focus_retarget(int32_t *target)',
                 'static uint8_t focus_run(int32_t want, uint16_t target_u,\n                         const struct servo_cfg *cfg)',
                 'static void home_cutoff(void)', 'static uint8_t home_command(void)',
                 'static uint8_t home_cancel_requested(void)']:
        body += function(s, name)
    body = body.replace('if (tag == EM_REC_Q_POS2D)', 'compute_hook();\n        if (tag == EM_REC_Q_POS2D)')
    begin = s.index('struct home_still {')
    body += s[begin:s.index('\n};', begin) + 3] + '\n'
    for name in ['static void home_still_init(struct home_still *st)',
                 'static uint8_t home_still_for(struct home_still *st, uint32_t ms)',
                 'static void motor_home(void)']:
        body += function(s, name)
    (work / 'main.inc').write_text(body)
    encoder = (work / 'src/abs_encoder.c').read_text()
    tracker = '#define ENC_COUNTS 16384\n'
    tracker += function(encoder, 'void abs_encoder_track_reset(void)').replace('g_track      = 0;', 'resets++;\n\tg_track      = 0;')
    tracker += function(encoder, 'int32_t abs_encoder_track(void)')
    (work / 'tracker.inc').write_text(tracker)
    (work / 'servo.c').write_text((work / 'src/servo.c').read_text())
    trace = (ROOT / 'firmware/upstream-diagnostic/tests/trace_host.c').read_text()
    trace = trace.replace('uint32_t st_lock(void) { return 0; }', '').replace('void st_unlock(uint32_t k) { (void)k; }', '')
    (work / 'trace.c').write_text(trace)
    flags = ['clang', '-std=gnu99', '-O1', '-Wall', '-Wextra', '-Werror', '-DST_HOST', '-DEA9_NO_LOG',
             '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
             '-I' + str(work), '-I' + str(work / 'tools/hosttest'), '-I' + str(work / 'src')]
    exe = work / 'probe'
    cmd = [*flags, HERE / 'test_time.c', work / 'tools/hosttest/shim.c', work / 'trace.c', work / 'servo.c',
           *[work / 'src' / (n + '.c') for n in ['emount', 'emount_packets', 'em_frame', 'em_owner', 'em_shutdown', 'startup_trace', 'focus_map', 'focus_dist', 'focus_pred']], '-o', exe]
    r = subprocess.run(list(map(str, cmd)), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for case in cases:
        r = subprocess.run([str(exe), case, variant], capture_output=True, text=True, timeout=20)
        assert r.returncode == 0, (variant, case, r.stdout, r.stderr)
        rows.append(dict(variant=variant, case=case, stdout=r.stdout.strip()))
    if variant == 'frozen':
        for case in ['home-drive-pump-cap', 'home-settle-pump-cap', 'home-drive-read-cap', 'home-settle-read-cap', 'home-drive-pump-over', 'home-settle-pump-over', 'home-drive-read-over', 'home-settle-read-over', 'home-wrap-drive-pump-cap', 'home-wrap-settle-pump-cap', 'servo-gap-max', 'predictor-boundaries']:
            r = subprocess.run([str(exe), case, 'proposal'], capture_output=True, text=True, timeout=20)
            assert r.returncode != 0 and 'Assertion' in r.stderr, (case, r.returncode, r.stdout, r.stderr)
            rows.append(dict(variant='frozen', case=case, negativeControl=True, exitCode=r.returncode, stdout=r.stdout.strip(), stderr=r.stderr.strip()))
for name, digest in manifest['sources'].items():
    assert sha(src / name) == digest, name
result = dict(source=str(src), sourceHashes=manifest['sources'], checks=len(rows), results=rows,
              pathGuards=guards,
              hardwareAccess=False, wallClockMeasured=False,
              inputs={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ['.py', '.c']})
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(rows, indent=2))
