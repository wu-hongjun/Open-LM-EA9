/* Semantics recovered at 0x8dd4/8d20/8bfc/8fc8/8d94/8e28/8a2c. See
 * docs/reverse-engineering/factory-af-baseline.md for evidence and deviations.
 * SPDX-License-Identifier: MIT */
#include "factory_af.h"
#include <limits.h>
#include <string.h>

static int32_t signed32(uint32_t value)
{
    return value <= INT32_MAX ? (int32_t)value : -1 - (int32_t)(UINT32_MAX - value);
}
static int32_t signed16(uint32_t value)
{
    value &= 0xffffu;
    return value < 0x8000u ? (int32_t)value : (int32_t)value - 65536;
}
void ea9_factory_init(struct ea9_factory_af *s) { memset(s, 0, sizeof(*s)); }
void ea9_factory_target(struct ea9_factory_af *s, uint16_t protocol, int32_t position)
{
    s->target = signed16(((uint32_t)signed16(protocol) - 4096u) * 4u);
    s->direction = position < s->target ? 1 : position > s->target ? 2 : 3;
    s->armed = s->enabled = 1;
    s->timeout = 0;
    s->completed = 0;
    /* History, accumulator, previous sample and callback divider survive. */
}
void ea9_factory_stop(struct ea9_factory_af *s)
{
    s->armed = s->enabled = 0;
    s->completed = 1;
}
int32_t ea9_factory_speed(uint8_t direction, int32_t error)
{
    if (direction == 1) {
        if (error > 600) return 250;
        if (error > 300) return 100;
        if (error > 100) return 50;
        return error / 2;
    }
    if (direction == 2) {
        if (error < -600) return -250;
        if (error < -300) return -100;
        if (error < -100) return -50;
        return error / 2;
    }
    return 0;
}
int32_t ea9_factory_pid(struct ea9_factory_af *s, int32_t error)
{
    /* ARM's 32-bit overflow is intentional here. Signed C overflow is not. */
    uint32_t e = (uint32_t)error, old = s->previous_error, old2 = s->previous_error2;
    s->accumulator += 500u * (e - old) + 150u * e + 300u * (e - 2u * old + old2);
    s->previous_error2 = old;
    s->previous_error = e;
    int32_t result = signed32(s->accumulator) / 200;
    if (result > 0 && result < 200) result = 200;
    if (result < 0 && result > -200) result = -200;
    if (result > EA9_FACTORY_DUTY_LIMIT) result = EA9_FACTORY_DUTY_LIMIT;
    if (result < -EA9_FACTORY_DUTY_LIMIT) result = -EA9_FACTORY_DUTY_LIMIT;
    return result;
}
int32_t ea9_factory_control(struct ea9_factory_af *s, int32_t position)
{
    int32_t pos = signed16((uint32_t)position);
    s->velocity = signed16((uint32_t)pos - (uint32_t)s->previous_position);
    s->previous_position = pos;
    if (s->enabled) {
        int32_t error = signed16((uint32_t)s->target - (uint32_t)pos);
        s->duty = ea9_factory_pid(s, ea9_factory_speed(s->direction, error) - s->velocity);
    }
    return s->duty;
}
uint8_t ea9_factory_complete(const struct ea9_factory_af *s, int32_t position)
{
    if (s->completed) return s->completed;
    if (s->direction == 1) return position >= s->target;
    if (s->direction == 2) return position <= s->target;
    return 1;
}
uint8_t ea9_factory_tick(struct ea9_factory_af *s, int32_t position)
{
    uint8_t result = 0;
    if (s->armed) {
        if (s->timeout == EA9_FACTORY_TIMEOUT_COUNT) {
            ea9_factory_stop(s);
            result |= EA9_FACTORY_TICK_TIMEOUT;
        } else ++s->timeout;
    }
    if (s->divider == EA9_FACTORY_CONTROL_DIVIDER - 1u) {
        s->divider = 0;
        uint8_t enabled = s->enabled;
        ea9_factory_control(s, position);
        if (enabled) result |= EA9_FACTORY_TICK_CONTROL;
    } else ++s->divider;
    return result;
}
