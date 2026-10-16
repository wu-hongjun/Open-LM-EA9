#include <assert.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#define STARTUP_TRACE_IMPLEMENTATION
#include "startup_trace.h"
static jmp_buf stop;
static uint32_t now,g_pa23_at;
static int disabled,mode,tail_block,n,flushes;
static unsigned char order[8];
static uint32_t em_rx_bytes;
static uint16_t em_rx_errors,em_rx_status;
struct reg { uint32_t reg; };
static struct {struct {struct reg OUTSET;} Group[1];} port;
#define PORT (&port)
#define DIAG_MARK_SHUTREQ 1
#define DIAG_MARK_PA23 2
#define EM_PIN_BODY_CS 1
#define EM_PIN_BODY_VD 2
static void diag_tally_mark(int a,int b){(void)a;(void)b;}
static uint32_t millis(void){return now;}
static void delay_ms(unsigned ms){if(ms==100&&tail_block)longjmp(stop,1);now+=ms;}
static int em_pin_level(unsigned pin){return pin==EM_PIN_BODY_VD&&(mode==1||(mode==2&&now<550));}
static void em_uart_disable(void){assert(!disabled);disabled=1;}
void st_note(uint8_t kind,uint8_t id,uint8_t cls,uint8_t seq,uint16_t length,uint16_t operand,uint32_t ms){
    (void)id;(void)cls;(void)seq;(void)length;(void)operand;(void)ms;assert(kind==ST_SHUTDOWN&&disabled);
}
void st_flush(int allowed,uint32_t ms,uint32_t bytes,uint16_t errors,uint16_t status,uint8_t pins){
    (void)ms;(void)bytes;(void)errors;(void)status;(void)pins;assert(allowed&&disabled&&!PORT->Group[0].OUTSET.reg);flushes++;
}
void st_terminal(uint8_t kind,uint8_t value,uint32_t ms){
    assert(disabled&&flushes==1&&ms==now);order[n++]=kind;
    if(kind==ST_VD_LOW){assert(value==2&&now==52&&!PORT->Group[0].OUTSET.reg);}
    if(kind==ST_VD_TIMEOUT){assert(value==(mode==2?1:0)&&now==550&&!PORT->Group[0].OUTSET.reg);}
    if(kind==ST_PA23){assert(PORT->Group[0].OUTSET.reg==(1u<<23)&&g_pa23_at==now);}
    if(kind==ST_TAIL_DONE){assert(now-g_pa23_at==100);}
}
/* EXTRACTED_PRODUCTION_FUNCTION */
int main(void){
    for(mode=0;mode<=2;mode++)for(tail_block=0;tail_block<=1;tail_block++){
        now=g_pa23_at=disabled=n=flushes=0;PORT->Group[0].OUTSET.reg=0;
        if(!setjmp(stop))powerdown_signal();
        assert(n==(tail_block?2:3));assert(order[0]==(mode?ST_VD_TIMEOUT:ST_VD_LOW));assert(order[1]==ST_PA23);
        if(!tail_block)assert(order[2]==ST_TAIL_DONE);
    }
    puts("production tail: VD two-low/500ms timeout, PA23, 100ms completion, cut-before-delay-return PASS");
}
