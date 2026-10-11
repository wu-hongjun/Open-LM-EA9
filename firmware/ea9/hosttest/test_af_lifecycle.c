#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define main ea9_firmware_entry
#include "../src/main.c"
#undef main
struct host_pm host_pm;
extern void sim_reset(void);
extern double sim_pos;
extern double sim_encoder_gain;
extern uint32_t host_millis;
extern void host_body_frame(const uint8_t *, uint16_t);
extern int sim_stop_lo, sim_stop_hi, sim_encoder_stuck, sim_noise, sim_released;
extern int16_t sim_current_duty(void);
extern void (*sim_read_hook)(void);
static int scenario, samples;
static void final_read_fault(void);
static struct servo_result *observed_result;
static void final_read_drift(void) {
    if (observed_result->outcome == SERVO_OK) { sim_pos += 100; sim_read_hook = NULL; }
}
void em_uart_disable(void) {}
void vdd_init(void) {}
uint16_t vdd_read_mv(void) { return 3150; }
void vdd_read_burst(uint16_t *lo, uint16_t *hi, uint16_t ms) {
    (void)ms; *lo = *hi = 3150;
    if (scenario == 1) ea9_io_trip(EA9_IO_ADC);
}
void vdd_track_reset(void) {}
void vdd_track_result(uint16_t *lo, uint16_t *hi) { *lo = *hi = 3150; }
void vdd_track_sample(void) {
    ++samples;
    if (scenario == 7 && samples > 4 && !sim_current_duty()) sim_pos += 20;
    if (samples == 4 && scenario == 6) sim_read_hook = final_read_fault;
    if (samples == 4 && scenario == 2) ea9_io_trip(EA9_IO_ENCODER);
    if (samples == 4 && scenario == 3) { park_to_infinity(); powerdown_signal(); }
    if (samples == 4 && scenario == 5) ea9_io_trip(EA9_IO_ADC);
    if (samples == 4 && scenario == 9) {
        uint8_t stop[23] = {0xF0, 23, 0, 1, 0, 4};
        stop[19] = EM_REC_STOP; stop[22] = 0x55;
        host_body_frame(stop, sizeof stop);
    }
    if (samples == 4 && scenario == 10) host_millis += 100;
}
static void final_read_fault(void) {
    if (!g_pred.active) { assert(!ea9_af_faulted(&g_af_state)); ea9_io_trip(EA9_IO_ENCODER); }
}
int main(int argc, char **argv) {
    assert(argc == 2); scenario = atoi(argv[1]); sim_reset(); sim_noise = 0;
    sim_stop_lo = 0; sim_stop_hi = 5952; sim_pos = 100;
    em_init();
    if (scenario == 4) { sim_stop_lo = -1000000; sim_pos = 20000; }
    if (scenario == 8) { sim_encoder_gain = -1; sim_pos = 1000; }
    if (scenario <= 4 || scenario == 7 || scenario == 8 || scenario == 9) {
        motor_home();
        if (!scenario) { assert(g_homed && !g_af_state.active && !ea9_af_faulted(&g_af_state)); }
        else if (scenario == 9) {
            assert(!g_homed && !g_af_state.active && !ea9_af_faulted(&g_af_state));
            assert(sim_current_duty() == 0 && sim_released && !g_next_pending);
            assert(g_reference.phase == EA9_HOME_CANCELLED);
            struct em_focus_cmd move = { .op = EM_OP_MOVE, .target = 4300 };
            focus_exec(&move); assert(sim_current_duty() == 0 && sim_released);
        }
        else {
            assert(!g_homed && !g_af_state.active && sim_current_duty() == 0 && sim_released);
            assert(g_af_state.shutdown || ea9_af_faulted(&g_af_state));
            motor_home(); assert(!g_homed && sim_current_duty() == 0 && sim_released);
        }
    } else if (scenario == 11) {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();
        uint32_t before = host_millis;
        assert(focus_run(0, FOCUS_EM06_LO, &UPSTREAM_PROFILE) == SERVO_OK);
        assert(host_millis - before >= 10 && samples >= 2 && !g_af_state.active);
    } else if (scenario == 12) {
        struct servo_result result = {.outcome = SERVO_TIMEOUT};
        observed_result = &result; sim_read_hook = final_read_drift;
        sim_pos = 0; abs_encoder_track_reset();
        servo_move_rel(400, &UPSTREAM_PROFILE, &result);
        assert(sim_read_hook == NULL && result.outcome == SERVO_STALL);
        assert(!ea9_af_completion_event(&g_af_state, EM_OP_MOVE, result.outcome, 0));
    } else {
        g_homed = 1; sim_pos = 0; abs_encoder_track_reset();

        uint8_t result = focus_run(400, focus_counts_to_em06(400), &UPSTREAM_PROFILE);
        assert(result == SERVO_IO_FAULT && ea9_af_faulted(&g_af_state));
        assert(!g_af_state.active && sim_current_duty() == 0 && sim_released);
        assert(focus_run(800, focus_counts_to_em06(800), &UPSTREAM_PROFILE) != SERVO_OK);
    }
    puts("actual main homing/focus/shutdown case passed"); return 0;
}
