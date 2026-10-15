#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define EM_RX_BUF_LEN 256
#define EM_RX_POISON_LEN 64
#define EM_RX_POISON 0xa5
#define SERCOM_USART_INTFLAG_ERROR 128
#define SERCOM_USART_INTENCLR_RXC 4
struct reg {uint32_t reg; struct {uint8_t RXC,ERROR;} bit;};
struct {struct {struct reg INTFLAG,DATA,STATUS,INTENCLR;} USART;} hw;
#define EMSERCOM (&hw)
static unsigned locked, deferred, inject_reset, reads, stuck;
void SERCOM1_Handler(void);
static uint32_t millis(void){return 42;}
static uint32_t st_lock(void){return locked++;}
static void st_unlock(uint32_t prior){locked=prior;if(!locked&&deferred){deferred=0;SERCOM1_Handler();}}
static uint8_t probe_data(void){++reads;if(!stuck)hw.USART.INTFLAG.bit.RXC=0;return 0x42;}
static void reset_probe(unsigned i){
    if(inject_reset&&i==32){hw.USART.INTFLAG.bit.RXC=1;if(locked)deferred=1;else SERCOM1_Handler();}
}
#include "uart_under_test.inc"
#define CHECK(x) do{if(!(x)){printf("FAIL:%d:%s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char **argv){
    if(argc!=2)return 2;
    if(!strcmp(argv[1],"reset")){
        inject_reset=1;em_uart_rx_reset();CHECK(em_uart_rx_len()==1 && em_uart_rx_buf()[0]==0x42);
    }else if(!strcmp(argv[1],"stuck")){
        stuck=1;hw.USART.INTFLAG.bit.RXC=1;SERCOM1_Handler();CHECK(reads==4);
        CHECK(hw.USART.INTENCLR.reg==SERCOM_USART_INTENCLR_RXC && em_uart_rx_len()==0);
        em_uart_rx_reset();CHECK(em_uart_rx_len()==0);
    }else if(!strcmp(argv[1],"error")){
        hw.USART.INTFLAG.bit.RXC=1;hw.USART.INTFLAG.bit.ERROR=1;hw.USART.STATUS.reg=5;
        SERCOM1_Handler();CHECK(em_uart_rx_len()==0 && em_rx_errors==1 && em_rx_status==5);
        hw.USART.INTFLAG.bit.ERROR=0;em_uart_rx_reset();hw.USART.INTFLAG.bit.RXC=1;SERCOM1_Handler();CHECK(em_uart_rx_len()==1);
    }else if(!strcmp(argv[1],"overflow")){
        for(unsigned i=0;i<257;++i){hw.USART.INTFLAG.bit.RXC=1;SERCOM1_Handler();}
        CHECK(em_uart_rx_len()==0);
    }else return 2;
    puts("PASS");return 0;
}
