#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "em_owner.h"
#include "em_shutdown.h"
#define EM_FRAME_END 0x55u
#define EM_PIN_BODY_CS 2
#define EM_PIN_LENS_CS 4
#define EM_CS_HOLD_US 100
#define ST_TX 4
struct { struct {struct {uint32_t reg;} OUTSET, OUTCLR;} Group[1]; } host_port;
#define PORT (&host_port)
static struct em_owner g_owner;
static struct em_shutdown g_shutdown;
static unsigned lock_depth, lock_calls, send_calls, tx_failed, pin, pending, inject;
static uint8_t source[256], captured[256];
static uint16_t captured_len;
static uint32_t em_frames_tx;
static volatile uint32_t em_cs_edges;
static uint32_t millis(void) { return 42; }
static void delay_us(uint32_t n) { (void)n; }
static void st_note(int a,int b,int c,int d,int e,int f,uint32_t g) { (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g; }
static uint32_t st_lock(void) {
    ++lock_calls;
    /* An EIC IRQ just before the final critical section is realistic. */
    if (inject && lock_calls == 1) {
        if(inject==1) pin=1;
        if(inject==2) pending=1;
        if(inject==3) {g_owner.phase=1;g_owner.interrupted=1;}
        if(inject==4) g_shutdown.state=EM_SD_PENDING;
        if(inject==5) {source[6]=0xe7;em_cs_edges++;}
    }
    return lock_depth++;
}
static void st_unlock(uint32_t prior) {lock_depth=prior;}
static int em_pin_level(uint8_t n) {(void)n;return pin;}
static int em_eic_receive_pending(void) {return pending;}
static uint8_t em_shutdown_requested(void) {return g_shutdown.state!=EM_SD_IDLE;}
static uint8_t em_uart_send(const uint8_t *b,uint16_t n) {
    if (lock_depth) {puts("MASKED UART SEND");exit(9);}
    if(tx_failed) return 0;
    ++send_calls;
    /* A higher-priority RX callback updates an outgoing aperture template. */
    source[6]=0xe7;
    memcpy(captured,b,n);captured_len=n;
    return 1;
}
static void *probe_memcpy(void *dst, const void *src, size_t n) {
    if(lock_depth){puts("MASKED COPY");exit(9);}
    size_t half=n/2;memcpy(dst,src,half);
    if(inject==6){source[6]=0xe7;em_cs_edges++;}
    memcpy((uint8_t *)dst+half,(const uint8_t *)src+half,n-half);return dst;
}
#define memcpy probe_memcpy
#include "tx_under_test.inc"
#undef memcpy
#define CHECK(x) do{if(!(x)){printf("FAIL:%d:%s\n",__LINE__,#x);return 1;}}while(0)
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    memset(source,0,256);source[0]=0xf0;source[3]=2;source[5]=0x28;source[6]=0x31;
    const char *test=argv[1];
    if(!strcmp(test,"high"))pin=1;
    else if(!strcmp(test,"pending"))pending=1;
    else if(!strcmp(test,"status")){g_owner.phase=1;g_owner.interrupted=1;}
    else if(!strcmp(test,"shutdown"))g_shutdown.state=EM_SD_PENDING;
    else if(!strcmp(test,"failed"))tx_failed=1;
    else if(!strcmp(test,"race-high"))inject=1;
    else if(!strcmp(test,"race-pending"))inject=2;
    else if(!strcmp(test,"race-status"))inject=3;
    else if(!strcmp(test,"race-shutdown"))inject=4;
    else if(!strcmp(test,"after-copy"))inject=5;
    else if(!strcmp(test,"during-copy"))inject=6;
    if(!strcmp(test,"ack")) {
        g_shutdown.state=EM_SD_ACTIVE;memcpy(g_shutdown.request,source,11);
        em_transmit(g_shutdown.request,11);
    } else if(!strcmp(test,"length"))em_transmit(source,256);
    else em_transmit(source,11);
    CHECK(lock_depth==0);
    if(pin||pending||inject||g_owner.phase||!strcmp(test,"shutdown")||tx_failed) {
        CHECK(send_calls==0 && em_frames_tx==0);
        if(!tx_failed)CHECK(host_port.Group[0].OUTSET.reg==0);
    } else {
        CHECK(send_calls==1 && em_frames_tx==1);
        CHECK(captured[6]==0x31);
        CHECK(captured_len==(!strcmp(test,"length")?256:11));
        CHECK(captured[2]==(captured_len>>8));
        uint16_t sum=0;for(unsigned i=1;i<captured_len-3u;++i)sum+=captured[i];
        CHECK(captured[captured_len-3]==(uint8_t)sum && captured[captured_len-2]==sum>>8);
    }
    puts("PASS");return 0;
}
