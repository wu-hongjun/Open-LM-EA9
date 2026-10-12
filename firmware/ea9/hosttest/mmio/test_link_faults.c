/* Actual UART and GPIO motor-release code against RAM-backed DFP registers.
 * No electrical timing or camera behavior is represented. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "io_guard.h"
#include "motor.h"
#include "em_uart.h"
Port test_port;
Pm test_pm;
Gclk test_gclk;
Tcc test_tcc;
Sercom test_spi, test_uart;
Adc test_adc;
static uint32_t tick, irq;
static unsigned samples;
static uint8_t reason;
static int frozen, stall, mid_fault;
uint32_t test_irq_state(void) { return irq; }
void test_irq_disable(void) { irq = 1; }
void test_irq_restore(uint32_t state) { irq = state; }
uint32_t millis(void) {
    ++samples;
    /* Model ready flags and W1C TXC; RAM does not implement register semantics. */
    test_uart.USART.INTFLAG.reg = stall ? 0 : SERCOM_USART_INTFLAG_DRE | SERCOM_USART_INTFLAG_TXC;
    if (mid_fault && samples == 3) ea9_io_trip(reason);
    return frozen ? tick : tick++;
}
static int detached(void) {
    return !test_port.Group[0].PINCFG[8].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[9].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[18].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[19].bit.PMUXEN;
}
int main(int argc, char **argv) {
    assert(argc == 2);
    const char *name = argv[1];
    reason = !strcmp(name,"encoder") ? EA9_IO_ENCODER :
             !strcmp(name,"adc") ? EA9_IO_ADC :
             !strcmp(name,"pwm") ? EA9_IO_PWM :
             !strcmp(name,"combined") ? EA9_IO_ENCODER|EA9_IO_ADC|EA9_IO_PWM :
             !strcmp(name,"mid-adc") ? EA9_IO_ADC :
             !strcmp(name,"uart") ? EA9_IO_UART :
             !strcmp(name,"clock") ? EA9_IO_CLOCK :
             !strcmp(name,"timebase") ? EA9_IO_TIMEBASE :
             !strcmp(name,"eic") ? EA9_IO_EIC : 0;
    mid_fault = !strcmp(name,"mid-adc");
    stall = !strcmp(name,"stall") || !strcmp(name,"frozen");
    frozen = !strcmp(name,"frozen");
    motor_attach_pins(); assert(!detached());
    if (reason && !mid_fault) ea9_io_trip(reason);
    test_uart.USART.DATA.reg = 0xbeefu;
    const uint8_t bytes[] = {0xf0, 0x10, 0x01, 0x16, 0x55};
#ifdef EA9_FROZEN28
    em_uart_send(bytes, sizeof bytes);
#else
    uint8_t sent = em_uart_send(bytes, sizeof bytes);
    assert(sent == (!stall && !(reason & (EA9_IO_UART|EA9_IO_CLOCK|EA9_IO_TIMEBASE|EA9_IO_EIC))));
#endif
    if (reason && !(reason & (EA9_IO_UART|EA9_IO_CLOCK|EA9_IO_TIMEBASE|EA9_IO_EIC))) {
        if (test_uart.USART.DATA.reg != 0x55) {
            fprintf(stderr,"motion fault suppressed healthy UART\n"); return 1;
        }
        assert(ea9_io_faults() == reason && detached());
        motor_attach_pins(); motor_drive(800); assert(detached());
    } else if (reason || stall) {
        assert(test_uart.USART.DATA.reg == 0xbeefu && detached());
        assert(ea9_io_faults() == (reason ? reason : EA9_IO_UART));
    } else {
        assert(test_uart.USART.DATA.reg == 0x55 && !ea9_io_faults());
#ifndef EA9_FROZEN28
        em_uart_disable(); assert(!em_uart_send(bytes, sizeof bytes));
#endif
    }
    assert(!irq && samples <= EA9_IO_POLL_LIMIT + 3u);
    printf("actual UART fault isolation %s: passed\n",name); return 0;
}
