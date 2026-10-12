/* AF 2.4 counterexamples: inherited mechanical simulation, not a measurement
 * of this owner's motor/lens and not an optical-focus model. No device access.
 * SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "factory_servo.h"
#include "factory_af.h"
#include "af_control.h"
#include "af_completion.h"
#include "io_guard.h"
#include "abs_encoder.h"

extern void sim_reset(void);
extern int sim_noise, sim_stop_lo, sim_stop_hi;
extern double sim_vel;
extern unsigned sim_clamp_n;
static void pump(int32_t position) { (void)position; }
int main(int argc, char **argv)
{
    assert(argc == 2);
    int32_t target = atoi(argv[1]);
    sim_reset(); sim_noise = 0; sim_stop_lo = 0; sim_stop_hi = 5952;
    abs_encoder_track_reset();
    /* The deployed 2.4 wrapper limits, independent of its pure PID math. */
    struct servo_cfg cfg = { .duty_max = 1280, .stall_ms = 300,
        .timeout_ms = 380, .total_ms = 5000, .pump = pump };
    struct servo_result result;
    factory_servo_move_to(target, &cfg, &result);
    struct ea9_af_state state = {0};
    uint8_t fault = ea9_af_note_result(&state, result.outcome);
    uint8_t event = ea9_af_completion_event(&state, EM_OP_MOVE, result.outcome, 0);
    uint8_t next = ea9_af_begin_motion(&state);
    if (target == 4) {
        assert(result.outcome == SERVO_STALL && result.end == 0);
        assert(result.duty_peak == 200 && result.ms >= 300);
        assert(fault && !event && !next && !ea9_io_faults());
    } else if (target == 5952) {
        assert(result.outcome == SERVO_TIMEOUT && result.end < target);
        assert(fault && !event && !next && !ea9_io_faults());
    } else assert(result.outcome == SERVO_OK && !fault && event == EM_REC_MOVE && next);
    /* Instruction-validated factory callback semantics retain a completion
     * on deadline and admit a fresh target; they have no wrapper fault latch. */
    struct ea9_factory_af stock;
    ea9_factory_init(&stock);
    ea9_factory_target(&stock, 5632, 192);
    uint8_t tick = 0;
    for (unsigned i = 0; i < 301; ++i) tick = ea9_factory_tick(&stock, 192);
    assert((tick & EA9_FACTORY_TICK_TIMEOUT) && stock.completed && !stock.enabled);
    ea9_factory_target(&stock, 4200, 192);
    assert(stock.enabled && stock.armed && !stock.completed);
    printf("target=%ld end=%ld outcome=%u ms=%u duty_peak=%u io_fault=%u session_fault=%u completion_event=%u next_motion_allowed=%u simulated_stop_contacts=%u simulated_end_velocity=%.3f\n",
        (long)target, (long)result.end, result.outcome, result.ms, result.duty_peak,
        ea9_io_faults(), state.fault_reason, event, next, sim_clamp_n, sim_vel);
    return 0;
}
