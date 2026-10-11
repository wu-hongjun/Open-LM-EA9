/* delay.c -- millisecond delay and a free-running millisecond tick on SysTick.
 *
 * The stock firmware uses ASF4's hal_delay on SysTick (0x64ac calls
 * delay_init(SysTick), NOTES.md §13).  This is the same idea written directly,
 * so the building blocks have no ASF4 dependency.
 */
#include "board.h"
#include "delay.h"
#ifdef EA9_AF_BUILD
#include "io_guard.h"
#endif

static volatile uint32_t g_millis;

void delay_init(void)
{
	SysTick->LOAD = (F_CPU / 1000u) - 1u;
	SysTick->VAL  = 0;
	SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk | SysTick_CTRL_TICKINT_Msk
	                | SysTick_CTRL_ENABLE_Msk;
}

void SysTick_Handler(void)
{
	g_millis++;
}

uint32_t millis(void)
{
	return g_millis;
}

uint32_t clock_cycles(void)
{
    /* Preserve the caller's IRQ mask. A rollover can pend after the first
     * VAL read but cannot advance the epoch while this snapshot is masked. */
    uint32_t mask = __get_PRIMASK();
    __disable_irq();
    uint32_t epoch = g_millis;
    uint32_t pending = SCB->ICSR & SCB_ICSR_PENDSTSET_Msk;
    uint32_t value = SysTick->VAL;
    uint32_t after = SCB->ICSR & SCB_ICSR_PENDSTSET_Msk;
    if (after && !pending) value = SysTick->VAL;
    if (after) ++epoch;
    uint32_t result = epoch * (F_CPU / 1000u) + SysTick->LOAD - value;
    __set_PRIMASK(mask);
    return result;
}

void delay_ms(uint32_t ms)
{
	uint32_t start = g_millis;
#ifdef EA9_AF_BUILD
	uint32_t polls = 0;
#endif
	while ((uint32_t)(g_millis - start) < ms) {
#ifdef EA9_AF_BUILD
		if (ea9_io_faults()) return;
		if (++polls >= EA9_MOTION_POLL_LIMIT) { ea9_io_trip(EA9_IO_TIMEBASE); return; }
#endif
	}
}

/* Microsecond delay, counted in SysTick cycles rather than in a calibrated
 * loop so it survives -O changes.  The protocol gaps it has to reproduce are
 * 10 us, 100 us and 300 us (emount.c), all far shorter than the 1 ms reload,
 * but the wrap is handled anyway so a long call cannot silently return early.
 */
void delay_us(uint32_t us)
{
	uint32_t target  = us * (F_CPU / 1000000u);
	uint32_t elapsed = 0;
	uint32_t last    = SysTick->VAL;
#ifdef EA9_AF_BUILD
	struct ea9_io_wait wait = { millis(), 0 };
#endif

	while (elapsed < target) {
		uint32_t now = SysTick->VAL;
#ifdef EA9_AF_BUILD
		if (!ea9_io_wait_pending(&wait, EA9_IO_TIMEBASE)) return;
#endif

		/* SysTick counts DOWN, so a normal step is last - now. */
		elapsed += (last >= now) ? (last - now)
		                         : (last + SysTick->LOAD + 1u - now);
		last = now;
	}
}
