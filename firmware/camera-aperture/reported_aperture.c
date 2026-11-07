#include "reported_aperture.h"
#include "board.h"
#include "emount.h"
#include "emount_packets.h"

#define NO_REQUEST 0xffffu

static volatile uint16_t pending = NO_REQUEST;

static uint16_t word(const uint8_t *bytes)
{
    return (uint16_t)(bytes[0] | (uint16_t)bytes[1] << 8);
}

static void put_word(uint8_t *bytes, uint16_t value)
{
    bytes[0] = (uint8_t)value;
    bytes[1] = (uint8_t)(value >> 8);
}

void reported_aperture_offer(const uint8_t *frame, uint16_t available)
{
    if (available < 9u || available > 256u || frame[0] != 0xf0u) return;

    uint16_t length = word(frame + 1);
    if (length < 9u || length > available || frame[length - 1u] != 0x55u) return;

    uint16_t sum = 0;
    for (uint16_t i = 1; i < length - 3u; ++i) sum += frame[i];
    if (sum != word(frame + length - 3u)) return;

    uint16_t value;
    if (frame[3] == 2u && frame[5] == 1u && length >= 41u) {
        value = EM_APERTURE_NOW;
    } else if (frame[3] == 2u && frame[5] == 0x1bu && length >= 11u) {
        value = word(frame + 6);
    } else if (frame[3] == 1u && frame[5] == 3u && length >= 16u) {
        value = word(frame + 11);
    } else {
        return;
    }

    /* Camera thirds of a stop need their full fractional byte. */
    if (value >= EM_APERTURE_MAX && value <= EM_APERTURE_MIN) pending = value;
}

void reported_aperture_commit(void)
{
    uint32_t key = __get_PRIMASK();
    __disable_irq();
    uint16_t value = pending;
    pending = NO_REQUEST;
    if (value != NO_REQUEST) {
        put_word(em_msg_05 + 6, value);
        put_word(em_msg_05 + 8, value);
        put_word(em_msg_1B + 6, value);
        put_word(em_msg_1B + 8, value);
        uint16_t optional = em_m08_aperture_on ? value : 0u;
        put_word(em_msg_28 + 15, optional);
        put_word(em_msg_35 + 15, optional);
    }
    __set_PRIMASK(key);
}

void reported_aperture_init(void)
{
    pending = EM_APERTURE_NOW;
    reported_aperture_commit();
}
