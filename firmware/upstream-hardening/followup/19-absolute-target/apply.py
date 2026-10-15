#!/usr/bin/env python3
"""Private-source proposal: preserve resolved targets using the caller's sample."""
from pathlib import Path
import argparse

def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

def apply(src):
    src = src.resolve()
    root = Path(__file__).resolve().parents[4]
    assert src.is_relative_to(root / 'artifacts/private'), src
    assert src.name == 'src' and src.is_dir(), src
    p = src / 'servo.c'
    text = p.read_text()
    text = replace_once(text, '''void servo_move_rel(int32_t delta, const struct servo_cfg *cfg,
                    struct servo_result *out)
{
	uint32_t polls = 0;
	int32_t  start  = abs_encoder_track();
	int32_t  target = start + delta;''', '''void servo_move_from(int32_t start, int32_t target,
                     const struct servo_cfg *cfg, struct servo_result *out)
{
	uint32_t polls = 0;''')
    text = replace_once(text, '(delta >= 0) ? 1 : -1', '(target >= start) ? 1 : -1')
    text += '''
/* Preserve the relative API for callers that have not resolved a target. */
void servo_move_rel(int32_t delta, const struct servo_cfg *cfg,
                    struct servo_result *out)
{
	int32_t start = abs_encoder_track();
	servo_move_from(start, start + delta, cfg, out);
}
'''
    p.write_text(text)
    p = src / 'servo.h'
    p.write_text(replace_once(p.read_text(), 'void servo_move_rel(int32_t delta_counts,', '''/* Use a caller-owned admitted position sample and an absolute target in the
 * same coordinate system. The caller must keep both in the controller's
 * supported arithmetic domain. Feedback is read again before any drive. */
void servo_move_from(int32_t start, int32_t target,
                     const struct servo_cfg *cfg, struct servo_result *out);

void servo_move_rel(int32_t delta_counts,'''))
    p = src / 'main.c'
    text = p.read_text()
    text = replace_once(text, '''	/* The predictor's target is the COMMANDED position, not the servo's
	 * internal start+delta -- they differ by whatever the encoder moved
	 * between the two reads, and the field the body sees should be bounded
	 * by what it asked for. */''', '''	/* Keep the resolved destination and starting sample shared by the
	 * predictor and servo. A later feedback read must not shift the target. */''')
    text = replace_once(text, 'servo_move_rel(delta, cfg, &r);', 'servo_move_from(here, want, cfg, &r);')
    # The diagnostic-only park call has the same absolute-zero intent.
    text = replace_once(text, 'servo_move_rel(-here, &PARK, &r);', 'servo_move_from(here, 0, &PARK, &r);')
    p.write_text(text)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    a = p.parse_args()
    apply(a.source)
