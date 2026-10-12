/* Event eligibility stays independent of servo tuning and wire serialization.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_AF_COMPLETION_H
#define EA9_AF_COMPLETION_H
#include "af_control.h"
/* Zero means no event. Stop is acknowledged even without a usable reference;
 * Move/Scan/Drive events denote actuator termination, not optical lock or exact
 * target arrival. Healthy bounded deadline/resolution results are eligible. */
uint8_t ea9_af_completion_event(const struct ea9_af_state *state, uint8_t operation,
                                uint8_t outcome, uint8_t stopped_by_camera);
#endif
