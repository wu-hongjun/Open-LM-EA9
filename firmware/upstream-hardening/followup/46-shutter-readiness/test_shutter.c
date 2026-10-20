/* Synthetic records; exact foreground/home/query/focus-entry bodies are included. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "emount_packets.h"
#include "servo.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
#include "startup_trace.h"
#include "motion_trace.h"
extern uint32_t host_millis;
extern int sent_n,sent_overflow;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);void host_frame_sync(void);
uint32_t millis(void);unsigned query_pending(void),query_answers(void),host_fault(void),host_status(void);
static uint8_t g_homed,g_aborted,g_next_pending,inhibited,g_last_op,g_abort_pending,g_abort_by_stop;
static uint32_t g_next_session,g_focus_session;
static struct em_focus_cmd g_next;
static struct focus_pred g_pred;
static const struct servo_cfg STOCK={.dry=0};
static unsigned drives,brakes,releases,resets,reports,lock_depth,wire_queries,wire_stops,wire_moves,wire_status,wire_shutdown;
static unsigned g_stops_idle,g_focus_aborts,conversions,inject_action,raw_arm;
static int32_t position;
static unsigned expected_observed;
#ifndef EXPECT_HOME_TAIL
#define EXPECT_HOME_TAIL 0
#endif
uint32_t st_lock(void){unsigned old=lock_depth;lock_depth=1;return old;}
void st_unlock(uint32_t old){lock_depth=old;}
uint8_t motor_is_inhibited(void){return inhibited;}
void motor_inhibit(void){inhibited=1;}
void motor_emergency_release(void){releases++;}
void motor_attach_pins(void){assert(!inhibited);}
void motor_drive(int16_t d){assert(!inhibited);if(d){assert(d==-800);drives++;}}
void motor_brake(void){assert(!inhibited);brakes++;}
void abs_encoder_track_reset(void){resets++;}
int32_t abs_encoder_track(void){position+=7;return position;}
static void focus_report_at(int32_t p){(void)p;reports++;}
static void focus_report(void){reports++;}
static void __attribute__((unused)) vdd_track_reset(void){}
static void __attribute__((unused)) vdd_track_result(uint16_t *lo,uint16_t *hi){*lo=*hi=0;}
static void focus_scan(const struct em_focus_cmd *c){(void)c;assert(!"forbidden scan entry after home failure");}
static void focus_drive(const struct em_focus_cmd *c){(void)c;assert(!"forbidden drive entry after home failure");}
static int focus_cmd_target(const struct em_focus_cmd *c,int32_t *p){(void)c;(void)p;assert(!"forbidden target conversion after home failure");return 0;}
static uint8_t focus_run(int32_t p,uint16_t t,const struct servo_cfg *cfg){(void)p;(void)t;(void)cfg;assert(!"forbidden servo entry after home failure");return SERVO_ABORTED;}
static void seal(uint8_t *p,unsigned n){unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;}
static void frame(unsigned id){uint8_t p[25]={0};unsigned n=id==1?17:id==0x0a?25:11;p[3]=2;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);}
static void record(unsigned tag){uint8_t p[40]={0};unsigned length=tag==EM_REC_STOP?1:tag==EM_REC_MOVE?5:tag==EM_REC_SCAN?14:tag==EM_REC_DRIVE?8:3;unsigned n=22+length;p[3]=1;p[4]=0x72;p[5]=4;p[19]=tag;p[20]=0x88;p[21]=0x13;seal(p,n);host_body_frame(p,n);}
static void query(void){record(EM_REC_Q_POS2D);}
void send_hook(const uint8_t *p){if(raw_arm&&p[5]==5){raw_arm=0;frame(0x0a);}}
static void capture_wire(void){
 for(int i=0;i<sent_n;i++){
  uint8_t *p=sent[i];unsigned n=sent_len[i],sum=0;
  assert(n>=9&&p[0]==0xf0&&p[1]==n&&p[n-1]==0x55);
  for(unsigned j=1;j<n-3;j++)sum+=p[j];assert(p[n-3]==(sum&255)&&p[n-2]==(sum>>8));
  if(p[5]==0x16)wire_shutdown++;
  if(p[5]==6){wire_status++;for(unsigned j=45;j<n-3;){
   unsigned tag=p[j];
   if(tag==EM_REC_Q_POS2D){assert(j+3<=n-3);assert((unsigned)(p[j+1]|p[j+2]<<8)==focus_distance_code(focus_em06_to_counts(5000),EM_FOCAL_MM10));wire_queries++;j+=3;}
   else {assert(tag==EM_REC_STOP||tag==EM_REC_MOVE);assert(j+2<=n-3);if(tag==EM_REC_STOP){assert(p[j+1]==1);wire_stops++;}else wire_moves++;j+=2;}
  }}
 }
 assert(!sent_overflow);sent_n=0;
}
static void __attribute__((unused)) vdd_track_sample(void){}
static void compute_hook(void){assert(!lock_depth);conversions++;if(inject_action){unsigned id=inject_action;inject_action=0;frame(id);}}
#include "worker.inc"
#include "pump.inc"
#include "home.inc"
#include "focus_entry.inc"
#include "foreground.inc"
static void tick(void){host_millis++;host_frame_sync();foreground();capture_wire();}
static void safety(void){
 assert(!g_homed&&inhibited&&!resets&&!brakes&&drives==1&&!reports&&!wire_moves&&!lock_depth);
 const uint8_t *p=st_motion_data();for(unsigned i=0;i<112;i++)assert(p[i]==0);
 if(EXPECT_HOME_TAIL){assert(p[112]==0x39&&p[113]==ST_HOME_DRIVE);assert(p[115]==expected_observed);}
 else {for(unsigned i=112;i<ST_MOTION_BYTES;i++)assert(p[i]==0);}
 assert(host_fault()==ST_HOME_DRIVE);
}
int main(int argc,char **argv){
 assert(argc==2);const char *mode=argv[1];
 ea9_packets_init();em_init();frame(0x0a);em_poll();sent_n=0;
 em_set_shutdown_inhibit_handler(motion_shutdown_inhibit);
 home_service();capture_wire();assert(g_home_state==HOME_FAILED&&host_fault()==ST_HOME_DRIVE&&g_home_attempts==1);safety();
 if(!strcmp(mode,"failed-stop-retry")){
  record(EM_REC_STOP);tick();tick();assert(wire_stops==1);safety();
  unsigned after_stop=g_home_state;record(EM_REC_MOVE);tick();expected_observed=1;safety();
  printf("after_stop_state=%u home_attempts=%u drives=%u\n",after_stop,g_home_attempts,drives);fflush(stdout);
  assert(after_stop==HOME_CANCELLED&&g_home_attempts==2&&g_home_state==HOME_FAILED);
 }else{
  if(strcmp(mode,"no-motion")){
   unsigned tags[]={EM_REC_MOVE,EM_REC_SCAN,EM_REC_DRIVE};
   for(unsigned i=0;i<3;i++){record(tags[i]);tick();expected_observed++;assert(!em_focus_pending&&g_next_pending);safety();}
  }
  if(!strcmp(mode,"observe-command"))assert(st_motion_data()[115]==3);
  if(!strcmp(mode,"saturating")){
   for(unsigned i=3;i<270;i++){record(EM_REC_MOVE);tick();if(expected_observed<255)expected_observed++;safety();}
  }
  if(!strcmp(mode,"uninitialized-tail")){
   uint8_t *tail=(uint8_t *)(void *)st_motion_data()+112;tail[0]=0;
   record(EM_REC_MOVE);tick();assert(tail[3]==3);tail[0]=0x39;safety();
  }
  if(!strcmp(mode,"no-inhibit-tail")){
   inhibited=0;record(EM_REC_MOVE);assert(home_command());assert(st_motion_data()[115]==3);inhibited=1;safety();
  }
  query();tick();assert(wire_queries==1&&!query_pending()&&!query_answers());safety();
  if(!strcmp(mode,"raw-readiness")){
   for(unsigned cycle=0;cycle<3;cycle++){
    raw_arm=1;tick();assert(!raw_arm);tick();assert(!host_status());
    record(EM_REC_MOVE);tick();expected_observed++;safety();
    unsigned statuses=wire_status;query();for(unsigned i=0;i<4;i++)tick();assert(wire_status==statuses&&query_answers()==1);
    frame(0x0a);em_poll();capture_wire();tick();assert(host_status()&&wire_queries==cycle+2&&!query_answers());safety();
   }
  }
  if(!strcmp(mode,"session-cut")){
   query();inject_action=1;tick();assert(!em_handshake_done&&!query_pending()&&!query_answers());
   frame(0x0a);em_poll();capture_wire();tick();assert(wire_queries==1);safety();
  }
  if(!strcmp(mode,"shutdown-cut")){query();inject_action=0x16;tick();}
  else {frame(0x16);tick();}
  assert(em_shutdown_requested()&&em_shutdown_acked&&wire_shutdown==1);safety();
 }
 printf("PASS %s queries=%u status=%u stops=%u moves=%u conversions=%u\n",mode,wire_queries,wire_status,wire_stops,wire_moves,conversions);
 return 0;
}
