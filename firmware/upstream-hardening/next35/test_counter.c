#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "emount.h"
extern uint32_t host_millis;
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
static void boot(void) {
 uint8_t p[11]={0xf0,11,0,2,0x20,0x0a,0,0,0,0,0x55};uint16_t sum=0;
 for(unsigned i=1;i<8;i++)sum+=p[i];p[8]=sum;p[9]=sum>>8;
 em_init();host_body_frame(p,sizeof p);em_poll();assert(em_handshake_done);sent_n=0;
}
int main(int argc,char **argv) {
 assert(argc==2);int omitted=argv[1][0]=='1';boot();
 uint32_t prev=0;uint16_t expected=EM_FRAME_PERIOD_DEFAULT,count=0;
 static const uint32_t times[]={0,1,10,20,30,31,50,80,100,130,200,UINT32_MAX-20,UINT32_MAX-10,0,10,40,71};
 for(unsigned k=0;k<sizeof times/sizeof *times;k++) {
  uint32_t now=times[k];if(prev) {uint32_t dt=now-prev;if(dt>=EM_FRAME_PERIOD_MIN&&dt<=EM_FRAME_PERIOD_MAX){expected=(uint16_t)dt;count++;}}
  prev=now;host_millis=now;host_frame_sync();em_poll();assert(em_frame_period_ms==expected);
  assert(em_frame_period_n==(omitted?0:count));
  printf("PERIOD %u\n",expected);
 }
 for(int k=0;k<sent_n;k++) {printf("WIRE %u:",sent_len[k]);for(unsigned i=0;i<sent_len[k];i++)printf("%02x",sent[k][i]);putchar('\n');}
 printf("PASS periods=%zu statusFrames=%d\n",sizeof times/sizeof *times,sent_n);return 0;
}
