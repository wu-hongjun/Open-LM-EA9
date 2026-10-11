/* Counterexamples derived from REA, exercised against the candidate policies.
 * This is not a factory emulator or a physical calibration. SPDX-License-Identifier: MIT */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "af_reference.h"
#include "af_completion.h"
#include "af_timing.h"
#include "focus_map.h"
#include "io_guard.h"

static void mapping(void)
{
    assert(FOCUS_FACTORY_ORIGIN == 4096 && FOCUS_REFERENCE_OFFSET == 192);
    assert(focus_counts_to_reference(0) == 192);
    assert(focus_counts_to_reference(5952) == 6144);
    for (unsigned wire = 0; wire <= UINT16_MAX; ++wire) {
        int32_t expected = wire <= 4144 ? 0 : wire >= 5632 ? 5952 : (wire - 4144) * 4;
        assert(focus_em06_to_counts(wire) == expected);
    }
    for (int32_t count = 0; count <= 5952; ++count) {
        assert(focus_reference_to_counts(focus_counts_to_reference(count)) == count);
        assert(focus_counts_to_em06(count) == 4144 + count / 4);
    }
    assert(focus_counts_to_reference(INT_MIN) == 192);
    assert(focus_counts_to_reference(INT_MAX) == 6144);
    assert(focus_reference_to_counts(INT_MIN) == 0);
    assert(focus_reference_to_counts(INT_MAX) == 5952);
    /* Factory s16 arithmetic can wrap here; the candidate bounds the request. */
    assert(focus_em06_to_counts(12288) == 5952);
}

static void reference(void)
{
    struct ea9_home h = {0};
    assert(ea9_home_sample(&h, 0, 100) == EA9_HOME_UNKNOWN);
    ea9_home_begin(&h, 1000, 0);
    assert(ea9_home_sample(&h, 500, 20) == EA9_HOME_DRIVING);
    assert(ea9_home_sample(&h, 500, 59) == EA9_HOME_DRIVING);
    assert(ea9_home_sample(&h, 500, 60) == EA9_HOME_SETTLING);
    assert(ea9_home_sample(&h, 500, 99) == EA9_HOME_SETTLING);
    assert(ea9_home_sample(&h, 500, 100) == EA9_HOME_READY);
    assert(h.outcome == SERVO_OK);
    ea9_home_cancel(&h); assert(h.phase == EA9_HOME_READY);

    ea9_home_begin(&h, 0, 0);
    assert(ea9_home_sample(&h, 121, 1) == EA9_HOME_FAILED && h.outcome == SERVO_WRONG_WAY);
    ea9_home_begin(&h, 0, 0);
    assert(ea9_home_sample(&h, -6073, 1) == EA9_HOME_FAILED && h.outcome == SERVO_RUNAWAY);
    ea9_home_begin(&h, INT_MIN, 0);
    assert(ea9_home_sample(&h, INT_MAX, 1) == EA9_HOME_FAILED && h.outcome == SERVO_WRONG_WAY);
    ea9_home_begin(&h, INT_MAX, 0);
    assert(ea9_home_sample(&h, INT_MIN, 1) == EA9_HOME_FAILED && h.outcome == SERVO_RUNAWAY);

    /* Deadline wins even if the sample also looks stationary. */
    ea9_home_begin(&h, 1000, 0);
    assert(ea9_home_sample(&h, 1000, 300) == EA9_HOME_FAILED && h.outcome == SERVO_TIMEOUT);
    ea9_home_begin(&h, 1000, 0);
    assert(ea9_home_sample(&h, 1000, 40) == EA9_HOME_SETTLING);
    assert(ea9_home_sample(&h, 1000, 540) == EA9_HOME_FAILED && h.outcome == SERVO_TIMEOUT);
    ea9_home_begin(&h, 1000, 0);
    assert(ea9_home_sample(&h, 1000, 40) == EA9_HOME_SETTLING);
    assert(ea9_home_sample(&h, 1121, 41) == EA9_HOME_FAILED && h.outcome == SERVO_RUNAWAY);

    /* Small continuing drift must accumulate, rather than resetting a baseline
     * on every sample and being mistaken for stationary encoder noise. */
    ea9_home_begin(&h, 1000, 0);
    for (int32_t t = 1; t < 300; ++t)
        assert(ea9_home_sample(&h, 1000 - t, t) == EA9_HOME_DRIVING);
    assert(ea9_home_sample(&h, 700, 300) == EA9_HOME_FAILED);
    ea9_home_begin(&h, 1000, UINT32_MAX - 19);
    assert(ea9_home_sample(&h, 1000, 20) == EA9_HOME_SETTLING);
    assert(ea9_home_sample(&h, 1000, 60) == EA9_HOME_READY);
    ea9_home_begin(&h, 0, 0);
    h.samples = EA9_MOTION_POLL_LIMIT - 1;
    assert(ea9_home_sample(&h, 0, 0) == EA9_HOME_FAILED && h.outcome == SERVO_IO_FAULT);
    ea9_home_begin(&h, 0, 0); ea9_home_cancel(&h);
    assert(h.phase == EA9_HOME_CANCELLED && h.outcome == SERVO_ABORTED);
    assert(ea9_home_sample(&h, 0, 80) == EA9_HOME_CANCELLED);
}

