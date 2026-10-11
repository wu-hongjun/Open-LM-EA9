/* Host register memory uses the official DFP register types. No mapped I/O. */
#include "board.h"
extern Port test_port;
extern Pm test_pm;
extern Gclk test_gclk;
extern Tcc test_tcc;
extern Sercom test_spi, test_uart;
extern Adc test_adc;
extern Sysctrl test_sysctrl;
extern Eic test_eic;
extern Nvmctrl test_nvmctrl;
extern uint32_t test_dfll_cal_word;
#undef PORT
#undef PM
#undef GCLK
#undef TCC0
#undef ADC
#define PORT (&test_port)
#define PM (&test_pm)
#define GCLK (&test_gclk)
#define TCC0 (&test_tcc)
#define ADC (&test_adc)
#undef SYSCTRL
#undef EIC
#define SYSCTRL (&test_sysctrl)
#define EIC (&test_eic)
#undef NVMCTRL
#define NVMCTRL (&test_nvmctrl)
#define NVM_CAL_WORD1 test_dfll_cal_word
void test_nvic_enable(IRQn_Type irq);
void test_nvic_priority(IRQn_Type irq, uint32_t priority);
#undef NVIC_EnableIRQ
#undef NVIC_SetPriority
#define NVIC_EnableIRQ(irq) test_nvic_enable(irq)
#define NVIC_SetPriority(irq, priority) test_nvic_priority(irq, priority)
#undef ENC_SPI_SERCOM_ADDR
#undef EM_SERCOM_ADDR
#define ENC_SPI_SERCOM_ADDR ((uintptr_t)&test_spi)
#define EM_SERCOM_ADDR ((uintptr_t)&test_uart)
uint32_t test_irq_state(void);
void test_irq_disable(void);
void test_irq_restore(uint32_t state);
#define __get_PRIMASK() test_irq_state()
#define __disable_irq() test_irq_disable()
#define __set_PRIMASK(state) test_irq_restore(state)

extern SysTick_Type test_systick;
#undef SysTick
#define SysTick (&test_systick)
