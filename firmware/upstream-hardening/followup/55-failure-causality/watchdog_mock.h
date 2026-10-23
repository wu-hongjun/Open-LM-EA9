/* Inert register/control-flow boundary. Not a peripheral or timing model. */
typedef union { uint32_t reg; struct { unsigned SYNCBUSY:1, ALWAYSON:1; } bit; } reg_t;
struct host_wdt { reg_t STATUS,CTRL,CONFIG,CLEAR; }; extern struct host_wdt wdt;
struct host_gclk { reg_t STATUS,GENDIV,GENCTRL,CLKCTRL; }; extern struct host_gclk gclk;
struct host_pm { reg_t RCAUSE,APBAMASK; }; extern struct host_pm pm;
#define PM_APBAMASK_WDT (1u<<4)
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
void host_disable_irq(void);
void host_wfi(void) __attribute__((noreturn));
#define __disable_irq() host_disable_irq()
#define __WFI() host_wfi()
