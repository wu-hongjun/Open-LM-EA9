#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
extern int sent_n;
extern uint8_t sent[][256];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
static int armed, pending, irq_mask, mode;
static uint8_t incoming[17];
static void seal(uint8_t *p,unsigned n) {
 unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;
 for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
}
static void deliver(void) { if(pending && !irq_mask) {pending=0;host_body_frame(incoming,17);} }
uint32_t st_lock(void) {unsigned k=irq_mask;irq_mask=1;return k;}
void st_unlock(uint32_t k) {irq_mask=k;deliver();}
void integration_hook(int point) {if(armed && point==mode){armed=0;pending=1;deliver();}}
int main(int argc,char **argv) {
 if(argc!=3)return 2;mode=atoi(argv[1]);unsigned id=atoi(argv[2]);
 uint8_t request[11]={0};em_init();
 incoming[3]=2;incoming[4]=0x71;incoming[5]=id;seal(incoming,17);
 request[3]=2;request[5]=(mode==1?0x34:0x0a);request[6]=0x34;request[7]=0x12;seal(request,11);
 host_body_frame(request,11);armed=1;em_poll();
 int good=!em_handshake_done;
 if(mode==0)good=em_handshake_done && sent_n==1;
 if(mode==1 || mode==3 || mode==4)good=sent_n==0;
 if(mode==1 && id==0x19)good=sent_n==1 && sent[0][5]==0x34 && sent[0][7]==0x34 && sent[0][8]==0x12;
 printf("%s point=%d interrupt-id=%u hs=%u tx=%d epoch=%u\n",good?"PASS":"FAIL",mode,id,em_handshake_done,sent_n,(unsigned)em_session_generation());
 return !good;
}
