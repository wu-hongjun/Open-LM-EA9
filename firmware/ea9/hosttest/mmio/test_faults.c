#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "io_guard.h"
#include "motor.h"
#include "abs_encoder.h"
#include "vdd.h"
#include "em_uart.h"
void SERCOM1_Handler(void);
Port test_port;
Pm test_pm;
Gclk test_gclk;
Tcc test_tcc;
Sercom test_spi, test_uart;
Adc test_adc;
static uint32_t tick, irq;
static int pending_irq, frozen, adc_never_ready;
uint32_t test_irq_state(void) { return irq; }
void test_irq_disable(void) { irq = 1; }
void test_irq_restore(uint32_t state) {
    irq = state;
    if (!irq && pending_irq) { pending_irq = 0; ea9_io_trip(EA9_IO_UART); }
}
uint32_t millis(void) {
    /* Model W1C RESRDY and a conversion that never completes. */
    if (adc_never_ready && test_adc.SWTRIG.reg) test_adc.INTFLAG.reg = 0;
    return frozen ? tick : tick++;
}
static int detached(void) {
    return !test_port.Group[0].PINCFG[8].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[9].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[18].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[19].bit.PMUXEN;
}
int main(int argc, char **argv) {
    assert(argc == 2); motor_attach_pins(); assert(!detached());
    if (!strcmp(argv[1], "encoder")) {
        assert(abs_encoder_raw() == 0); assert(ea9_io_faults() == EA9_IO_ENCODER);
        assert(test_port.Group[0].OUTSET.reg == (1u << ENC_CS1_PIN));
        assert(abs_encoder_track() == 0); abs_encoder_track_reset();
    } else if (!strcmp(argv[1], "encoder-reset")) {
        abs_encoder_init(); assert(ea9_io_faults() == EA9_IO_ENCODER);
    } else if (!strcmp(argv[1], "burst-frozen")) {
        frozen = 1; uint16_t lo = 99, hi = 99;
        vdd_read_burst(&lo, &hi, 20);
        assert(ea9_io_faults() == EA9_IO_TIMEBASE && lo == 0 && hi == 0);
    } else if (!strcmp(argv[1], "adc")) {
        adc_never_ready = 1;
        assert(vdd_read_mv() == 0 && ea9_io_faults() == EA9_IO_ADC);
    } else if (!strcmp(argv[1], "uart")) {
        uint8_t byte = 0; em_uart_send(&byte, 1); assert(ea9_io_faults() == EA9_IO_UART);
    } else if (!strcmp(argv[1], "uart-rx")) {
        test_uart.USART.INTFLAG.reg = SERCOM_USART_INTFLAG_RXC;
        SERCOM1_Handler(); assert(ea9_io_faults() == EA9_IO_UART);
    } else if (!strcmp(argv[1], "pwm")) {
        *(volatile uint32_t *)&test_tcc.SYNCBUSY.reg = 0xf00;
        motor_drive(500); assert(ea9_io_faults() == EA9_IO_PWM);
    } else if (!strcmp(argv[1], "release")) {
        *(volatile uint32_t *)&test_tcc.SYNCBUSY.reg = 0xffffffff;
        uint32_t before = tick; motor_emergency_release(); assert(before == tick);
        motor_inhibit(); motor_drive(500); assert(detached());
        puts("no-wait release and shutdown inhibition passed"); return 0;
    } else if (!strcmp(argv[1], "irq")) {
        pending_irq = 1; motor_attach_pins();
        assert(ea9_io_faults() == EA9_IO_UART && !irq);
    } else if (!strcmp(argv[1], "irq-masked")) {
        irq = 1; pending_irq = 1; motor_attach_pins(); assert(irq == 1 && !ea9_io_faults());
        test_irq_restore(0); assert(ea9_io_faults() == EA9_IO_UART);
    } else if (!strcmp(argv[1], "frozen")) {
        frozen = 1; assert(abs_encoder_raw() == 0); assert(ea9_io_faults() == EA9_IO_ENCODER);
    } else { assert(0); }
    assert(detached()); uint32_t before = tick; motor_drive(1000); motor_brake(); motor_attach_pins(); assert(detached() && tick == before);
    puts("actual hardware-driver fault/rearm case passed"); return 0;
}
