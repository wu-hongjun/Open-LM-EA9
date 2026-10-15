#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "abs_encoder.h"
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
static uint32_t g_focus_session;
static uint8_t g_abort_pending;
static struct focus_pred g_pred;
static unsigned conversions,reports,samples,reads,raw,query_at,fault_at,capture_arm,action;
static int32_t g_track;
static uint16_t g_track_last;
uint8_t motor_is_inhibited(void) {return inhibited;}
void motor_inhibit(void) {inhibited=1;}
void motor_attach_pins(void) {}
void motor_drive(int16_t d) {(void)d;}
void motor_brake(void) {}
uint32_t st_lock(void) {unsigned k=mask;mask=1;return k;}
void st_unlock(uint32_t k) {mask=k;}
static void seal(uint8_t *p,unsigned n) {
 unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;
 for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
}
static void frame(unsigned id) {
 uint8_t p[17]={0};unsigned n=id==1?17:11;
 p[3]=2;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);
}
static void query(void) {
 uint8_t p[25]={0};p[3]=1;p[4]=0x72;p[5]=4;
 p[19]=EM_REC_Q_POS2D;p[20]=5000&255;p[21]=5000>>8;
 seal(p,sizeof p);host_body_frame(p,sizeof p);
}
static void compute_hook(void) {
 assert(!mask);conversions++;
 if(action){unsigned id=action;action=0;frame(id);}
}
void send_hook(const uint8_t *p) {
 if(capture_arm && p[5]==5){capture_arm=0;frame(1);}
}
static void focus_report_at(int32_t pos) {assert(pos>=-ENC_TRACK_LIMIT && pos<=ENC_TRACK_LIMIT);reports++;}
static void vdd_track_sample(void) {samples++;}
uint16_t abs_encoder_raw(void) {
 reads++;host_millis+=5;
 if(reads==query_at)query();
 if(reads==fault_at)raw=1;
 host_frame_sync();return raw;
}
#include "tracker.inc"
#include "worker.inc"
#include "pump.inc"
#include "abort.inc"
static unsigned wire_answers(void) {
 unsigned total=0;
 for(int i=0;i<sent_n;i++){
  uint8_t *p=sent[i];unsigned n=sent_len[i],sum=0;
  assert(n>=9 && p[0]==0xf0 && p[1]==n && p[n-1]==0x55);
  for(unsigned j=1;j<n-3;j++)sum+=p[j];assert(p[n-3]==(sum&255) && p[n-2]==(sum>>8));
  if(p[5]!=6)continue;
  assert(n==48 || n==51);
  if(n==51){assert(p[45]==EM_REC_Q_POS2D);uint16_t value=p[46]|p[47]<<8;assert(value==focus_distance_code(focus_em06_to_counts(5000),EM_FOCAL_MM10));total++;}
 }
 assert(!sent_overflow);return total;
}
int main(int argc,char **argv) {
 assert(argc==2);const char *mode=argv[1];
 em_init();frame(0x0a);em_poll();assert(em_handshake_done);sent_n=0;
 unsigned epoch=em_session_generation();g_focus_session=epoch;
 if(!strncmp(mode,"pump-",5)){
  g_homed=strstr(mode,"unhomed")==0;
  action=strstr(mode,"shutdown")?0x16:1;query();
  host_frame_sync();pump(0);
  assert(conversions==1 && !query_answers() && !query_pending() && !mask && wire_answers()==0);
  assert(reports==(unsigned)g_homed);
  if(strstr(mode,"shutdown")){assert(em_shutdown_requested());for(int i=0;i<sent_n;i++)assert(sent[i][5]!=6);}
  else {assert(em_session_generation()==epoch+1 && !em_handshake_done);frame(0x0a);em_poll();host_frame_sync();pump(0);assert(wire_answers()==0);}
 } else if(!strcmp(mode,"capture")){
  query();capture_arm=1;host_frame_sync();pump(0);
  assert(!capture_arm && em_session_generation()==epoch && em_handshake_done);
  host_frame_sync();pump(0);frame(0x0a);em_poll();host_frame_sync();pump(0);
  assert(wire_answers()==1 && !query_answers() && !query_pending());
 } else {
  g_homed=1;
  struct servo_cfg cfg={.stop_ms=30,.v_cruise=10000,.ff_div=40,.kp_div=50,.tau_ms=26,.v_arrive=500,.arrive_steps=2,.duty_max=1280,.tolerance=12,.noise=8,.timeout_ms=400,.stall_ms=300,.pump=pump,.abort=focus_abort};
  if(!strncmp(mode,"servo-coordinate",16)){
   /* Reach inclusive upper boundary through actual tracker calls. */
   for(unsigned i=0;i<8;i++){raw=(i&1)?0:8192;assert(abs_encoder_track()==(int32_t)((i+1)*8192));}
   reads=0;raw=0;fault_at=strstr(mode,"final")?5:3;query_at=fault_at;
  } else {action=strstr(mode,"shutdown")?0x16:1;query_at=3;}
  struct servo_result r;servo_move_rel(0,&cfg,&r);
  assert(r.outcome==SERVO_ABORTED && !mask && wire_answers()==0);
  if(!strncmp(mode,"servo-coordinate",16)){
   assert(inhibited && r.end==ENC_TRACK_LIMIT && conversions==0 && query_pending()==1 && !query_answers());
   assert(reads==(strstr(mode,"final")?5u:4u));
  }else{assert(conversions==1 && !query_answers() && !query_pending());}
  printf("servo outcome=%u reads=%u end=%d ",r.outcome,reads,r.end);
 }
 printf("PASS %s conversions=%u reports=%u pumps=%u answers=%u epoch=%u\n",mode,conversions,reports,samples,wire_answers(),(unsigned)em_session_generation());
 return 0;
}
