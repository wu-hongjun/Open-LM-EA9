#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "io_guard.h"
#include "motor.h"
Port test_port;
SysTick_Type test_systick;
SCB_Type test_scb;
void SysTick_Handler(void);
static uint32_t irq;
uint32_t test_irq_state(void) { return irq; }
void test_irq_disable(void) { irq = 1; }
void test_irq_restore(uint32_t state) { irq = state; }
int main(int argc, char **argv) {
    assert(argc == 2); motor_attach_pins(); delay_init();
    if (!strcmp(argv[1], "cycles")) {
        /* Real implementation: phase, pending rollover, wrap and IRQ mask.
         * Hardware register rollover racing the snapshot is not simulated. */
        test_systick.VAL = 47999;
        assert(clock_cycles() == 0 && irq == 0);
        test_systick.VAL = 23999;
        assert(clock_cycles() == 24000);
        SysTick_Handler();
        assert(clock_cycles() == 72000);
        test_scb.ICSR = SCB_ICSR_PENDSTSET_Msk;
        irq = 1;
        assert(clock_cycles() == 120000 && irq == 1);
        test_scb.ICSR = 0;
        for (unsigned i = 1; i < 100000; ++i) SysTick_Handler();
        assert(clock_cycles() == (uint32_t)(100000ull * 48000u + 24000u));
        assert(irq == 1 && !ea9_io_faults());
        puts("actual SysTick snapshot phase/pending/wrap/IRQ preservation passed");
        return 0;
    }
    if (!strcmp(argv[1], "us")) delay_us(100); else delay_ms(50);
    assert(ea9_io_faults() == EA9_IO_TIMEBASE);
    assert(!test_port.Group[0].PINCFG[8].bit.PMUXEN);
    assert(!test_port.Group[0].PINCFG[9].bit.PMUXEN);
    assert(!test_port.Group[0].PINCFG[18].bit.PMUXEN);
    assert(!test_port.Group[0].PINCFG[19].bit.PMUXEN);
    puts("actual delay with frozen SysTick released motor and returned"); return 0;
}
