#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
#include "servo.h"
#include "startup_trace.h"
extern int sent_n, sent_overflow;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern uint32_t host_millis;
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
unsigned query_answers(void);
unsigned query_pending(void);
uint32_t millis(void);
static int g_aborted, g_homed, inhibited, mask;
static struct focus_pred g_pred;
static unsigned conversions, reports, samples, pumps, pump_depth, max_depth;
static unsigned reads, drives, active, inject, reply_while_active, homing_stream;
static uint8_t want_tag[32], got_tag[32];
static uint16_t want_val[32], got_val[32];
static unsigned want_n, got_n, observed;
uint8_t motor_is_inhibited(void) {return inhibited;}
void motor_inhibit(void) {inhibited=1;}
void motor_attach_pins(void) {}
void motor_drive(int16_t d) {(void)d;drives++;}
void motor_brake(void) {}
uint16_t abs_encoder_raw(void) {return 0;}
uint32_t st_lock(void) {unsigned k=mask;mask=1;return k;}
void st_unlock(uint32_t k) {mask=k;}
static void seal(uint8_t *p,unsigned n) {
 unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;
 for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
}
static void frame(unsigned cls,unsigned id) {
 uint8_t p[17]={0};unsigned n=id==1?17:11;
 p[3]=cls;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);
}
static void query(unsigned i) {
 uint8_t p[25]={0};uint8_t tag=(i&1)?EM_REC_Q_D2POS:EM_REC_Q_POS2D;
 uint16_t operand=(i&1)?(320+17*i):(4144+211*i);
 p[3]=1;p[4]=0x72;p[5]=4;p[19]=tag;p[20]=operand;p[21]=operand>>8;
 seal(p,sizeof p);host_body_frame(p,sizeof p);
 want_tag[want_n]=tag;
 want_val[want_n++]=tag==EM_REC_Q_POS2D?focus_distance_code(focus_em06_to_counts(operand),EM_FOCAL_MM10):focus_counts_to_em06(focus_counts_for_code(operand,EM_FOCAL_MM10));
}
static void collect(void) {
 for(;observed<(unsigned)sent_n;observed++) {
  uint8_t *p=sent[observed];unsigned n=sent_len[observed];
  assert(n>=9 && p[0]==0xf0 && p[1]==n && p[n-1]==0x55);
  unsigned sum=0;for(unsigned j=1;j<n-3;j++)sum+=p[j];
  assert(p[n-3]==(sum&255) && p[n-2]==(sum>>8));
  if(p[5]!=6)continue;
  assert(n<=EM06_LEN_MAX);
  printf("wire06=");for(unsigned j=0;j<n;j++)printf("%02x",p[j]);puts("");
  for(unsigned j=45;j<n-3;) {
   if(p[j]==EM_REC_Q_POS2D || p[j]==EM_REC_Q_D2POS) {
    assert(j+3<=n-3 && got_n<32);got_tag[got_n]=p[j];got_val[got_n++]=p[j+1]|p[j+2]<<8;j+=3;
    if(active)reply_while_active++;
   } else {assert(p[j]==EM_REC_DRIVE || p[j]==EM_REC_STOP);j+=p[j]==EM_REC_DRIVE?4:2;}
  }
 }
 assert(!sent_overflow);
}
static void compute_hook(void) {assert(!mask);conversions++;}
static void focus_report_at(int32_t pos) {(void)pos;reports++;}
static void vdd_track_sample(void) {
 samples++;collect();
 if(homing_stream && (samples==1 || samples==2)) {
  assert(!mask && !g_homed);unsigned begin=(samples-1)*4;
  for(unsigned i=begin;i<begin+4;i++)query(i);
 }
}
#include "worker.inc"
#include "pump.inc"
static void tick(void) {host_frame_sync();pump(0);assert(!mask);}
static void wire(void) {host_frame_sync();em_poll();collect();}
int32_t abs_encoder_track(void) {
 reads++;host_millis+=5;
 if(inject && reads==3){
  unsigned count=inject==2?4:2;for(unsigned i=0;i<count;i++)query(i);
  inject=inject==2?3:0;
 }
 if(inject==3 && reads==4){for(unsigned i=4;i<8;i++)query(i);inject=0;}
 host_frame_sync();return reads<=2?0:100;
}
static void finish(void) {
 assert(got_n==want_n);
 for(unsigned i=0;i<want_n;i++){assert(got_tag[i]==want_tag[i]);assert(got_val[i]==want_val[i]);}
 assert(!query_pending() && !query_answers() && !mask);
 printf("PASS answers=%u conversions=%u pumps=%u samples=%u reports=%u max_depth=%u active_replies=%u\n",got_n,conversions,pumps,samples,reports,max_depth,reply_while_active);
}
int main(int argc,char **argv) {
 assert(argc==2 || argc==3);int observe=argc==3;const char *mode=argv[1];
 em_init();frame(2,0x0a);em_poll();assert(em_handshake_done);sent_n=0;
 if(!strcmp(mode,"capacity") || !strcmp(mode,"refill") || !strcmp(mode,"event")) {
  for(unsigned i=0;i<4;i++)query(i);focus_answer_queries();assert(query_answers()==4);
  for(unsigned i=4;i<8;i++)query(i);assert(query_pending()==4);
  if(!strcmp(mode,"refill")){wire();assert(got_n==2 && query_answers()==2);}
  if(!strcmp(mode,"event"))em_post_event(EM_REC_DRIVE,1);
  focus_answer_queries();
  unsigned retained=!strcmp(mode,"refill")?2:4;
  printf("retention waiting=%u expected=%u conversions=%u\n",query_pending(),retained,conversions);fflush(stdout);
  if(!observe)assert(query_pending()==retained);
  for(unsigned i=0;i<8;i++){wire();focus_answer_queries();}
  if(observe) {
   unsigned expected=!strcmp(mode,"refill")?6:4;
   assert(got_n==expected && want_n==8 && conversions==8);
   for(unsigned i=0;i<got_n;i++){assert(got_tag[i]==want_tag[i]);assert(got_val[i]==want_val[i]);}
   assert(!query_pending() && !query_answers());
   printf("OBSERVED admitted=%u converted=%u delivered=%u lost=%u\n",want_n,conversions,got_n,want_n-got_n);
  } else finish();
 } else if(!strcmp(mode,"pump-backlog")) {
  g_homed=1;
  for(unsigned i=0;i<4;i++)query(i);focus_answer_queries();
  for(unsigned i=4;i<8;i++)query(i);
  for(unsigned i=0;i<5;i++)tick();
  assert(pumps==5 && samples==5 && max_depth==1);finish();
 } else if(!strcmp(mode,"pump-homed") || !strcmp(mode,"pump-unhomed")) {
  g_homed=!strcmp(mode,"pump-homed");query(0);query(1);tick();
  assert(pumps==1 && samples==1 && reports==(unsigned)g_homed && max_depth==1);
  finish();
 } else if(!strcmp(mode,"homing-stream")) {
  homing_stream=1;active=1;
  for(unsigned i=0;i<6;i++)tick();active=0;
  assert(!g_homed && !reports && max_depth==1 && reply_while_active==8);finish();
 } else if(!strcmp(mode,"servo") || !strcmp(mode,"servo-backlog")) {
  g_homed=1;active=1;inject=!strcmp(mode,"servo-backlog")?2:1;
  struct servo_cfg cfg={.stop_ms=30,.v_cruise=10000,.ff_div=40,.kp_div=50,.tau_ms=33,.v_arrive=500,.arrive_steps=2,.duty_max=1000,.tolerance=12,.noise=8,.timeout_ms=400,.stall_ms=300,.pump=pump};
  struct servo_result r;servo_move_rel(100,&cfg,&r);active=0;
  assert(r.outcome==SERVO_OK && drives && pumps>1 && max_depth==1);
  printf("servo outcome=%u reads=%u active_replies=%u\n",r.outcome,reads,reply_while_active);fflush(stdout);
  assert(reply_while_active==(!strcmp(mode,"servo-backlog")?8u:2u));finish();
 } else if(!strcmp(mode,"session") || !strcmp(mode,"shutdown")) {
  for(unsigned i=0;i<4;i++)query(i);focus_answer_queries();
  for(unsigned i=4;i<8;i++)query(i);
  frame(2,!strcmp(mode,"session")?1:0x16);
  if(!strcmp(mode,"session")) {
   assert(!query_answers() && !query_pending());em_poll();frame(2,0x0a);em_poll();assert(em_handshake_done);
   sent_n=0;want_n=0;query(8);focus_answer_queries();wire();finish();
  } else {
   unsigned c=conversions;tick();assert(em_shutdown_requested() && conversions==c && got_n==0);
   for(int i=0;i<sent_n;i++)assert(sent[i][5]!=6);puts("PASS shutdown suppresses queued work and status");
  }
 } else if(!strcmp(mode,"inhibited") || !strcmp(mode,"aborted") || !strcmp(mode,"unready")) {
  query(0);inhibited=!strcmp(mode,"inhibited");g_aborted=!strcmp(mode,"aborted");
  if(!strcmp(mode,"unready"))em_handshake_done=0;
  tick();assert(conversions==0 && query_pending()==1 && got_n==0);puts("PASS readiness guard");
 } else if(!strcmp(mode,"ordinary")) {
  query(0);query(1);focus_answer_queries();wire();finish();
 } else if(!strcmp(mode,"lock-full")) {
  for(unsigned i=0;i<4;i++)query(i);focus_answer_queries();query(4);
  uint8_t tag=0xa5;uint16_t operand=0xbeef;
  mask=1;unsigned took=em_take_query(&tag,&operand);assert(mask==1);mask=0;
  assert(!took && tag==0xa5 && operand==0xbeef && query_pending()==1);
  puts("PASS full answer queue preserves operand, pending query and nested mask");
 } else if(!strcmp(mode,"lock")) {
  uint8_t tag=0;uint16_t operand=0;mask=1;assert(!em_take_query(&tag,&operand));assert(mask==1);mask=0;puts("PASS nested mask retained");
 } else assert(0);
 return 0;
}
