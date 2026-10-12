/* Production wrapper with scripted sensor/clock responses, not a physics or
 * optical focus model. Each scenario is a fresh process with fresh globals. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "factory_servo.h"
#include "factory_af.h"
#include "io_guard.h"
#include "focus_map.h"

static const char *scenario;
static uint64_t ticks, begun, first_drive;
static int16_t duty;
static int powered, aborted, retargeted, released, calls, pumps;
static uint16_t peak;
static int32_t last_position;

uint32_t millis(void) { return (uint32_t)(ticks / 48000u); }
uint32_t clock_cycles(void) {
    if (strcmp(scenario, "frozen")) ticks += 5000u;
    if (!strcmp(scenario, "gap") && powered && !aborted) { ticks += 12u * 60008u; aborted = 1; }
    return (uint32_t)ticks;
}
void motor_emergency_release(void) { duty = 0; released = 1; }
void motor_release(void) { motor_emergency_release(); }
void motor_brake(void) { duty = 0; released = 0; }
void motor_drive(int16_t d) {
    assert(!ea9_io_faults()); duty = d; ++calls;
    uint16_t magnitude = d < 0 ? -d : d;
    if (magnitude > peak) peak = magnitude;
    assert(magnitude <= 800);
    if (d && !powered) { powered = 1; first_drive = ticks; }
}
int32_t abs_encoder_track(void) {
    int32_t position = 0;
    if (!strcmp(scenario, "invalid-positive")) return INT32_MAX;
    if (!strcmp(scenario, "invalid-negative")) return INT32_MIN;
    if (powered && (!strcmp(scenario, "success") || !strcmp(scenario, "wrap") ||
                    !strcmp(scenario, "stop-cross") || !strcmp(scenario, "late-stop") ||
                    !strcmp(scenario, "final-invalid") || !strcmp(scenario, "final-drift") || !strcmp(scenario, "late-fault") ||
                    !strcmp(scenario, "retarget") || !strcmp(scenario, "progress-timeout") ||
                    !strcmp(scenario, "deadline-stop"))) {
        int32_t time = (int32_t)((ticks - first_drive) / 48000u);
        position = time * ((!strcmp(scenario, "progress-timeout") || !strcmp(scenario, "deadline-stop")) ? 1 : 4);
        if (retargeted) position = 160 - (time - 40) * 4;
    }
    if (!strcmp(scenario, "mid-invalid") && powered) return INT32_MAX;
    if (!strcmp(scenario, "final-invalid") && powered && !duty) return INT32_MIN;
    if (!strcmp(scenario, "runaway") || !strcmp(scenario, "runaway-stop")) position = powered ? 1100 : 0;
    if (!strcmp(scenario, "wrong-way") || !strcmp(scenario, "wrong-way-stop")) position = powered ? 850 : 1000;
    if (!strcmp(scenario, "final-drift") && powered && !duty && position >= 400) position += 1000;
    if (!strcmp(scenario, "late-fault") && powered && !duty && position >= 400) ea9_io_trip(EA9_IO_ENCODER);
    last_position = position;
    return position;
}
static void pump(int32_t position) {
    assert(position >= -120 && position <= 6072);
    ++pumps;
    if (!strcmp(scenario, "resolution-stop")) aborted = 1;
    if (!strcmp(scenario, "deadline-stop") && powered && !duty) aborted = 1;
    if ((!strcmp(scenario, "runaway-stop") || !strcmp(scenario, "wrong-way-stop")) && powered) aborted = 1;
    if (!strcmp(scenario, "early-fault") && pumps == 2) ea9_io_trip(EA9_IO_ENCODER);
    if (!strcmp(scenario, "stop") && powered) aborted = 1;
    if (!strcmp(scenario, "stop-cross") && position >= 400) aborted = 1;
    if (!strcmp(scenario, "late-stop") && position >= 400 && !duty) aborted = 1;
}
static uint8_t abort_motion(void) { return !strcmp(scenario, "gap") ? 0 : aborted; }
static uint8_t retarget(int32_t *target) {
    if (!strcmp(scenario, "retarget-limit-stop") && powered) {
        if (!retargeted) { *target = 500; retargeted = 1; return 1; }
        aborted = 1; return 0;
    }
    if (!strcmp(scenario, "retarget") && powered && !retargeted && (ticks-first_drive)/48000u >= 40) {
        *target = 80; retargeted = 1; return 1;
    }
    return 0;
}
int main(int argc, char **argv) {
    assert(argc == 2); scenario = argv[1];
    if (!strcmp(scenario, "wrap")) ticks = UINT32_MAX - 50000u;
    begun = ticks;
    struct servo_cfg cfg = { .duty_max = 800, .stall_ms = 600, .timeout_ms = 380,
        .total_ms = 5000, .pump = pump, .abort = abort_motion,
        .retarget = retarget, .retarget_max = 16 };
    if (!strcmp(scenario, "dry")) cfg.dry = 1;
    if (!strcmp(scenario, "stall")) cfg.stall_ms = 100;
    if (!strcmp(scenario, "retarget-limit-stop")) cfg.retarget_max = 1;
    struct servo_result result;
    int32_t target = !strncmp(scenario, "wrong-way", 9) ? 1400 : 400;
    if (!strncmp(scenario, "resolution", 10)) target = 4;
    factory_servo_move_to(target, &cfg, &result);
    if (!strcmp(scenario, "success") || !strcmp(scenario, "wrap") || !strcmp(scenario, "retarget")) {
        assert(result.outcome == SERVO_OK && powered && !duty && !ea9_io_faults());
        assert(first_drive - begun >= 11u * 60008u);
        assert(first_drive - begun < 11u * 60008u + 10000u);
        if (retargeted) assert(result.retargets == 1 && result.target == 80 && last_position <= 80);
        else assert(last_position >= 400 && result.target == 400);
    } else if (!strcmp(scenario, "resolution")) {
        assert(result.outcome == SERVO_RESOLUTION && !powered && !peak && result.end == 0);
    } else if (!strcmp(scenario, "progress-timeout")) {
        assert(result.outcome == SERVO_DEADLINE && result.end > 8 && result.end < 400 && !duty && !ea9_io_faults());
    } else if (!strcmp(scenario, "retarget-limit-stop") || !strcmp(scenario, "resolution-stop") || !strcmp(scenario, "deadline-stop") || !strcmp(scenario, "stop") || !strcmp(scenario, "stop-cross") || !strcmp(scenario, "late-stop")) {
        assert(result.outcome == SERVO_ABORTED && !duty && released);
    } else if (!strcmp(scenario, "mid-invalid") || !strcmp(scenario, "final-invalid") || !strcmp(scenario, "early-fault") || !strcmp(scenario, "late-fault") || !strcmp(scenario, "gap") || !strcmp(scenario, "frozen") || !strcmp(scenario, "invalid-positive") || !strcmp(scenario, "invalid-negative")) {
        assert(result.outcome == SERVO_IO_FAULT && !duty && released && ea9_io_faults());
    } else if (!strcmp(scenario, "runaway") || !strcmp(scenario, "runaway-stop") || !strcmp(scenario, "final-drift")) {
        assert(result.outcome == SERVO_RUNAWAY && !duty && released);
    } else if (!strcmp(scenario, "wrong-way") || !strcmp(scenario, "wrong-way-stop")) {
        assert(result.outcome == SERVO_WRONG_WAY && !duty && released);
    } else if (!strcmp(scenario, "stall")) {
        assert(result.outcome == SERVO_STALL && result.ms <= 102 && !duty && released);
    } else if (!strcmp(scenario, "timeout") || !strcmp(scenario, "dry")) {
        assert(result.outcome == SERVO_TIMEOUT && result.ms >= 375 && result.ms <= 377 && !duty);
        if (cfg.dry) assert(calls == 0);
    } else return 2;
    assert(peak <= 800);
    printf("factory wrapper %s: passed (outcome=%u, ms=%u)\n", scenario, result.outcome, result.ms);
    return 0;
}
