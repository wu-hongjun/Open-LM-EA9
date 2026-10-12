#include "io_guard.h"
#include "motor.h"
#include "board.h"
static volatile uint8_t faults;
uint8_t ea9_io_faults(void) { return faults; }
void ea9_io_trip(uint8_t reason)
{
    uint32_t irq_state = __get_PRIMASK();
    __disable_irq();
    faults |= reason;
    __set_PRIMASK(irq_state);
    /* GPIO-only: works even before TCC initialization or with SYNCBUSY stuck. */
    motor_emergency_release();
}
uint8_t ea9_io_wait_pending(struct ea9_io_wait *wait, uint8_t reason)
{
    return ea9_io_wait_pending_mask(wait, reason, 0xffu);
}
uint8_t ea9_io_wait_pending_mask(struct ea9_io_wait *wait, uint8_t reason, uint8_t blockers)
{
    if (faults & blockers) return 0;
    if (++wait->polls >= EA9_IO_POLL_LIMIT ||
        (uint32_t)(millis() - wait->start) >= EA9_IO_DEADLINE_MS) {
        ea9_io_trip(reason);
        return 0;
    }
    return 1;
}
uint8_t ea9_io_startup_pending(uint32_t *polls, uint8_t reason)
{
    if (faults) return 0;
    if (++*polls >= EA9_IO_POLL_LIMIT) { ea9_io_trip(reason); return 0; }
    return 1;
}
