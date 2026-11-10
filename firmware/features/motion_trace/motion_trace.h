#ifndef OLA_MOTION_TRACE_H
#define OLA_MOTION_TRACE_H

#include <stdint.h>

#define MT_ADDRESS 0x14000u
#define MT_BYTES 4096u
#define MT_SLOTS 2u
#define MT_PAGE 64u
#define MT_HOME_CAP 48u
#define MT_AF_CAP 192u

enum mt_kind {
    MT_HOME_PHASE = 1,
    MT_HOME_SAMPLE,
    MT_COMMAND,
    MT_LEG_START,
    MT_SERVO_SAMPLE,
    MT_RETARGET,
    MT_LEG_END,
    MT_LEG_SKIPPED,
};

enum mt_home_phase {
    MT_DRIVE_START = 1,
    MT_DRIVE_STILL,
    MT_DRIVE_CAP,
    MT_SETTLE_START,
    MT_SETTLE_STILL,
    MT_SETTLE_CAP,
    MT_ORIGIN,
};

void mt_home_phase(uint32_t ms, uint8_t phase, uint16_t raw, int32_t position);
/* Call before reading the sensor so sampling adds at most one SPI transaction
 * per interval. Samples are raw; phase markers also carry the tracked count. */
int mt_home_sample_due(uint32_t ms);
void mt_record(uint32_t ms, uint8_t kind, uint8_t detail, uint16_t aux,
               int32_t a, int32_t b);
void mt_servo_sample(uint32_t ms, int32_t pos, int32_t target, int16_t duty);

/* Called from the outer main loop after the shutdown signal. At most one
 * previously erased slot is used per boot. The header is programmed last. */
int mt_save(const uint8_t *area, int (*write_page)(unsigned, const uint8_t *));

#endif
