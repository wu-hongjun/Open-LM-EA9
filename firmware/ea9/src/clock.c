/* clock.c -- bring GCLK0 to 48 MHz exactly the way the stock firmware does.
 *
 * Recovered from 0x81b8 (DFLL) and 0x770c (generators), NOTES.md §13:
 *   DFLL48M open loop  -- DFLLCTRL = ENABLE only, DFLLMUL = 0 (MUL = 0),
 *                         DFLLVAL COARSE from the factory calibration word at
 *                         0x00806024 with the 0x3f -> 0x1f fallback, FINE = 512
 *   GEN0 = DFLL48M, GEN1 = OSC32K, GEN2 = OSC8M
 *
 * At 48 MHz the flash needs one wait state.
 */
#include "board.h"
#ifdef EA9_AF_BUILD
#include "io_guard.h"
#endif

#ifndef NVM_CAL_WORD1
#define NVM_CAL_WORD1           (*(volatile uint32_t *)0x00806024u)
#endif
#define NVM_DFLL_COARSE_POS     26
#define NVM_DFLL_COARSE_MASK    0x3fu

static uint8_t gclk_sync(void)
{
#ifdef EA9_AF_BUILD
	return EA9_IO_WAIT_STARTUP(!GCLK->STATUS.bit.SYNCBUSY, EA9_IO_CLOCK);
#else
	while (GCLK->STATUS.bit.SYNCBUSY) {
	}
	return 1;
#endif
}

void clock_init(void)
{
	/* one wait state is required above 24 MHz */
	NVMCTRL->CTRLB.bit.RWS = 1;

	/* --- DFLL48M, open loop ------------------------------------------- */
	SYSCTRL->DFLLCTRL.reg = SYSCTRL_DFLLCTRL_ENABLE;
#ifdef EA9_AF_BUILD
	if (!EA9_IO_WAIT_STARTUP(SYSCTRL->PCLKSR.bit.DFLLRDY, EA9_IO_CLOCK)) return;
#else
	while (!SYSCTRL->PCLKSR.bit.DFLLRDY) {
	}
#endif

	SYSCTRL->DFLLMUL.reg = SYSCTRL_DFLLMUL_CSTEP(1) | SYSCTRL_DFLLMUL_FSTEP(1);

	uint32_t coarse = (NVM_CAL_WORD1 >> NVM_DFLL_COARSE_POS) & NVM_DFLL_COARSE_MASK;
	if (coarse == NVM_DFLL_COARSE_MASK) {
		coarse = 0x1f;                 /* uncalibrated part: mid-scale */
	}
	SYSCTRL->DFLLVAL.reg = SYSCTRL_DFLLVAL_COARSE(coarse) | SYSCTRL_DFLLVAL_FINE(512);

	SYSCTRL->DFLLCTRL.reg = SYSCTRL_DFLLCTRL_ENABLE;
#ifdef EA9_AF_BUILD
	if (!EA9_IO_WAIT_STARTUP(SYSCTRL->PCLKSR.bit.DFLLRDY, EA9_IO_CLOCK)) return;
#else
	while (!SYSCTRL->PCLKSR.bit.DFLLRDY) {
	}
#endif

	/* --- generator 0 = DFLL48M, no division ---------------------------- */
	GCLK->GENDIV.reg = GCLK_GENDIV_ID(0) | GCLK_GENDIV_DIV(1);
	if (!gclk_sync()) return;
	GCLK->GENCTRL.reg = GCLK_GENCTRL_ID(0) | GCLK_GENCTRL_SRC_DFLL48M
	                    | GCLK_GENCTRL_GENEN;
	(void)gclk_sync();
}

/* Route generator 0 to one peripheral channel and turn on its APBC clock. */
void clock_enable_peripheral(uint8_t gclk_id, uint32_t apbc_mask)
{
	PM->APBCMASK.reg |= apbc_mask;
	GCLK->CLKCTRL.reg = GCLK_CLKCTRL_ID(gclk_id) | GCLK_CLKCTRL_GEN_GCLK0
	                    | GCLK_CLKCTRL_CLKEN;
#ifdef EA9_AF_BUILD
	/* Runtime peripheral routing follows delay_init; a motion fault must not
	 * suppress the clock readiness check for an otherwise healthy UART. */
	(void)EA9_IO_WAIT_MASK(!GCLK->STATUS.bit.SYNCBUSY, EA9_IO_CLOCK, EA9_IO_TIMING_FAULTS);
#else
	(void)gclk_sync();
#endif
}
