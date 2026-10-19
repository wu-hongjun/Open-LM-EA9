/* Extracted production control flow; inert MMIO and a synthetic tick-read boundary. */
#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "startup_trace.h"
static jmp_buf stop;
static unsigned fault,reads,advance;
static volatile uint32_t g_millis;
static volatile uint8_t g_disabled;
static struct {struct {
 struct {volatile uint32_t reg;} CTRLA,SYNCBUSY,DATA;
 struct {volatile uint32_t reg;struct {volatile unsigned DRE,TXC;}bit;}INTFLAG;
}USART;} peripheral;
#define EMSERCOM (&peripheral)
#define SERCOM_USART_CTRLA_ENABLE 2u
#define SERCOM_USART_INTFLAG_TXC 2u
void st_fail(uint8_t f){fault=f;longjmp(stop,1);}
/* Production SysTick ISR and millis; only delay_ms's tick read is substituted. */
/* EXTRACTED_CLOCK_FUNCTIONS */
static uint32_t probe_tick(void){reads++;if(advance)SysTick_Handler();return millis();}
/* EXTRACTED_DELAY_FUNCTION */
/* EXTRACTED_UART_FUNCTIONS */
int main(int argc,char **argv){
 assert(argc==2);unsigned scenario=(unsigned)atoi(argv[1]);uint8_t byte=0x5a;
 if(scenario==0){advance=1;for(unsigned i=0;i<4;i++){const unsigned durations[]={0,1,50,100};uint32_t before=g_millis;delay_ms(durations[i]);assert(g_millis-before==durations[i]+1u+(durations[i]==0));}g_millis=UINT32_MAX-10;delay_ms(50);assert(g_millis==40);}
 else if(scenario==1){if(!setjmp(stop)){delay_ms(1);assert(0);}assert(fault==ST_TICK_WAIT && reads==268435457u && g_millis==0);}
 else if(scenario==2){peripheral.USART.CTRLA.reg=2;em_uart_disable();assert(g_disabled && peripheral.USART.CTRLA.reg==0);peripheral.USART.SYNCBUSY.reg=1;assert(!em_uart_send(&byte,1));}
 else if(scenario==3){peripheral.USART.SYNCBUSY.reg=1;if(!setjmp(stop)){em_uart_disable();assert(0);}assert(g_disabled && fault==ST_UART_WAIT);}
 else if(scenario==4 || scenario==5){peripheral.USART.INTFLAG.bit.DRE=scenario==5;if(!setjmp(stop)){em_uart_send(&byte,1);assert(0);}assert(fault==ST_UART_WAIT);}
 else {peripheral.USART.INTFLAG.bit.DRE=peripheral.USART.INTFLAG.bit.TXC=1;assert(em_uart_send(&byte,1));assert(peripheral.USART.DATA.reg==byte);}
 printf("production wait boundary scenario %u PASS\n",scenario);
}
