/* The pure factory law is instruction-tested separately. This wrapper owns
 * coordinates, foreground scheduling, command cancellation and fault limits.
 * It is a candidate, not a reproduction of factory interrupt/peripheral timing.
 * SPDX-License-Identifier: MIT */
#include "factory_servo.h"
#include "factory_af.h"
#include "focus_map.h"
#include "abs_encoder.h"
#include "motor.h"
#include "delay.h"
#include "io_guard.h"
#include <string.h>

static struct ea9_factory_af controller;
static uint32_t callback_at;
static uint8_t initialized;

/* No fabricated burst of PID steps after a delayed bus/sensor transaction.
 * At most 10 callback periods may be coalesced, allowing one control step.
 * Longer gaps latch a timebase fault and release drive. */
static uint8_t sample(int32_t position)
{
    uint32_t now = clock_cycles();
    if (!initialized) {
        ea9_factory_init(&controller);
        controller.previous_position = position + FOCUS_REFERENCE_OFFSET;
        callback_at = now;
        initialized = 1;
        return 0;
    }
    uint32_t elapsed = now - callback_at;
    uint32_t count = elapsed / EA9_FACTORY_CALLBACK_CYCLES;
    if (count >= EA9_FACTORY_CONTROL_DIVIDER) {
        /* Idle may pause for startup/park work; disabled history can be
         * rebased without driving. Active PID cannot recover missed samples. */
        if (controller.enabled) { ea9_io_trip(EA9_IO_TIMEBASE); return 0; }
        controller.previous_position = position + FOCUS_REFERENCE_OFFSET;
        controller.divider = (controller.divider + count % EA9_FACTORY_CONTROL_DIVIDER) % EA9_FACTORY_CONTROL_DIVIDER;
        callback_at += count * EA9_FACTORY_CALLBACK_CYCLES;
        return 0;
    }
    uint8_t result = 0;
    for (uint32_t i = 0; i < count; ++i)
        result |= ea9_factory_tick(&controller, position + FOCUS_REFERENCE_OFFSET);
    callback_at += count * EA9_FACTORY_CALLBACK_CYCLES;
    return result;
}
void factory_servo_sample_idle(int32_t position)
{
    /* Validate before adding the reference offset, including the first idle
     * sample. An invalid tracker value must not become signed C overflow. */
    if (position < -120 || position > FOCUS_TRAVEL_COUNTS + 120) {
        ea9_io_trip(EA9_IO_ENCODER);
        return;
    }
    if (!controller.enabled && !ea9_io_faults()) (void)sample(position);
}
static int32_t admitted_target(int32_t target)
{
    if (target < 0) return 0;
    if (target > FOCUS_TRAVEL_COUNTS) return FOCUS_TRAVEL_COUNTS;
    return target;
}
void factory_servo_move_to(int32_t target, const struct servo_cfg *cfg,
                           struct servo_result *out)
{
    memset(out, 0, sizeof(*out));
    out->outcome = SERVO_ABORTED;
    uint32_t started = millis(), leg_at = started, polls = 0;
    int32_t pos = abs_encoder_track();
    int32_t leg_start = pos, desired = admitted_target(target);
    out->start = out->end = pos;
    /* Coordinates admitted by the protocol have four-count resolution. */
    out->target = focus_em06_to_counts(focus_counts_to_em06(desired));
    if (ea9_io_faults()) goto fault;
    factory_servo_sample_idle(pos);
    if (ea9_io_faults()) goto fault;
    ea9_factory_target(&controller, focus_counts_to_em06(desired), pos + FOCUS_REFERENCE_OFFSET);
    int32_t sign = out->target > pos ? 1 : out->target < pos ? -1 : 0;
    int32_t moved_at = pos;
    uint32_t last_motion = started;
    for (;;) {
        pos = abs_encoder_track();
        out->end = pos;
        if (ea9_io_faults()) goto fault;
        /* Admit feedback before telemetry and retarget origin arithmetic. */
        if (pos < -120 || pos > FOCUS_TRAVEL_COUNTS + 120) {
            ea9_io_trip(EA9_IO_ENCODER); goto fault;
        }
        if (cfg->pump) cfg->pump(pos);
        if (ea9_io_faults()) goto fault;
        /* Retarget precedes completion. Stop/Scan/Drive set the caller's
         * abort latch through this hook; none can become a stale success. */
        int32_t next;
        if (cfg->retarget && cfg->retarget(&next)) {
            int32_t next_desired = admitted_target(next);
            int32_t next_target = focus_em06_to_counts(focus_counts_to_em06(next_desired));
            /* Retransmitting the same admitted wire target is not a new leg.
             * Consume it without resetting PID/deadline or spending budget.
             * Relative commands are resolved by the caller before this test. */
            if (next_target != out->target) {
                /* Keep polling Stop/replacement even after the budget. */
                if (out->retargets >= cfg->retarget_max) {
                    out->outcome = SERVO_TIMEOUT; break;
                }
                desired = next_desired;
                out->target = next_target;
                ea9_factory_target(&controller, focus_counts_to_em06(desired), pos + FOCUS_REFERENCE_OFFSET);
                sign = out->target > pos ? 1 : out->target < pos ? -1 : 0;
                leg_start = moved_at = pos;
                leg_at = last_motion = millis();
                ++out->retargets;
            }
        }
        if (cfg->abort && cfg->abort()) { out->outcome = SERVO_ABORTED; break; }
        uint32_t now = millis();
        if (++polls >= EA9_MOTION_POLL_LIMIT) { ea9_io_trip(EA9_IO_TIMEBASE); goto fault; }
        if (cfg->total_ms && (uint32_t)(now - started) >= cfg->total_ms) { out->outcome = SERVO_TIMEOUT; break; }
        /* Do not copy factory signed wrapping into an out-of-range mechanism. */
        if ((sign > 0 && pos > out->target + 600) || (sign < 0 && pos < out->target - 600)) {
            out->outcome = SERVO_RUNAWAY; break;
        }
        if ((sign > 0 && pos < leg_start - 120) || (sign < 0 && pos > leg_start + 120)) {
            out->outcome = SERVO_WRONG_WAY; break;
        }
        int32_t movement = pos - moved_at;
        if (movement > 8 || movement < -8) { moved_at = pos; last_motion = now; }
        if ((uint32_t)(now - last_motion) >= cfg->stall_ms && sign) { out->outcome = SERVO_STALL; break; }
        uint8_t tick = sample(pos);
        if (ea9_io_faults()) goto fault;
        /* A whole leg no larger than the wire's four-count resolution ends
         * without energizing a coil. Report the measured position, not target.
         * This is not a wider arrival band for ordinary moving corrections. */
        if (sign && out->target >= leg_start - FOCUS_COUNTS_PER_UNIT &&
            out->target <= leg_start + FOCUS_COUNTS_PER_UNIT &&
            pos >= out->target - FOCUS_COUNTS_PER_UNIT &&
            pos <= out->target + FOCUS_COUNTS_PER_UNIT) {
            out->outcome = SERVO_RESOLUTION; break;
        }
        if ((tick & EA9_FACTORY_TICK_TIMEOUT) || (uint32_t)(now - leg_at) >= cfg->timeout_ms) {
            /* Factory reports actuator completion on its deadline. Retain
             * that eligibility only with real, direction-consistent progress.
             * No-progress, I/O, runaway and wrong-way guards remain sticky. */
            out->outcome = (sign > 0 ? pos > leg_start + 8 :
                           sign < 0 ? pos < leg_start - 8 : 0)
                          ? SERVO_DEADLINE : SERVO_TIMEOUT;
            break;
        }
        /* Factory completion means target crossing, not optical focus lock.
         * The wrapper brakes at completion instead of keeping PID armed
         * until a later protocol stage as stock does. */
        if (ea9_factory_complete(&controller, pos + FOCUS_REFERENCE_OFFSET)) {
            out->outcome = SERVO_OK; break;
        }
        if (tick & EA9_FACTORY_TICK_CONTROL) {
            int32_t duty = controller.duty;
            if (duty > cfg->duty_max) duty = cfg->duty_max;
            if (duty < -(int32_t)cfg->duty_max) duty = -(int32_t)cfg->duty_max;
            uint16_t magnitude = (uint16_t)(duty < 0 ? -duty : duty);
            if (magnitude > out->duty_peak) out->duty_peak = magnitude;
            if (!out->duty_first && (pos > out->start + 8 || pos < out->start - 8)) out->duty_first = magnitude;
            if (!cfg->dry) motor_drive((int16_t)duty);
        }
    }
    ea9_factory_stop(&controller);
    if (!cfg->dry) {
        if (out->outcome == SERVO_OK || out->outcome == SERVO_RESOLUTION ||
            out->outcome == SERVO_DEADLINE) { motor_drive(0); motor_brake(); }
        else motor_release();
    }
    out->end = abs_encoder_track();
    if (ea9_io_faults()) goto fault;
    if (out->end < -120 || out->end > FOCUS_TRAVEL_COUNTS + 120) {
        ea9_io_trip(EA9_IO_ENCODER); goto fault;
    }
    if (cfg->pump) cfg->pump(out->end);
    if (ea9_io_faults()) goto fault;
    if ((sign > 0 && out->end > out->target + 600) || (sign < 0 && out->end < out->target - 600)) {
        out->outcome = SERVO_RUNAWAY;
        motor_release();
    }
    if ((sign > 0 && out->end < leg_start - 120) ||
        (sign < 0 && out->end > leg_start + 120)) {
        out->outcome = SERVO_WRONG_WAY;
        motor_release();
    }
    /* A final sample can invalidate a previously admissible termination. */
    if ((out->outcome == SERVO_RESOLUTION &&
         (out->end < out->target - FOCUS_COUNTS_PER_UNIT ||
          out->end > out->target + FOCUS_COUNTS_PER_UNIT)) ||
        (out->outcome == SERVO_DEADLINE &&
         (sign > 0 ? out->end <= leg_start + 8 : out->end >= leg_start - 8))) {
        out->outcome = SERVO_TIMEOUT;
        motor_release();
    }
    /* A Stop/shutdown received on the final report still cancels completion. */
    if (cfg->abort && cfg->abort()) {
        /* Stop cancels completion, but must not erase an observed hard fault. */
        if (out->outcome == SERVO_OK || out->outcome == SERVO_RESOLUTION ||
            out->outcome == SERVO_DEADLINE) out->outcome = SERVO_ABORTED;
        motor_release();
    }
    out->ms = (uint16_t)(millis() - started);
    return;
fault:
    ea9_factory_stop(&controller);
    out->outcome = SERVO_IO_FAULT;
    motor_emergency_release();
    out->ms = (uint16_t)(millis() - started);
}
void servo_move_rel(int32_t delta, const struct servo_cfg *cfg, struct servo_result *out)
{
    int64_t target = (int64_t)abs_encoder_track() + delta;
    factory_servo_move_to(target < 0 ? 0 : target > FOCUS_TRAVEL_COUNTS ? FOCUS_TRAVEL_COUNTS : (int32_t)target, cfg, out);
}
