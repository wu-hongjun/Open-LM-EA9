/* Camera-command translation and session fault policy, independent of I/O.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_AF_CONTROL_H
#define EA9_AF_CONTROL_H
#include <stdint.h>
#include "emount.h"
#include "servo.h"

struct ea9_af_state { uint8_t fault_reason, active, shutdown; };

/* Unsafe feedback/peripheral faults latch; bounded healthy termination does not. */
uint8_t ea9_af_outcome_completed(uint8_t outcome);
uint8_t ea9_af_outcome_arrived(uint8_t outcome);
uint8_t ea9_af_faulted(const struct ea9_af_state *state);
uint8_t ea9_af_note_result(struct ea9_af_state *state, uint8_t outcome);
/* Prevent nested servo ownership when the bus is pumped during a move. */
uint8_t ea9_af_begin_motion(struct ea9_af_state *state);
void ea9_af_end_motion(struct ea9_af_state *state);
void ea9_af_request_shutdown(struct ea9_af_state *state);

/* Returns 1 for a position target, 0 for a sentinel or non-position command.
 * All accepted targets are bounded to the advertised mechanical travel.
 * current_counts is a single sampled position, not a protocol position. */
uint8_t ea9_af_resolve_target(const struct em_focus_cmd *command,
                             int32_t current_counts, uint16_t focal_mm10,
                             uint16_t defocus_scale, int32_t *target_counts);
#endif
