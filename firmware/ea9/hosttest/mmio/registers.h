/* Host register memory uses the official DFP register types. No mapped I/O. */
#include "board.h"
extern Port test_port;
extern Pm test_pm;
extern Gclk test_gclk;
extern Tcc test_tcc;
extern Sercom test_spi, test_uart;
extern Adc test_adc;
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
