#include "motion_trace.h"
#include "profile_bank.h"
#include <string.h>

struct mt_event {
    uint32_t ms;
    uint8_t kind, detail;
    uint16_t aux;
    int32_t a, b;
};

typedef char event_size_must_be_16[sizeof(struct mt_event) == 16 ? 1 : -1];
typedef char trace_must_fit[MT_PAGE + (MT_HOME_CAP + MT_AF_CAP) *
                            sizeof(struct mt_event) <= MT_BYTES ? 1 : -1];

static struct mt_event home[MT_HOME_CAP], af[MT_AF_CAP];
static uint32_t af_total, next_home_sample, last_servo_sample;
static unsigned home_count, af_head;
static int8_t last_sign;
static uint8_t servo_sampled, save_attempted;

void mt_record(uint32_t ms, uint8_t kind, uint8_t detail, uint16_t aux,
               int32_t a, int32_t b)
{
    struct mt_event event = {ms, kind, detail, aux, a, b};

    if (kind == MT_HOME_PHASE || kind == MT_HOME_SAMPLE) {
        if (home_count < MT_HOME_CAP) home[home_count++] = event;
        return;
    }
    if (kind == MT_LEG_START) {
        servo_sampled = 0;
        last_sign = 0;
    }
    af[af_head++] = event;
    if (af_head == MT_AF_CAP) af_head = 0;
    af_total++;
}

void mt_home_phase(uint32_t ms, uint8_t phase, uint16_t raw, int32_t position)
{
    next_home_sample = ms + 20u;
    mt_record(ms, MT_HOME_PHASE, phase, raw, position, 0);
}

int mt_home_sample_due(uint32_t ms)
{
    if ((int32_t)(ms - next_home_sample) < 0) return 0;
    next_home_sample = ms + 20u;
    return 1;
}

void mt_servo_sample(uint32_t ms, int32_t pos, int32_t target, int16_t duty)
{
    int8_t sign = (duty > 0) - (duty < 0);
    int reversal = sign && last_sign && sign != last_sign;

    if (sign) last_sign = sign;
    if (servo_sampled && !reversal && ms - last_servo_sample < 20u) return;
    servo_sampled = 1;
    last_servo_sample = ms;
    mt_record(ms, MT_SERVO_SAMPLE, reversal, (uint16_t)duty, pos, target);
}

static void put32(uint8_t *dst, uint32_t value)
{
    for (unsigned i = 0; i < 4; ++i) dst[i] = (uint8_t)(value >> (i * 8));
}

static int write_events(const uint8_t *area, int (*write_page)(unsigned, const uint8_t *),
                        unsigned offset, const struct mt_event *events, unsigned bytes)
{
    const uint8_t *src = (const uint8_t *)events;
    uint8_t page[MT_PAGE];

    for (unsigned i = 0; i < bytes; i += MT_PAGE) {
        unsigned used = bytes - i < MT_PAGE ? bytes - i : MT_PAGE;

        memset(page, 0xff, sizeof(page));
        memcpy(page, src + i, used);
        if (write_page(offset + i, page) || memcmp(area + offset + i, page, MT_PAGE)) return 0;
    }
    return 1;
}

static int blank(const uint8_t *slot)
{
    for (unsigned i = 0; i < MT_BYTES; ++i) {
        if (slot[i] != 0xff) return 0;
    }
    return 1;
}

int mt_save(const uint8_t *area, int (*write_page)(unsigned, const uint8_t *))
{
    uint8_t header[MT_PAGE] = {'O','L','A','M','O','T','1','!'};
    unsigned af_count = af_total < MT_AF_CAP ? af_total : MT_AF_CAP;
    unsigned home_bytes = home_count * sizeof(*home);
    unsigned af_bytes = af_count * sizeof(*af);
    unsigned offset = 0;

    if (save_attempted || !home_count) return 0;
    save_attempted = 1;
    while (offset < MT_BYTES * MT_SLOTS && !blank(area + offset)) offset += MT_BYTES;
    if (offset == MT_BYTES * MT_SLOTS) return 0;
    if (!write_events(area, write_page, offset + MT_PAGE, home, home_bytes) ||
        !write_events(area, write_page, offset + MT_PAGE + sizeof(home), af, af_bytes)) return 0;

    put32(header + 8, home_count);
    put32(header + 12, af_count);
    put32(header + 16, af_total);
    put32(header + 20, pb_crc32((const uint8_t *)home, home_bytes));
    put32(header + 24, pb_crc32((const uint8_t *)af, af_bytes));
    put32(header + 60, pb_crc32(header, 60));
    return !write_page(offset, header) && !memcmp(area + offset, header, MT_PAGE);
}
