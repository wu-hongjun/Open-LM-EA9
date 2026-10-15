/* Only PBC and WP, only erased 64-byte pages inside the reserved app tail. */
#include "board.h"
#include "delay.h"
#include "em_uart.h"
#include "startup_trace.h"
uint32_t st_lock(void) { uint32_t k=__get_PRIMASK(); __disable_irq(); return k; }
void st_unlock(uint32_t k) { __set_PRIMASK(k); }
static int address_ok(uint32_t a) {
    return a>=ST_FLASH_BASE && a<=ST_FLASH_END-ST_PAGE_BYTES && !(a&63u);
}
int st_read_page(uint32_t a, uint8_t p[64]) {
    if (!address_ok(a)) return 0;
    for (unsigned i=0;i<64;i++) p[i]=((volatile const uint8_t *)a)[i];
    return 1;
}
static int ready(void) {
    uint32_t budget=4194304u;
    while (!(NVMCTRL->INTFLAG.reg&NVMCTRL_INTFLAG_READY)) if (--budget==0) return 0;
    return 1;
}
int st_write_page(uint32_t a, const uint8_t p[64]) {
    if (!address_ok(a) || !ready()
        || (NVMCTRL->STATUS.reg&(NVMCTRL_STATUS_PROGE|NVMCTRL_STATUS_LOCKE|NVMCTRL_STATUS_NVME))) return 0;
    for (unsigned i=0;i<64;i++) if (((volatile const uint8_t *)a)[i]!=255) return 0;
    NVMCTRL->CTRLB.bit.MANW=1;
    NVMCTRL->ADDR.reg=a/2;
    NVMCTRL->CTRLA.reg=NVMCTRL_CTRLA_CMDEX_KEY|NVMCTRL_CTRLA_CMD_PBC;
    if (!ready()) return 0;
    for (unsigned i=0;i<16;i++) {
        uint32_t word=0;
        for (unsigned k=0;k<4;k++) word|=(uint32_t)p[4*i+k]<<(8*k);
        ((volatile uint32_t *)a)[i]=word;
    }
    /* AHB read barrier after filling the buffer (SAM D21 manual-write guidance). */
    (void)*(volatile const uint32_t *)a;
    NVMCTRL->ADDR.reg=a/2;
    NVMCTRL->CTRLA.reg=NVMCTRL_CTRLA_CMDEX_KEY|NVMCTRL_CTRLA_CMD_WP;
    (void)*(volatile const uint32_t *)a;
    if (!ready() || (NVMCTRL->STATUS.reg&(NVMCTRL_STATUS_PROGE|NVMCTRL_STATUS_LOCKE|NVMCTRL_STATUS_NVME))) return 0;
    for (unsigned i=0;i<64;i++) if (((volatile const uint8_t *)a)[i]!=p[i]) return 0;
    return 1;
}
void st_fail(uint8_t fault) {
    __disable_irq();
    /* Fail-stop without waiting on a possibly wedged TCC synchronization. */
    PORT->Group[0].PINCFG[MOTOR_PIN_WO0].bit.PMUXEN=0;
    PORT->Group[0].PINCFG[MOTOR_PIN_WO1].bit.PMUXEN=0;
    PORT->Group[0].PINCFG[MOTOR_PIN_WO2].bit.PMUXEN=0;
    PORT->Group[0].PINCFG[MOTOR_PIN_WO3].bit.PMUXEN=0;
    PORT->Group[0].DIRCLR.reg=(1u<<MOTOR_PIN_WO0)|(1u<<MOTOR_PIN_WO1)
                           |(1u<<MOTOR_PIN_WO2)|(1u<<MOTOR_PIN_WO3);
    PORT->Group[0].OUTSET.reg=1u<<MOTOR_PIN_WO3;
    st_note(ST_FAULT,fault,0,0,0,0,millis());
    st_flush(1,millis(),em_rx_bytes,(uint16_t)em_rx_errors,em_rx_status,255);
    for (;;) __WFI();
}
