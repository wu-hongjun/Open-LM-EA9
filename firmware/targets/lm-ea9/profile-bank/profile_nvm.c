/* LM-EA9 SAMD21 port; portable selection logic lives under firmware/features. */
#include "profile_nvm.h"
#include "sam.h"
#include <string.h>

/* Run command + READY polling from SRAM, with interrupts masked by the caller.
 * This bounds software polling, not an electrical/peripheral bus failure. */
#define RAM __attribute__((section(".ramfunc.profile"), noinline))
#define WAIT_BUDGET 1000000u
static int faulted;
int pb_journal_range(unsigned offset, unsigned bytes, unsigned alignment) {
    return alignment && offset%alignment==0 && bytes && offset<PB_JOURNAL_BYTES &&
           bytes<=PB_JOURNAL_BYTES-offset;
}
static RAM int ready(void) {
    for(unsigned n=0;n<WAIT_BUDGET;++n)
        if(NVMCTRL->INTFLAG.reg & NVMCTRL_INTFLAG_READY) return 1;
    return 0;
}
static RAM int command(uint16_t cmd) {
    if(!ready()) return 0;
    NVMCTRL->CTRLA.reg=(uint16_t)(0xa500u | cmd);
    /* Peripheral read barrier without a main-array read while NVM is busy. */
    (void)NVMCTRL->INTFLAG.reg;
    return ready() && !(NVMCTRL->STATUS.reg &
        (NVMCTRL_STATUS_PROGE | NVMCTRL_STATUS_LOCKE | NVMCTRL_STATUS_NVME));
}
static RAM int mutate(unsigned offset, const uint8_t *page) {
    uint32_t key=__get_PRIMASK(); __disable_irq();
    uint32_t ctrl=NVMCTRL->CTRLB.reg;
    int ok=ready();
    if(ok) {
        NVMCTRL->STATUS.reg=NVMCTRL_STATUS_PROGE | NVMCTRL_STATUS_LOCKE | NVMCTRL_STATUS_NVME;
        NVMCTRL->CTRLB.reg=ctrl | NVMCTRL_CTRLB_MANW;
        if(page) {
            ok=command(NVMCTRL_CTRLA_CMD_PBC);
            if(ok) {
                volatile uint16_t *dst=(volatile uint16_t *)(PB_JOURNAL_ADDRESS+offset);
                for(unsigned i=0;i<32;++i) dst[i]=(uint16_t)(page[2*i] | (uint16_t)page[2*i+1]<<8);
            }
        }
        if(ok) {
            NVMCTRL->ADDR.reg=(PB_JOURNAL_ADDRESS+offset)/2;
            ok=command(page ? NVMCTRL_CTRLA_CMD_WP : NVMCTRL_CTRLA_CMD_ER);
        }
        if(ok) ok=command(NVMCTRL_CTRLA_CMD_INVALL);
        /* Restore only once idle. On a timeout, latch fault and issue no more commands. */
        if(NVMCTRL->INTFLAG.reg & NVMCTRL_INTFLAG_READY) NVMCTRL->CTRLB.reg=ctrl;
    }
    if(!ok) faulted=1;
    __set_PRIMASK(key); return ok ? 0 : -1;
}
static int allowed(int writing) {
    uint32_t p=NVMCTRL->PARAM.reg;
    if(faulted || (p & NVMCTRL_PARAM_NVMP_Msk)!=2048u ||
       (p & NVMCTRL_PARAM_PSZ_Msk)!=NVMCTRL_PARAM_PSZ_64 || !ready()) return 0;
    /* E17A: sixteen 8 KiB lock regions. Never change their lock state. */
    return !writing || (NVMCTRL->LOCK.reg & (1u << (PB_JOURNAL_ADDRESS/8192u))) != 0;
}
static int read_bytes(void *ctx, unsigned off, uint8_t *out, unsigned n) {
    (void)ctx;
    if(!pb_journal_range(off,n,1) || !allowed(0)) return -1;
    memcpy(out,(const void *)(PB_JOURNAL_ADDRESS+off),n); return 0;
}
static int write_page(void *ctx, unsigned off, const uint8_t *page) {
    (void)ctx;
    if(!pb_journal_range(off,64,256) || !allowed(1)) return -1;
    const volatile uint8_t *p=(const volatile uint8_t *)(PB_JOURNAL_ADDRESS+off);
    for(unsigned i=0;i<64;++i) if(p[i]!=255) return -1;
    return mutate(off,page);
}
static int erase_row(void *ctx, unsigned off) {
    (void)ctx;
    if(!pb_journal_range(off,256,256) || !allowed(1)) return -1;
    return mutate(off,0);
}
const pb_io *pb_samd21_io(void) {
    static const pb_io io={0,read_bytes,write_page,erase_row}; return &io;
}
