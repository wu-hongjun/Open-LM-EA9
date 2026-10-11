/* AF-only sticky peripheral faults. A deadline plus a poll ceiling also
 * terminates waits if SysTick stops. The ceiling is not a calibrated time. */
#ifndef EA9_IO_GUARD_H
#define EA9_IO_GUARD_H
#include <stdint.h>
#include "delay.h"
enum { EA9_IO_ENCODER = 1, EA9_IO_ADC = 2, EA9_IO_PWM = 4, EA9_IO_TIMEBASE = 8, EA9_IO_UART = 16 };
#define EA9_IO_DEADLINE_MS 2u
#define EA9_IO_POLL_LIMIT 100000u
#define EA9_MOTION_POLL_LIMIT 1000000u
struct ea9_io_wait { uint32_t start, polls; };
uint8_t ea9_io_faults(void);
void ea9_io_trip(uint8_t reason);
uint8_t ea9_io_wait_pending(struct ea9_io_wait *wait, uint8_t reason);
/* Evaluate the actual volatile register each time, with no callback overhead. */
#define EA9_IO_WAIT(ready, reason) ({ \
    struct ea9_io_wait wait_ = { millis(), 0 }; \
    uint8_t ok_ = !ea9_io_faults(); \
    while (ok_ && !(ready)) ok_ = ea9_io_wait_pending(&wait_, (reason)); \
    ok_; })
#endif
