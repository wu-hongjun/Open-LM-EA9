/* Target-only, included by startup_trace_flash.c. Independent OSCULP32K
 * source; no IRQ pet and no flash operations in a foreground health sample. */
static void st_halt(void) __attribute__((noreturn));
static void st_halt(void) { __disable_irq(); for (;;) __WFI(); }
static void st_wdt_sync(void)
{
    uint32_t budget=4194304u;
    while (WDT->STATUS.bit.SYNCBUSY) if (!--budget) st_halt();
}
static void st_gclk_sync(void)
{
    uint32_t budget=4194304u;
    while (GCLK->STATUS.bit.SYNCBUSY) if (!--budget) st_halt();
}
void st_crash_boot(void)
{
    motor_emergency_release();
    uint8_t cause=PM->RCAUSE.reg;
    PM->APBAMASK.reg |= PM_APBAMASK_WDT;
    /* An always-on fuse is incompatible with this fail-stop design. */
    if (WDT->CTRL.bit.ALWAYSON) st_halt();
    st_wdt_sync();
    WDT->CTRL.reg=0;
    st_wdt_sync();
    st_init();
    if (st_boot_record(cause)) st_halt();
}
void st_watchdog_start(void)
{
    GCLK->GENDIV.reg=GCLK_GENDIV_ID(4)|GCLK_GENDIV_DIV(32);
    st_gclk_sync();
    GCLK->GENCTRL.reg=GCLK_GENCTRL_ID(4)|GCLK_GENCTRL_SRC_OSCULP32K
        |GCLK_GENCTRL_GENEN;
    st_gclk_sync();
    GCLK->CLKCTRL.reg=GCLK_CLKCTRL_ID(WDT_GCLK_ID)|GCLK_CLKCTRL_GEN_GCLK4
        |GCLK_CLKCTRL_CLKEN;
    st_gclk_sync();
    WDT->CONFIG.reg=WDT_CONFIG_PER_4K;
}
void st_watchdog_arm(void)
{
    /* Configuration was completed before protocol activation; enabling is
     * asynchronous, without an active-protocol synchronization wait. */
    if (WDT->STATUS.bit.SYNCBUSY) st_halt();
    WDT->CTRL.reg=WDT_CTRL_ENABLE;
}
void st_health(uint32_t now)
{
    static uint32_t last;
    if ((uint32_t)(now-last)<250u || WDT->STATUS.bit.SYNCBUSY) return;
    last=now;
    st_checkpoint(now);
    /* Asynchronous clear: never wait on synchronization in protocol flow. */
    WDT->CLEAR.reg=WDT_CLEAR_CLEAR_KEY;
}
/* No C prologue, no exception-stack dereference, no flash attempt in fault
 * context. System-reset cause does not uniquely identify a HardFault. */
void HardFault_Handler(void) __attribute__((naked));
void HardFault_Handler(void)
{
    __asm__ volatile (
        "cpsid i\n"
        "dsb\n"
        "ldr r0, =0xe000ed0c\n"
        "ldr r1, =0x05fa0004\n"
        "str r1, [r0]\n"
        "dsb\n"
        "1: b 1b\n");
}
