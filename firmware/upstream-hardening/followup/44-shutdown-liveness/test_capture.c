/* Exact emount/frame/owner/shutdown source; synthetic UART and EIC boundaries. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "emount_packets.h"
#include "startup_trace.h"
extern int sent_n, sent_overflow;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
unsigned probe_status(void),probe_retry(void),probe_pending(void);
static unsigned mask, capture, action, inhibited, powerdowns, injected;
static uint32_t epoch;
uint32_t st_lock(void){unsigned old=mask;mask=1;return old;}
void st_unlock(uint32_t k){mask=k;}
static void seal(uint8_t *p,unsigned n){unsigned sum=0;p[0]=0xf0;p[1]=n;p[n-1]=0x55;for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;}
static void frame(unsigned id){uint8_t p[17]={0};unsigned n=id==1?17:11;p[3]=2;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);}
static void inhibit(void){inhibited++;}
static void powerdown(void){assert(!mask && inhibited && em_shutdown_acked);powerdowns++;}
void send_hook(const uint8_t *p){
 assert(!mask);
 if(capture && p[5]==5){capture=0;frame(1);}
 else if(action && p[5]==1){unsigned a=action;action=0;injected++;frame(a==1?1:a==2?0x16:0x0a);}
}
int main(int argc,char **argv){
 assert(argc==2);unsigned scenario=(unsigned)atoi(argv[1]);st_init();ea9_packets_init();em_init();
 em_set_shutdown_inhibit_handler(inhibit);em_set_powerdown_handler(powerdown);
 frame(0x0a);em_poll();assert(em_handshake_done && probe_status());epoch=em_session_generation();
 /* Status begins; CS interrupts its first UART call with an init-class raw request. */
 capture=1;host_frame_sync();em_poll();assert(!capture && probe_pending());
 assert(em_session_generation()==epoch && em_handshake_done);
 int before=sent_n;em_poll();assert(sent_n==before); /* raw requires VD */
 if(scenario<=3)action=scenario;
 host_frame_sync();em_poll();assert(sent_n==before+1 && sent[before][5]==1);
 assert(!probe_retry() && !probe_status());
 if(scenario==1){assert(injected==1 && em_session_generation()==epoch+1 && !em_handshake_done);em_poll();}
 else assert(em_session_generation()==epoch);
 if(scenario==2){assert(injected==1 && inhibited==1 && em_shutdown_requested());}
 else {
  /* Additional VD pulses alone do not restart status after raw completion. */
  if(scenario!=3){before=sent_n;for(unsigned i=0;i<4;i++){host_frame_sync();em_poll();}assert(sent_n==before);}
  /* Ordinary readiness after capture restores status in the same session. */
  if(scenario!=3)frame(0x0a);
  em_poll();assert(em_handshake_done && probe_status());
  before=sent_n;host_frame_sync();em_poll();assert(sent_n==before+2 && sent[before][5]==5 && sent[before+1][5]==6);
  frame(0x16);assert(inhibited==1 && !em_handshake_done && !probe_status() && !probe_pending());
 }
 before=sent_n;em_poll();assert(sent_n==before+1 && sent[before][5]==0x16 && powerdowns==1);
 for(unsigned i=0;i<4;i++){frame(1);frame(0x0a);frame(0x16);host_frame_sync();em_poll();}
 assert(sent_n==before+1 && powerdowns==1 && inhibited==1 && !probe_retry());
 assert(!sent_overflow && !mask);
 for(int i=0;i<sent_n;i++){unsigned sum=0,n=sent_len[i];for(unsigned j=1;j<n-3;j++)sum+=sent[i][j];assert(sent[i][n-1]==0x55 && sent[i][n-3]==(sum&255) && sent[i][n-2]==(sum>>8));}
 printf("capture/shutdown scenario %u PASS (synthetic UART completion, no camera acceptance)\n",scenario);
}
