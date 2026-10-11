#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "io_guard.h"
#include "motor.h"
Port test_port;
SysTick_Type test_systick;
static uint32_t irq;
uint32_t test_irq_state(void) { return irq; }
void test_irq_disable(void) { irq = 1; }
void test_irq_restore(uint32_t state) { irq = state; }
int main(int argc, char **argv) {
    assert(argc == 2); motor_attach_pins(); delay_init();
    if (!strcmp(argv[1], "us")) delay_us(100); else delay_ms(50);
    assert(ea9_io_faults() == EA9_IO_TIMEBASE);
    assert(!test_port.Group[0].PINCFG[8].bit.PMUXEN);
    assert(!test_port.Group[0].PINCFG[9].bit.PMUXEN);
    assert(!test_port.Group[0].PINCFG[18].bit.PMUXEN);
    assert(!test_port.Group[0].PINCFG[19].bit.PMUXEN);
    puts("actual delay with frozen SysTick released motor and returned"); return 0;
}
