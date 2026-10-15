"""Close homing readiness after sticky inhibition; private scratch only."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]

def apply(work):
    work = Path(work).resolve()
    assert work.is_relative_to(ROOT / 'artifacts/private')
    p = work / 'src/main.c'
    s = p.read_text()
    old = 'static uint8_t home_cancel_requested(void)\n{\n'
    assert s.count(old) == 1
    new = old + '''    /* A rejected encoder coordinate must never become a new home reference.
     * Inhibition is sticky until restart, so this attempt is terminal too. */
    if (motor_is_inhibited()) {
        g_next_pending = 0;
        g_home_state = HOME_FAILED;
        return 1;
    }
'''
    p.write_text(s.replace(old, new))
