#ifndef EM_SHUTDOWN_H
#define EM_SHUTDOWN_H
#include <stdint.h>
#define EM_SHUTDOWN_CAP 64u
/* First accepted request owns shutdown through physical reset. ISR writes
 * PENDING only after the complete immutable snapshot. Foreground transitions
 * PENDING -> ACTIVE -> OFF; no state permits a second writer. */
struct em_shutdown {
    uint8_t request[EM_SHUTDOWN_CAP];
    uint16_t length;
    volatile uint8_t state;
};
enum { EM_SD_IDLE, EM_SD_PENDING, EM_SD_ACTIVE, EM_SD_OFF };
uint8_t em_shutdown_accept(struct em_shutdown *, const uint8_t *, uint16_t);
uint8_t em_shutdown_begin(struct em_shutdown *);
#endif
