#include <stdint.h>
#include <stdio.h>
#include <setjmp.h>
#include <string.h>
#define SERCOM_USART_INTFLAG_TXC 2
#define ST_UART_WAIT 5
struct {struct {struct {uint32_t reg;struct {unsigned DRE,TXC;} bit;} INTFLAG;struct {uint32_t reg;} DATA;} USART;} hw;
#define EMSERCOM (&hw)
static uint8_t g_disabled;
static jmp_buf fault;
static unsigned fault_code;
#define ST_WAIT_WHILE(condition, code) do {unsigned budget=8;while(condition){if(!--budget){fault_code=code;longjmp(fault,1);}}}while(0)
#include "send_under_test.inc"
#define CHECK(x) do{if(!(x)){printf("FAIL:%d:%s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char **argv){
    if(argc!=2)return 2;
    uint8_t data[3]={3,7,11};hw.USART.INTFLAG.bit.DRE=1;hw.USART.INTFLAG.bit.TXC=1;
    if(!strcmp(argv[1],"disabled")){g_disabled=1;CHECK(em_uart_send(data,3)==0 && hw.USART.DATA.reg==0);}
    else if(!strcmp(argv[1],"success")){CHECK(em_uart_send(data,3)==1 && hw.USART.DATA.reg==11);}
    else {
        if(!strcmp(argv[1],"dre-timeout"))hw.USART.INTFLAG.bit.DRE=0;
        else hw.USART.INTFLAG.bit.TXC=0;
        if(!setjmp(fault)){em_uart_send(data,3);CHECK(0);}
        CHECK(fault_code==ST_UART_WAIT);
    }
    puts("PASS");return 0;
}
