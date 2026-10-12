/* Independently implemented stock 1.8 motion semantics. No peripheral access.
 * SPDX-License-Identifier: MIT */
#ifndef EA9_FACTORY_AF_H
#define EA9_FACTORY_AF_H
#include <stdint.h>

/* These constants come from the recovered 1.8.0 application, not tuning on
 * the owner's lens. One callback is (7500+1)*8 cycles at nominal 48 MHz. */
#define EA9_FACTORY_CALLBACK_CYCLES 60008u
#define EA9_FACTORY_CONTROL_DIVIDER 11u
#define EA9_FACTORY_TIMEOUT_COUNT 300u
#define EA9_FACTORY_DUTY_LIMIT 1280

struct ea9_factory_af {
    uint32_t accumulator, previous_error, previous_error2;
    int32_t target, previous_position, velocity, duty;
    uint16_t timeout;
    uint8_t direction, enabled, armed, completed, divider;
};
enum { EA9_FACTORY_TICK_CONTROL = 1, EA9_FACTORY_TICK_TIMEOUT = 2 };

void ea9_factory_init(struct ea9_factory_af *state);
void ea9_factory_target(struct ea9_factory_af *state, uint16_t protocol,
                        int32_t relative_position);
void ea9_factory_stop(struct ea9_factory_af *state);
int32_t ea9_factory_speed(uint8_t direction, int32_t error);
int32_t ea9_factory_pid(struct ea9_factory_af *state, int32_t error);
int32_t ea9_factory_control(struct ea9_factory_af *state, int32_t position);
uint8_t ea9_factory_complete(const struct ea9_factory_af *state, int32_t position);
uint8_t ea9_factory_tick(struct ea9_factory_af *state, int32_t position);
#endif