static void completion(void)
{
    struct ea9_af_state s = {0};
    for (uint8_t op = EM_OP_MOVE; op <= EM_OP_MOVE_DEFOCUS; ++op)
        assert(ea9_af_completion_event(&s, op, SERVO_OK, 0) == EM_REC_MOVE);
    assert(ea9_af_completion_event(&s, EM_OP_SCAN, SERVO_OK, 0) == EM_REC_SCAN);
    assert(ea9_af_completion_event(&s, EM_OP_DRIVE, SERVO_OK, 0) == EM_REC_DRIVE);
    const uint8_t failures[] = {SERVO_TIMEOUT, SERVO_STALL, SERVO_WRONG_WAY, SERVO_RUNAWAY, SERVO_IO_FAULT, SERVO_ABORTED};
    for (unsigned i = 0; i < sizeof failures; ++i) {
        assert(!ea9_af_completion_event(&s, EM_OP_MOVE, failures[i], 0));
        assert(!ea9_af_completion_event(&s, EM_OP_SCAN, failures[i], 0));
        assert(!ea9_af_completion_event(&s, EM_OP_DRIVE, failures[i], 0));
    }
    assert(ea9_af_completion_event(&s, EM_OP_MOVE, SERVO_ABORTED, 1) == EM_REC_STOP);
    ea9_af_note_result(&s, SERVO_TIMEOUT);
    assert(!ea9_af_completion_event(&s, EM_OP_MOVE, SERVO_OK, 0));
    assert(ea9_af_completion_event(&s, EM_OP_STOP, SERVO_ABORTED, 1) == EM_REC_STOP);
    s.active = 1; assert(!ea9_af_completion_event(&s, EM_OP_STOP, SERVO_ABORTED, 1));
    s.active = 0; s.shutdown = 1;
    assert(!ea9_af_completion_event(&s, EM_OP_STOP, SERVO_ABORTED, 1));
}

int main(void)
{
    mapping(); reference(); completion();
    assert(ea9_af_elapsed(5, UINT32_MAX - 4) == 10);
    assert(EA9_AF_CONTROL_STEP_MS == 5 && EA9_AF_MAX_CONTROL_GAP_MS == 40);
    assert(EA9_STOCK_OVERFLOW_US_NUM * EA9_STOCK_PID_DIVIDER == 660088);
    assert(EA9_STOCK_OVERFLOW_US_NUM * EA9_STOCK_TIMEOUT_CALLBACKS == 18062408);
    puts("AF origin, reference, timing and completion counterexamples passed");
}
