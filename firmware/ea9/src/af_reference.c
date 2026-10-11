/* SPDX-License-Identifier: MIT */
#include "af_reference.h"
#include "focus_map.h"
#include "io_guard.h"
#include "servo.h"

void ea9_home_begin(struct ea9_home *h, int32_t sample, uint32_t now)
{
    *h = (struct ea9_home){ .phase = EA9_HOME_DRIVING, .phase_at = now,
        .last_motion_at = now, .start = sample, .still_at = sample };
}
static enum ea9_home_phase fail(struct ea9_home *h, uint8_t outcome)
{
    h->outcome = outcome;
    return h->phase = EA9_HOME_FAILED;
}
enum ea9_home_phase ea9_home_sample(struct ea9_home *h, int32_t sample, uint32_t now)
{
    if (h->phase != EA9_HOME_DRIVING && h->phase != EA9_HOME_SETTLING) return h->phase;
    if (++h->samples >= EA9_MOTION_POLL_LIMIT) return fail(h, SERVO_IO_FAULT);
    uint32_t elapsed = now - h->phase_at;
    if (elapsed >= (h->phase == EA9_HOME_DRIVING ? EA9_HOME_DRIVE_CAP_MS : EA9_HOME_SETTLE_CAP_MS))
        return fail(h, SERVO_TIMEOUT);
    int64_t distance = (int64_t)sample - h->start;
    if (h->phase == EA9_HOME_DRIVING) {
        if (distance > EA9_HOME_WRONG_WAY_COUNTS) return fail(h, SERVO_WRONG_WAY);
        if (distance < -(FOCUS_TRAVEL_COUNTS + EA9_HOME_WRONG_WAY_COUNTS)) return fail(h, SERVO_RUNAWAY);
    } else if (distance > EA9_HOME_SETTLE_LIMIT_COUNTS || distance < -EA9_HOME_SETTLE_LIMIT_COUNTS)
        return fail(h, SERVO_RUNAWAY);
    int64_t movement = (int64_t)sample - h->still_at;
    if (movement > EA9_HOME_NOISE_COUNTS || movement < -EA9_HOME_NOISE_COUNTS) {
        h->still_at = sample;
        h->last_motion_at = now;
    }
    uint32_t minimum = h->phase == EA9_HOME_DRIVING ? EA9_HOME_MIN_DRIVE_MS : EA9_HOME_MIN_SETTLE_MS;
    if (elapsed >= minimum && (uint32_t)(now - h->last_motion_at) >= EA9_HOME_STILL_MS) {
        if (h->phase == EA9_HOME_DRIVING) {
            h->phase = EA9_HOME_SETTLING;
            h->phase_at = h->last_motion_at = now;
            h->start = h->still_at = sample;
        } else {
            h->phase = EA9_HOME_READY;
            h->outcome = SERVO_OK;
        }
    }
    return h->phase;
}
void ea9_home_cancel(struct ea9_home *h)
{
    if (h->phase == EA9_HOME_DRIVING || h->phase == EA9_HOME_SETTLING) {
        h->phase = EA9_HOME_CANCELLED;
        h->outcome = SERVO_ABORTED;
    }
}
