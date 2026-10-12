/* SPDX-License-Identifier: MIT */
#include "af_completion.h"
uint8_t ea9_af_completion_event(const struct ea9_af_state *s, uint8_t op,
                                uint8_t outcome, uint8_t stopped)
{
    if (s->shutdown || s->active) return 0;
    if (op == EM_OP_STOP || stopped) return EM_REC_STOP;
    if (ea9_af_faulted(s) || !ea9_af_outcome_completed(outcome)) return 0;
    if (op == EM_OP_SCAN) return EM_REC_SCAN;
    if (op == EM_OP_DRIVE) return EM_REC_DRIVE;
    if (op >= EM_OP_MOVE && op <= EM_OP_MOVE_DEFOCUS) return EM_REC_MOVE;
    return 0;
}
