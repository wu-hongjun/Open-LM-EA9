/* Stock-derived law behind a bounded hardware motion owner.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_FACTORY_SERVO_H
#define EA9_FACTORY_SERVO_H
#include "servo.h"
void factory_servo_sample_idle(int32_t mechanical_position);
void factory_servo_move_to(int32_t target, const struct servo_cfg *cfg,
                           struct servo_result *out);
#endif
