#ifndef DELAY_H
#define DELAY_H
#include <stdint.h>
void     delay_init(void);
uint32_t millis(void);
/* Nominal 48 MHz ticks, wrapping modulo 2^32. SysTick epoch + sub-ms phase.
 * Used only by the factory baseline's foreground scheduler. */
uint32_t clock_cycles(void);
void     delay_ms(uint32_t ms);
void     delay_us(uint32_t us);
#endif
