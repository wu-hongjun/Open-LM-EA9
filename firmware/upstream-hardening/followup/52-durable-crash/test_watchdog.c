#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
typedef union { uint32_t reg; struct { unsigned SYNCBUSY:1, ALWAYSON:1; } bit; } reg_t;
static struct { reg_t STATUS,CTRL,CONFIG,CLEAR; } wdt;
static struct { reg_t STATUS,GENDIV,GENCTRL,CLKCTRL; } gclk;
static struct { reg_t RCAUSE,APBAMASK; } pm;
#define PM_APBAMASK_WDT (1u<<3)
#define WDT (&wdt)
#define GCLK (&gclk)
#define PM (&pm)
#define GCLK_GENDIV_ID(x) (x)
#define GCLK_GENDIV_DIV(x) ((x)<<8)
#define GCLK_GENCTRL_ID(x) (x)
#define GCLK_GENCTRL_SRC_OSCULP32K (3u<<8)
#define GCLK_GENCTRL_GENEN (1u<<16)
#define GCLK_CLKCTRL_ID(x) (x)
#define WDT_GCLK_ID 3u
#define GCLK_CLKCTRL_GEN_GCLK4 (4u<<8)
#define GCLK_CLKCTRL_CLKEN (1u<<14)
#define WDT_CONFIG_PER_4K 9u
#define WDT_CTRL_ENABLE 2u
#define WDT_CLEAR_CLEAR_KEY 0xa5u
static jmp_buf halted;
static unsigned masked, initialized, records, checkpoints, boot_halt;
static uint32_t checkpoint_ms;
void motor_emergency_release(void) { }
#define __disable_irq() (++masked)
#define __WFI() longjmp(halted,1)
void st_init(void) { ++initialized; }
int st_boot_record(uint8_t cause) { ++records; return boot_halt || (cause&96u); }
void st_checkpoint(uint32_t now) { ++checkpoints; checkpoint_ms=now; }
#include "watchdog_host.inc"
int main(void)
{
    pm.RCAUSE.reg=1;
    st_crash_boot(); assert(initialized==1 && records==1 && !masked);
    assert(pm.APBAMASK.reg&PM_APBAMASK_WDT);
    pm.RCAUSE.reg=32;
    if (!setjmp(halted)) { st_crash_boot(); assert(!"WDT boot returned"); }
    assert(initialized==2 && records==2 && masked);
    pm.RCAUSE.reg=1; boot_halt=1;
    if (!setjmp(halted)) { st_crash_boot(); assert(!"persistent latch returned"); }
    assert(records==3); boot_halt=0;
    wdt.CTRL.bit.ALWAYSON=1;
    if (!setjmp(halted)) { st_crash_boot(); assert(!"always-on boot returned"); }
    assert(records==3); wdt.CTRL.reg=0;
    wdt.STATUS.bit.SYNCBUSY=1;
    if (!setjmp(halted)) { st_crash_boot(); assert(!"wedged boot sync returned"); }
    assert(records==3); wdt.STATUS.reg=0;
    st_watchdog_start();
    assert(wdt.CTRL.reg==0 && wdt.CONFIG.reg==WDT_CONFIG_PER_4K);
    assert(gclk.GENDIV.reg==(4u|(32u<<8)));
    assert(gclk.GENCTRL.reg==(4u|GCLK_GENCTRL_SRC_OSCULP32K|GCLK_GENCTRL_GENEN));
    st_watchdog_arm(); assert(wdt.CTRL.reg==WDT_CTRL_ENABLE);
    st_health(249); assert(!checkpoints && !wdt.CLEAR.reg);
    st_health(250); assert(checkpoints==1 && checkpoint_ms==250 && wdt.CLEAR.reg==0xa5);
    wdt.CLEAR.reg=0; st_health(250); assert(!wdt.CLEAR.reg && checkpoints==1);
    wdt.STATUS.bit.SYNCBUSY=1; st_health(500);
    assert(!wdt.CLEAR.reg && checkpoints==1);
    wdt.STATUS.reg=0; st_health(500); assert(checkpoints==2 && wdt.CLEAR.reg==0xa5);
    wdt.CLEAR.reg=0; st_health(500); assert(!wdt.CLEAR.reg);
    st_health(UINT32_MAX-100); st_health(149); assert(checkpoint_ms==149);
    puts("watchdog actual-C paths pass");
}
