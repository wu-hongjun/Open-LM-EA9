/* SPDX-License-Identifier: MIT */
#include "af_control.h"
#include "focus_map.h"
#include "focus_dist.h"

uint8_t ea9_af_faulted(const struct ea9_af_state *state)
{
    return state->fault_reason != 0;
}

uint8_t ea9_af_note_result(struct ea9_af_state *state, uint8_t outcome)
{
    if (!state->fault_reason && !ea9_af_outcome_completed(outcome) && outcome != SERVO_ABORTED)
        state->fault_reason = outcome;
    return ea9_af_faulted(state);
}

uint8_t ea9_af_outcome_arrived(uint8_t outcome)
{
    return outcome == SERVO_OK || outcome == SERVO_RESOLUTION;
}
uint8_t ea9_af_outcome_completed(uint8_t outcome)
{
    return ea9_af_outcome_arrived(outcome) || outcome == SERVO_DEADLINE;
}

uint8_t ea9_af_begin_motion(struct ea9_af_state *state)
{
    if (state->active || state->shutdown || ea9_af_faulted(state)) return 0;
    state->active = 1;
    return 1;
}

void ea9_af_end_motion(struct ea9_af_state *state) { state->active = 0; }
void ea9_af_request_shutdown(struct ea9_af_state *state) { state->shutdown = 1; }

uint8_t ea9_af_resolve_target(const struct em_focus_cmd *c, int32_t current,
                             uint16_t focal, uint16_t scale, int32_t *out)
{
    int64_t target;
    switch (c->op) {
    case EM_OP_MOVE:
        if (c->target == EM_NO_TARGET) return 0;
        target = focus_em06_to_counts(c->target);
        break;
    case EM_OP_MOVE_DIST:
        target = focus_counts_for_code(c->target, focal);
        break;
    case EM_OP_MOVE_REL:
        target = (int64_t)current + (int64_t)c->delta * FOCUS_COUNTS_PER_UNIT;
        break;
    case EM_OP_MOVE_DEFOCUS:
        /* Widen before multiplication: the wire operands can exceed int32. */
        target = (int64_t)current + (int64_t)c->delta * scale * FOCUS_COUNTS_PER_UNIT;
        break;
    default:
        return 0;
    }
    if (target < 0) target = 0;
    if (target > FOCUS_TRAVEL_COUNTS) target = FOCUS_TRAVEL_COUNTS;
    *out = (int32_t)target;
    return 1;
}
