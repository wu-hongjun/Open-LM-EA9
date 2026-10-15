"""Partial arithmetic proposal; apply only to a fresh private 3.3 source copy."""
from pathlib import Path
import hashlib
PINS = {'main.c':'b82a84de828fa3dd776e32f557d8bb299b46086a8a96c415c69f90c587c9fad7', 'servo.c':'e86738affa837d9c10fa3988670d377b0b0de5e222851e619a4c20b206078e08'}
def apply(work):
    work=Path(work).resolve()
    root=Path(__file__).resolve().parents[4]
    assert work.is_relative_to(root/'artifacts/private'), 'private scratch required'
    src = work / 'src'
    texts = {}
    for name, pin in PINS.items():
        p = src / name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == pin, name
        texts[name] = p.read_text()
    s = texts['main.c']
    start = s.index('static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)\n{')
    end = s.index('\n/* The servo', start)
    f = s[start:end]
    f = f.replace('int32_t here;', 'int32_t here;\n\tint64_t wide;')
    f = f.replace('*out = here + (int32_t)c->delta * FOCUS_COUNTS_PER_UNIT;', 'wide = (int64_t)here + (int64_t)c->delta * FOCUS_COUNTS_PER_UNIT;')
    f = f.replace('*out = here + (int32_t)c->delta * (int32_t)em_defocus_scale()', 'wide = (int64_t)here + (int64_t)c->delta * em_defocus_scale()')
    f = f.replace('if (*out < 0)', 'if (wide < 0)').replace('else if (*out > FOCUS_TRAVEL_COUNTS)', 'else if (wide > FOCUS_TRAVEL_COUNTS)')
    f = f.replace('\treturn 1;\n}', '\telse {\n\t\t*out = (int32_t)wide;\n\t}\n\treturn 1;\n}')
    texts['main.c'] = s[:start]+f+s[end:]
    s = texts['servo.c']
    old = '\t\t\tint32_t err = aim - pos;'
    assert s.count(old)==1
    s = s.replace(old, '\t\t\tint64_t err = (int64_t)aim - pos;\n\t\t\tint64_t profile;')
    old = '\t\t\tv_target = clamp32(err * 1000 / (int32_t)cfg->stop_ms,\n\t\t\t                   -cfg->v_cruise, cfg->v_cruise);'
    assert s.count(old)==1
    s = s.replace(old, '\t\t\tprofile = err * 1000 / cfg->stop_ms;\n\t\t\tv_target = profile < -cfg->v_cruise ? -cfg->v_cruise\n\t\t\t           : profile > cfg->v_cruise ? cfg->v_cruise\n\t\t\t           : (int32_t)profile;')
    texts['servo.c'] = s
    for name,s in texts.items(): (src/name).write_text(s)
