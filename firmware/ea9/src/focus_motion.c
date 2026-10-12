#include "focus_motion.h"
#include "focus_map.h"
#include <string.h>

void focus_motion_reset(struct focus_motion *s) { memset(s, 0, sizeof(*s)); }

int8_t focus_motion_sample(struct focus_motion *s, int32_t counts,
                           uint32_t now, uint32_t frame, uint16_t period_ms)
{
    if (!s->initialized || (uint32_t)(now - s->sample_ms) > period_ms ||
        (uint32_t)(now - s->frame_ms) > 2u * period_ms ||
        (uint32_t)(frame - s->frame) > 1u ||
        (s->initialized && frame != s->frame && now == s->frame_ms)) {
        s->initialized = 1;
        s->frame_counts = counts;
        s->motion_counts = counts;
        s->sample_ms = s->window_ms = s->frame_ms = now;
        s->frame = s->window_frame = frame;
        s->known = s->moving = s->changed = 0;
        s->history_ready = 0;
        s->direction = 0;
        s->delta = 0;
        return -1;
    }
    s->sample_ms = now;
    int32_t displacement = counts - s->motion_counts;
    if (displacement >= FOCUS_COUNTS_PER_UNIT || displacement <= -FOCUS_COUNTS_PER_UNIT) {
        s->direction = displacement > 0 ? 1 : -1;
        s->motion_counts = counts;
        s->known = s->moving = s->changed = 1;
    }
    if (frame != s->window_frame && (uint32_t)(now - s->window_ms) >= period_ms) {
        s->known = 1;
        s->moving = s->changed;
        if (!s->moving) s->direction = 0;
        s->changed = 0;
        s->window_ms = now;
        s->window_frame = frame;
    }
    if (frame == s->frame) return 0;
    uint8_t history_ready = s->history_ready;
    s->delta = history_ready ? (int16_t)((counts - s->frame_counts) / FOCUS_COUNTS_PER_UNIT) : 0;
    s->frame_counts = counts;
    s->frame = frame;
    s->frame_ms = now;
    s->history_ready = 1;
    return history_ready ? 1 : 0;
}
