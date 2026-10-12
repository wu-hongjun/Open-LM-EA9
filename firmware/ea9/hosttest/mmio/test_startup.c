/* Real clock/EIC/UART setup against DFP register memory, never physical MMIO.
 * Poll-only clock bounds are intentionally tested with no millisecond reads. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "io_guard.h"
#include "clock.h"
#include "motor.h"
#include "em_eic.h"
#include "em_uart.h"

Port test_port;
Pm test_pm;
Gclk test_gclk;
Tcc test_tcc;
Sercom test_spi, test_uart;
Adc test_adc;
Sysctrl test_sysctrl;
Eic test_eic;
Nvmctrl test_nvmctrl;
uint32_t test_dfll_cal_word = (0x1Fu << 26);
static uint32_t tick, irq, millis_reads;
static int scenario, nvic_enables, eic_priority;

uint32_t test_irq_state(void) { return irq; }
void test_irq_disable(void) { irq = 1; }
void test_irq_restore(uint32_t state) { irq = state; }
void test_nvic_enable(IRQn_Type number) { (void)number; ++nvic_enables; }
void test_nvic_priority(IRQn_Type number, uint32_t priority)
{ assert(number == EIC_IRQn); eic_priority = (int)priority; }

uint32_t millis(void)
{
    ++millis_reads;
    /* A RAM-backed peripheral does not self-clear reset or assert sync busy.
     * Model those external transitions explicitly, excluding each stuck case. */
    if (scenario != 3 && scenario != 7) test_eic.CTRL.reg &= (uint8_t)~EIC_CTRL_SWRST;
    if (scenario == 4 && test_eic.CTRL.bit.ENABLE)
        *(volatile uint8_t *)&test_eic.STATUS.reg = EIC_STATUS_SYNCBUSY;
    if (scenario != 5) test_uart.USART.CTRLA.reg &= ~SERCOM_USART_CTRLA_SWRST;
    if (scenario == 6 && test_uart.USART.CTRLB.reg)
        *(volatile uint32_t *)&test_uart.USART.SYNCBUSY.reg = SERCOM_USART_SYNCBUSY_CTRLB;
    return scenario == 7 || scenario == 8 ? tick : tick++;
}
void delay_us(uint32_t us) { (void)us; }
void delay_ms(uint32_t ms) { (void)ms; }
static int detached(void)
{
    return !test_port.Group[0].PINCFG[8].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[9].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[18].bit.PMUXEN &&
           !test_port.Group[0].PINCFG[19].bit.PMUXEN;
}
int main(int argc, char **argv)
{
    assert(argc == 2); scenario = atoi(argv[1]);
    motor_attach_pins(); assert(!detached());
    *(volatile uint32_t *)&test_sysctrl.PCLKSR.reg = SYSCTRL_PCLKSR_DFLLRDY;
    if (scenario == 0 || scenario == 8) {
        if (scenario == 8) irq = 1;
        *(volatile uint32_t *)&test_sysctrl.PCLKSR.reg = 0;
        clock_init();
        assert(ea9_io_faults() == EA9_IO_CLOCK && !millis_reads);
        assert(!test_gclk.GENCTRL.reg && !test_sysctrl.DFLLMUL.reg);
        assert(irq == (scenario == 8));
    } else if (scenario == 1) {
        *(volatile uint8_t *)&test_gclk.STATUS.reg = GCLK_STATUS_SYNCBUSY;
        clock_init();
        assert(ea9_io_faults() == EA9_IO_CLOCK && !millis_reads);
        assert(!test_gclk.GENCTRL.reg);
    } else if (scenario == 2 || scenario == 3 || scenario == 4 || scenario == 7) {
        if (scenario == 2) *(volatile uint8_t *)&test_gclk.STATUS.reg = GCLK_STATUS_SYNCBUSY;
        em_eic_init(NULL, NULL);
        assert(ea9_io_faults() == EA9_IO_EIC && !nvic_enables);
        if (scenario == 3 || scenario == 7) assert(!test_eic.CONFIG[0].reg);
    } else if (scenario == 5 || scenario == 6) {
        em_uart_init(); assert(ea9_io_faults() == EA9_IO_UART && !nvic_enables);
        assert(!test_uart.USART.CTRLA.bit.ENABLE);
    } else if (scenario == 9) {
        clock_init();
        assert(!ea9_io_faults() && !millis_reads);
        assert(test_sysctrl.DFLLCTRL.reg == SYSCTRL_DFLLCTRL_ENABLE);
        assert(test_sysctrl.DFLLVAL.reg == (SYSCTRL_DFLLVAL_COARSE(0x1F) | SYSCTRL_DFLLVAL_FINE(512)));
        assert(test_gclk.GENCTRL.reg == (GCLK_GENCTRL_ID(0) | GCLK_GENCTRL_SRC_DFLL48M | GCLK_GENCTRL_GENEN));
        em_eic_init(NULL, NULL);
        assert(!ea9_io_faults() && nvic_enables == 1 && eic_priority == 1);
        assert(test_eic.CONFIG[0].reg == ((0xBu << (4 * EM_EXTINT_BODY_CS)) | (0x9u << (4 * EM_EXTINT_BODY_VD))));
        assert(test_eic.CTRL.reg == EIC_CTRL_ENABLE);
        em_uart_init();
        assert(!ea9_io_faults() && nvic_enables == 2);
        assert(test_uart.USART.CTRLA.reg == (EM_CTRLA | SERCOM_USART_CTRLA_ENABLE));
        assert(test_uart.USART.CTRLB.reg == EM_CTRLB && test_uart.USART.BAUD.reg == EM_BAUD);
        printf("real initialization successful register sequence passed\n"); return 0;
    } else if (scenario == 10) {
        *(volatile uint8_t *)&test_gclk.STATUS.reg = GCLK_STATUS_SYNCBUSY;
        em_uart_init(); assert(ea9_io_faults() == EA9_IO_CLOCK && millis_reads);
        assert(!test_uart.USART.CTRLA.reg && !nvic_enables);
    } else if (scenario >= 11 && scenario <= 13) {
        uint8_t reason = scenario == 11 ? EA9_IO_ENCODER : scenario == 12 ? EA9_IO_ADC : EA9_IO_PWM;
        ea9_io_trip(reason);
        em_eic_init(NULL, NULL); em_uart_init();
        if (ea9_io_faults() != reason || nvic_enables != 2) {
            fprintf(stderr,"motion fault blocked link initialization\n"); return 1;
        }
        assert(test_eic.CTRL.reg == EIC_CTRL_ENABLE);
        assert(test_uart.USART.CTRLA.reg == (EM_CTRLA | SERCOM_USART_CTRLA_ENABLE));
        assert(test_uart.USART.BAUD.reg == EM_BAUD);
    } else return 2;
    assert(detached());
    uint32_t before = millis_reads;
    motor_drive(1000); motor_brake(); motor_attach_pins();
    assert(detached() && before == millis_reads);
    printf("real initialization fault scenario %d returned with drive inhibited\n", scenario);
    return 0;
}
