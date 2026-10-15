#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "startup_trace.h"
#include "focus_map.h"
#include "focus_dist.h"
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
unsigned query_answers(void);
unsigned query_pending(void);
static int g_aborted, inhibited, mask, pending, cut, action, armed, conversions, replenished;
static int capture_arm;
static uint8_t query_tag = EM_REC_Q_POS2D;
static uint16_t query_operand = 5000;
int motor_is_inhibited(void) { return inhibited; }
static void seal(uint8_t *p,unsigned n) {
 unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;
 for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
}
static void frame(unsigned cls,unsigned id,unsigned n) {
 uint8_t p[32]={0};p[3]=cls;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);
}
static void query(void) {
 uint8_t p[25]={0};p[3]=1;p[4]=0x72;p[5]=4;
 p[19]=query_tag;p[20]=query_operand;p[21]=query_operand>>8;seal(p,sizeof p);host_body_frame(p,sizeof p);
}
static void deliver(void) {
 if(!pending || mask)return;
 pending=0;
 if(action==1)frame(2,1,17);
 if(action==2)frame(2,0x16,11);
 if(action==3)inhibited=1;
 if(action==4)g_aborted=1;
}
uint32_t st_lock(void) { unsigned k=mask;mask=1;return k; }
void st_unlock(uint32_t k) {mask=k;deliver();}
void query_cut(int point) {
 if(armed && cut==point){armed=0;pending=1;deliver();}
}
void query_compute_hook(void) {
 assert(!mask);conversions++;
 query_cut(2);
 if(action==5 && replenished<64){replenished++;query();}
}
void query_send_hook(const uint8_t *p) {
 if(capture_arm && p[5]==5){capture_arm=0;frame(2,1,17);}
}
#include "worker.inc"
static void wire(void) {
 host_frame_sync();em_poll();
 assert(sent_n>=2 && sent[sent_n-1][5]==6);
 unsigned i=sent_n-1;printf("wire06=");
 for(unsigned j=0;j<sent_len[i];j++)printf("%02x",sent[i][j]);puts("");
}
int main(int argc,char **argv) {
 assert(argc==5);action=atoi(argv[1]);cut=atoi(argv[2]);int fixed=atoi(argv[3]);int reverse=atoi(argv[4]);
 if(reverse){query_tag=EM_REC_Q_D2POS;query_operand=500;}
 em_init();frame(2,0x0a,11);em_poll();assert(em_handshake_done);sent_n=0;
 query();assert(query_pending()==1);unsigned epoch=em_session_generation();
 armed=action>0 && action<5;
 focus_answer_queries();
 unsigned answers=query_answers(),waiting=query_pending();
 printf("action=%d cut=%d fixed=%d reverse=%d conversions=%d answers=%u pending=%u epoch=%u readiness=%u\n",action,cut,fixed,reverse,conversions,answers,waiting,(unsigned)em_session_generation(),em_handshake_done);
 assert(!mask && !pending);
 if(action==0 || action==6){assert(answers==1 && conversions==1);}
 if(action==1){assert(em_session_generation()==epoch+1 && !em_handshake_done);assert(answers==(fixed?0u:1u));em_poll();frame(2,0x0a,11);em_poll();assert(em_handshake_done);}
 if(action>=2 && action<=4){assert(answers==(fixed?0u:1u));}
 if(action==5){assert(conversions==(fixed?EM_QUERY_Q:65));assert(waiting==(fixed?1u:0u));assert(answers==EM_QUERY_Q);}
 if(action==2){em_poll();assert(em_shutdown_acked);for(int i=0;i<sent_n;i++)assert(sent[i][5]!=6);puts("shutdown: stale queue state only, no status wire");}
 else if(action==3 || action==4){puts("inhibit/abort: queue state only; production main-loop status schedule not asserted");}
 else {
  if(action==6){capture_arm=1;host_frame_sync();em_poll();assert(!capture_arm && em_session_generation()==epoch && em_handshake_done);host_frame_sync();em_poll();frame(2,0x0a,11);em_poll();assert(em_session_generation()==epoch);}
  wire();unsigned n=sent_len[sent_n-1];
  if(action==1)assert(n==(fixed?48u:51u));
  if(action==0 || action==6){assert(n==51 && sent[sent_n-1][45]==query_tag);uint16_t expected=reverse?focus_counts_to_em06(focus_counts_for_code(query_operand,EM_FOCAL_MM10)):focus_distance_code(focus_em06_to_counts(query_operand),EM_FOCAL_MM10);assert(sent[sent_n-1][46]==(expected&255) && sent[sent_n-1][47]==(expected>>8));}
 }
 puts("PASS");return 0;
}
