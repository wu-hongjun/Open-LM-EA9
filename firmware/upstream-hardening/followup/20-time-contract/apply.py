"""Independent time proposals; root owns integration and image/version decisions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

def _source(build, name):
    build = Path(build).resolve()
    private = ROOT / 'artifacts/private'
    assert build.is_relative_to(private) and build != private, 'private scratch only'
    assert build not in [private / 'bounded34a', private / 'bounded34b'], 'frozen inputs'
    path = build / 'src' / name
    assert path.resolve().is_relative_to(build / 'src'), 'source must remain in scratch'
    return path

def home(build):
    path = _source(build, 'main.c')
    s = path.read_text()
    old = '&& home_still_for(&still, HOME_STILL_MS)) {'
    assert s.count(old) == 2
    for cap in ['HOME_MS', 'HOME_SETTLE_MS']:
        s = s.replace(old, '&& home_still_for(&still, HOME_STILL_MS)\n'
                      '\t\t    && (uint32_t)(millis() - t0) < ' + cap + ') {', 1)
    path.write_text(s)

def predictor(build):
    path = _source(build, 'focus_pred.c')
    s = path.read_text()
    old = '((pos - p->last_pos) * 256) / (int32_t)dt'
    assert s.count(old) == 1
    # Under the admitted coordinate contract the numerator is <= 33554432.
    # For dt > INT32_MAX its exact signed/positive quotient is therefore zero.
    s = s.replace(old, '(dt > INT32_MAX ? 0 : ((pos - p->last_pos) * 256) / (int32_t)dt)')
    path.write_text(s)
