/* AF-only sticky peripheral faults. A deadline plus a poll ceiling also
 * terminates waits if SysTick stops. The ceiling is not a calibrated time. */
#ifndef EA9_IO_GUARD_H
#define EA9_IO_GUARD_H
#include <stdint.h>
#include "delay.h"
enum { EA9_IO_ENCODER = 1, EA9_IO_ADC = 2, EA9_IO_PWM = 4, EA9_IO_TIMEBASE = 8,
       EA9_IO_UART = 16, EA9_IO_CLOCK = 32, EA9_IO_EIC = 64 };
/* Motion stays inhibited by every fault. A healthy camera link and its timing
 * must remain serviceable when only feedback/ADC/PWM has failed. */
#define EA9_IO_TIMING_FAULTS (EA9_IO_CLOCK | EA9_IO_TIMEBASE)
#define EA9_IO_LINK_FAULTS (EA9_IO_TIMING_FAULTS | EA9_IO_UART | EA9_IO_EIC)
#define EA9_IO_DEADLINE_MS 2u
#define EA9_IO_POLL_LIMIT 100000u
#define EA9_MOTION_POLL_LIMIT 1000000u
struct ea9_io_wait { uint32_t start, polls; };
uint8_t ea9_io_faults(void);
void ea9_io_trip(uint8_t reason);
uint8_t ea9_io_wait_pending(struct ea9_io_wait *wait, uint8_t reason);
uint8_t ea9_io_wait_pending_mask(struct ea9_io_wait *wait, uint8_t reason, uint8_t blockers);
uint8_t ea9_io_startup_pending(uint32_t *polls, uint8_t reason);
/* Before SysTick configuration there is no elapsed-time authority. Bound these
 * waits only by the finite poll ceiling, without claiming a millisecond rate. */
#define EA9_IO_WAIT_STARTUP(ready, reason) ({ \
    uint32_t polls_ = 0; \
    uint8_t ok_ = !ea9_io_faults(); \
    while (ok_ && !(ready)) ok_ = ea9_io_startup_pending(&polls_, (reason)); \
    ok_; })
/* Evaluate the actual volatile register each time, with no callback overhead. */
#define EA9_IO_WAIT_MASK(ready, reason, blockers) ({ \
    struct ea9_io_wait wait_ = { millis(), 0 }; \
    uint8_t ok_ = !(ea9_io_faults() & (blockers)); \
    while (ok_ && !(ready)) ok_ = ea9_io_wait_pending_mask(&wait_, (reason), (blockers)); \
    ok_; })
#define EA9_IO_WAIT(ready, reason) EA9_IO_WAIT_MASK(ready, reason, 0xffu)
#endif
