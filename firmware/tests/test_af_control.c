/* Bounds and session-failure cases for the actual AF command module.
 * SPDX-License-Identifier: MIT */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "af_control.h"
#include "focus_map.h"
#include "focus_dist.h"

static int32_t resolve(uint8_t op, uint16_t target, int16_t delta,
                       int32_t current, uint16_t scale)
{
    struct em_focus_cmd c = {.op = op, .target = target, .delta = delta};
    int32_t out = -123;
    assert(ea9_af_resolve_target(&c, current, 500, scale, &out));
    assert(out >= 0 && out <= FOCUS_TRAVEL_COUNTS);
    return out;
}

int main(void)
{
    struct em_focus_cmd c = {.op = EM_OP_MOVE, .target = EM_NO_TARGET};
    int32_t out = -123;
    unsigned i;
    unsigned cases = 0;
    assert(!ea9_af_resolve_target(&c, 0, 500, 1, &out) && out == -123);
    for (i = 0; i <= UINT16_MAX; ++i) {
        if (i == EM_NO_TARGET) continue;
        int32_t p = resolve(EM_OP_MOVE, (uint16_t)i, 0, INT32_MAX, UINT16_MAX);
        if (i <= FOCUS_EM06_LO) assert(p == 0);
        else if (i >= FOCUS_EM06_HI) assert(p == FOCUS_TRAVEL_COUNTS);
        else assert(p == (int32_t)(i - FOCUS_EM06_LO) * 4);
        ++cases;
    }
    /* Wire-sized relative operands crossed with extreme feedback and scale.
     * No signed overflow may turn a request into travel in the wrong direction. */
    const int32_t currents[] = {INT32_MIN, -120, 0, 2976, 5952, 6072, INT32_MAX};
    const uint16_t scales[] = {0, 1, 255, UINT16_MAX};
    const int16_t deltas[] = {INT16_MIN, -32767, -1, 0, 1, 32766, INT16_MAX};
    unsigned a, b, d;
    for (a = 0; a < sizeof currents / sizeof currents[0]; ++a)
        for (b = 0; b < sizeof scales / sizeof scales[0]; ++b)
            for (d = 0; d < sizeof deltas / sizeof deltas[0]; ++d) {
                int64_t wide = (int64_t)currents[a] + (int64_t)deltas[d] * scales[b] * 4;
                int32_t p = resolve(EM_OP_MOVE_DEFOCUS, 0, deltas[d], currents[a], scales[b]);
                assert(p == (wide < 0 ? 0 : wide > 5952 ? 5952 : wide));
                (void)resolve(EM_OP_MOVE_REL, 0, deltas[d], currents[a], scales[b]);
                cases += 2;
            }
    assert(resolve(EM_OP_MOVE_REL, 0, 1, 2976, 0) == 2980);
    assert(resolve(EM_OP_MOVE_REL, 0, -1, 2976, 0) == 2972);
    assert(resolve(EM_OP_MOVE_DIST, FOCUS_DIST_INF, 0, 2976, 1) == 0);
    assert(resolve(EM_OP_MOVE_DIST, 384, 0, 0, 1) > 0); /* one metre, 50mm */
    for (i = EM_OP_STOP; i <= EM_OP_DRIVE; ++i) {
        c.op = i; out = -123;
        assert(!ea9_af_resolve_target(&c, 0, 500, 1, &out) && out == -123);
    }
    /* A camera Stop stays recoverable; mechanical faults cannot restart under
     * later Move, Stop, success, or shutdown/park admission. */
    for (i = SERVO_STALL; i <= SERVO_WRONG_WAY; ++i) {
        struct ea9_af_state state = {0};
        assert(!ea9_af_note_result(&state, SERVO_OK));
        assert(!ea9_af_note_result(&state, SERVO_ABORTED));
        assert(ea9_af_note_result(&state, i));
        assert(ea9_af_note_result(&state, SERVO_OK));
        assert(ea9_af_note_result(&state, SERVO_ABORTED));
        assert(state.fault_reason == i);
    }
    struct ea9_af_state state = {0};
    assert(ea9_af_note_result(&state, UINT8_MAX));
    assert(!ea9_af_begin_motion(&state));
    /* Shutdown can arrive in the protocol pump inside a servo or homing move.
     * Neither a recursive park nor a later command may reacquire the driver. */
    struct ea9_af_state moving = {0};
    assert(ea9_af_begin_motion(&moving));
    assert(!ea9_af_begin_motion(&moving));
    ea9_af_request_shutdown(&moving);
    assert(!ea9_af_note_result(&moving, SERVO_ABORTED));
    ea9_af_end_motion(&moving);
    assert(!ea9_af_begin_motion(&moving));
    struct ea9_af_state stopped = {0};
    assert(ea9_af_begin_motion(&stopped));
    ea9_af_end_motion(&stopped);
    assert(!ea9_af_note_result(&stopped, SERVO_ABORTED));
    assert(ea9_af_begin_motion(&stopped)); /* ordinary camera Stop can resume */
    printf("AF command/fault checks passed: %u bounded target cases, sentinel and sticky fault policy.\n", cases);
    return 0;
}
