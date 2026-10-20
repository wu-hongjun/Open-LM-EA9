#include <assert.h>
#include <stdint.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "board.h"
#include "clock.h"
#include "startup_trace.h"
#undef st_note
struct adc_regs fake_adc;
uint32_t fake_fuse;
static jmp_buf failed;
static unsigned fault, conversions, polls, answers, ack, stage_adc, motors, encoders, releases;
static unsigned blocked, pending, inhibited;
static uint8_t g_homed;
static int g_pred;
uint32_t millis(void){return 0;}
void st_fail(uint8_t reason){fault=reason;fprintf(stderr,"production ADC fail-stop=%u\n",fault);longjmp(failed,1);}
void clock_enable_peripheral(uint8_t id,uint32_t mask){(void)id;(void)mask;}
void host_adc_start(void){conversions++;fake_adc.INTFLAG.reg=blocked?0:1;fake_adc.RESULT.reg=3000;}
static void focus_pred_sample(void *p,int32_t at,uint32_t ms){(void)p;(void)at;(void)ms;}
static void focus_report_at(int32_t at){(void)at;}
static void focus_answer_queries(void){answers++;}
static void em_poll(void){polls++;if(pending){ack++;pending=0;}if(polls==1){pending=1;inhibited=1;}}
static void abs_encoder_init(void){encoders++;}
static void motor_init(void){motors++;}
static void motor_release(void){releases++;}
void st_note(uint8_t kind,uint8_t id,uint8_t a,uint8_t b,uint16_t c,uint16_t d,uint32_t ms){(void)kind;(void)a;(void)b;(void)c;(void)d;(void)ms;if(id==ST_ADC)stage_adc++;}
#include "vdd.h"
#include "pump.inc"
static void startup(void){
#include "startup.inc"
}
#define CHECK(x) do{if(!(x)){fprintf(stderr,"FAIL: %s fault=%u adc=%u polls=%u answers=%u ack=%u motors=%u encoders=%u\n",#x,fault,conversions,polls,answers,ack,motors,encoders);return 1;}}while(0)
int main(int argc,char **argv){
 assert(argc==2);const char *mode=argv[1];
 if(!strcmp(mode,"healthy")){
  startup();pump(0);pump(0);CHECK(!fault&&ack==1&&answers==2&&polls==2&&motors==1&&encoders==1&&releases==1);
  #ifdef FIXED_RELEASE
  CHECK(!conversions&&!stage_adc);
  #else
  CHECK(conversions==10&&stage_adc==1);
  #endif
 }else if(!strcmp(mode,"stalled-capture")){
  blocked=1;
  if(!setjmp(failed)){pump(0);pump(0);}
  CHECK(!fault&&ack==1&&answers==2&&polls==2&&inhibited);
 }else if(!strcmp(mode,"stalled-startup")){
  blocked=1;
  if(!setjmp(failed))startup();
  CHECK(!fault&&motors==1&&encoders==1&&releases==1);
 }else return 2;
 printf("case=%s adc=%u adcstage=%u polls=%u queries=%u ack=%u fault=%u motors=%u\n",mode,conversions,stage_adc,polls,answers,ack,fault,motors);
 (void)g_homed;(void)g_pred;return 0;
}
