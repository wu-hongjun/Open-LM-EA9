/* Measured motion, independent of command completion and target prediction.
 * SPDX-License-Identifier: MIT */
#ifndef FOCUS_MOTION_H
#define FOCUS_MOTION_H
#include <stdint.h>

struct focus_motion {
    int32_t frame_counts, motion_counts;
    uint32_t sample_ms, window_ms, frame_ms, frame, window_frame;
    int16_t delta;
    int8_t direction; /* -1/0/+1: measured encoder polarity, not optical polarity */
    uint8_t initialized, changed, known, moving, history_ready;
};

/* Reset only when the tracker reference/session changes, never at Move/Stop. */
void focus_motion_reset(struct focus_motion *s);

/* Caller admits fresh tracker counts in [-120, travel+120] and a negotiated
 * 10..30 ms frame period. Movement requires four counts from the retained
 * motion anchor; quiet frames never discard slow cumulative displacement.
 * History preserves signed (current-previous-frame counts)/4, truncating toward
 * zero. Neither rule is measured noise calibration. Rest requires a whole
 * period and a new VD with no observed displacement of one resolution unit.
 * A sample gap >one period, frame gap >one edge, or no VD for >two periods
 * rebases as unknown. Unsigned clock/frame subtraction tolerates wrap.
 * Return +1 for one genuine per-frame history delta, 0 for no new entry,
 * -1 to discard pre-gap/reference history. The first changed VD after a
 * rebase seeds a history baseline, rather than emitting a partial interval.
 * Unknown is separate from rest. */
int8_t focus_motion_sample(struct focus_motion *s, int32_t counts,
                           uint32_t now, uint32_t frame, uint16_t period_ms);
#endif
