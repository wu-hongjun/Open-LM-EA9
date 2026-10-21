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
static void pump(int32_t);static uint8_t focus_abort(void),focus_retarget(int32_t *);
static void focus_report_at(int32_t),focus_report(void),focus_answer_queries(void);
static int32_t g_last_reported;static uint16_t g_last_target;
#include "stock.inc"
static unsigned servo_calls,drive_at,drive_active,cut_at,clock_action,clock_trigger;
static unsigned still_after=0;static int servo_active;static int16_t duty;
static int32_t servo_target;static unsigned stale_session;
static void frame(unsigned),record(unsigned);
static unsigned drives,brakes,releases,resets,lock_depth,wire_queries,wire_stops,wire_moves,wire_status,wire_shutdown;
static unsigned g_stops_idle,g_focus_aborts,raw_arm;
static int32_t position;
static unsigned last_now,last_ahead,last_flags,last_dir;

#ifndef EXPECT_HOME_TAIL
#define EXPECT_HOME_TAIL 0
#endif
uint32_t st_lock(void){unsigned old=lock_depth;lock_depth=1;return old;}
void st_unlock(uint32_t old){lock_depth=old;}
uint8_t motor_is_inhibited(void){return inhibited;}
void motor_inhibit(void){inhibited=1;}
void motor_emergency_release(void){releases++;duty=0;if(drive_active){drive_active=0;cut_at=host_millis;}}
void motor_home_release(void){motor_emergency_release();}
void motor_attach_pins(void){assert(!inhibited);}
void motor_drive(int16_t d){assert(!inhibited);duty=d;if(!servo_active&&d){assert(d==-800);drives++;drive_at=host_millis;drive_active=1;}if(!servo_active&&!d&&drive_active){drive_active=0;cut_at=host_millis;}}
void motor_brake(void){assert(!inhibited);brakes++;}
void abs_encoder_track_reset(void){resets++;position=0;}
int32_t abs_encoder_track(void){
 if(resets&&!servo_active&&stale_session){stale_session=0;frame(1);em_poll();frame(0x0a);em_poll();}
 if(resets&&!servo_active)return position;
 if(servo_active){if(duty>0&&position<servo_target){position+=8;if(position>servo_target)position=servo_target;}return position;}
 if(drives){unsigned elapsed=host_millis-drive_at;position=-(int32_t)(elapsed<still_after?elapsed:still_after)*10;}
 return position;
}
uint16_t abs_encoder_raw(void){return (uint16_t)position;}
void servo_start(int32_t start,int32_t target){assert(resets==1);assert(start==0);assert(g_homed&&!inhibited);assert(target==224);assert(g_last_reported==0);assert((ea9_data[EA9_OFF_06+26]|ea9_data[EA9_OFF_06+27]<<8)==FOCUS_EM06_LO);servo_calls++;servo_active=1;servo_target=target;}
static void focus_scan(const struct em_focus_cmd *c){(void)c;assert(0);}
static void focus_drive(const struct em_focus_cmd *c){(void)c;assert(0);}
void clock_hook(void){if(clock_action&&host_millis>=clock_trigger){unsigned action=clock_action;clock_action=0;if(action==2)record(EM_REC_STOP);else frame(action);}}
static void seal(uint8_t *p,unsigned n){unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;}
static void frame(unsigned id){uint8_t p[25]={0};unsigned n=id==1?17:id==0x0a?25:11;p[3]=2;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);}
static void record(unsigned tag){uint8_t p[40]={0};unsigned length=tag==EM_REC_STOP?1:tag==EM_REC_MOVE?5:tag==EM_REC_SCAN?14:tag==EM_REC_DRIVE?8:3;unsigned n=22+length;p[3]=1;p[4]=0x72;p[5]=4;p[19]=tag;p[20]=tag==EM_REC_MOVE?0x68:0x88;p[21]=tag==EM_REC_MOVE?0x10:0x13;seal(p,n);host_body_frame(p,n);}
static void query(void){record(EM_REC_Q_POS2D);}
void send_hook(const uint8_t *p){if(raw_arm&&p[5]==5){raw_arm=0;frame(0x0a);}}
static void capture_wire(void){
 for(int i=0;i<sent_n;i++){
  uint8_t *p=sent[i];unsigned n=sent_len[i],sum=0;
  assert(n>=9&&p[0]==0xf0&&p[1]==n&&p[n-1]==0x55);
  for(unsigned j=1;j<n-3;j++)sum+=p[j];assert(p[n-3]==(sum&255)&&p[n-2]==(sum>>8));
  if(p[5]==0x16)wire_shutdown++;
  if(p[5]==6){wire_status++;last_now=p[26]|p[27]<<8;last_ahead=p[8]|p[9]<<8;last_flags=p[6];last_dir=p[7];for(unsigned j=45;j<n-3;){
   unsigned tag=p[j];
   if(tag==EM_REC_Q_POS2D){assert(j+3<=n-3);assert((unsigned)(p[j+1]|p[j+2]<<8)==focus_distance_code(focus_em06_to_counts(5000),EM_FOCAL_MM10));wire_queries++;j+=3;}
   else {assert(tag==EM_REC_STOP||tag==EM_REC_MOVE);assert(j+2<=n-3);if(tag==EM_REC_STOP){assert(p[j+1]==1);wire_stops++;}else wire_moves++;j+=2;}
  }}
 }
 assert(!sent_overflow);sent_n=0;
}
#include "encoder.inc"
#include "focus.inc"
#include "home.inc"
#include "foreground.inc"
static void tick(void){host_millis++;host_frame_sync();foreground();capture_wire();}
int main(int argc,char **argv){
 assert(argc==2);const char *mode=argv[1];
 ea9_packets_init();em_init();frame(0x0a);em_poll();sent_n=0;
 em_set_shutdown_inhibit_handler(motion_shutdown_inhibit);
 if(!strcmp(mode,"stale-session"))stale_session=1;
 if(!strcmp(mode,"late"))still_after=280;
 if(!strcmp(mode,"failed"))still_after=10000;
 record(EM_REC_MOVE);
 if(!strcmp(mode,"session")){clock_action=1;clock_trigger=host_millis+25;}
 if(!strcmp(mode,"stop")){clock_action=2;clock_trigger=host_millis+25;}
 if(!strcmp(mode,"shutdown")){clock_action=0x16;clock_trigger=host_millis+25;}
 tick();
 if(!strcmp(mode,"session")||!strcmp(mode,"stop")||!strcmp(mode,"shutdown")){
  assert(servo_calls==0&&!g_homed&&!wire_moves);assert(!resets);
  if(!strcmp(mode,"shutdown")){em_poll();capture_wire();assert(em_shutdown_requested()&&wire_shutdown==1);}
  if(!strcmp(mode,"stop")){tick();assert(wire_stops==1);}
  puts("PASS cancellation before readiness");return 0;
 }
 if(!strcmp(mode,"stale-session")){assert(servo_calls==0);assert(g_homed&&!g_next_pending&&!wire_moves);puts("PASS stale session discarded after home");return 0;}
 if(!strcmp(mode,"failed")){
  assert(!g_homed&&inhibited&&!servo_calls&&!wire_moves&&!resets);
  query();tick();assert(wire_queries==1);
  record(EM_REC_MOVE);tick();assert(!servo_calls&&!wire_moves);assert(st_motion_data()[115]==1);
  for(unsigned i=0;i<112;i++)assert(st_motion_data()[i]==0);
  frame(0x16);tick();assert(wire_shutdown==1);puts("PASS failed home closed; query/shutdown live");return 0;
 }
 assert(g_homed&&g_home_state==HOME_READY&&!inhibited);assert(resets==1);assert(servo_calls==1);assert(!g_next_pending);
 tick();assert(servo_calls==1);assert(wire_moves==1);assert(position>=212&&position<=224);
 /* Real report functions publish origin-relative actual and forecast at rest. */
 assert(last_now==focus_counts_to_em06(position)&&last_ahead==last_now);
 assert((last_flags&0x82)==0x82&&last_dir==0);
 if(!strcmp(mode,"late"))assert(cut_at-drive_at==300);

 for(unsigned cycle=0;cycle<3;cycle++){
  raw_arm=1;tick();assert(!raw_arm);tick();assert(!host_status());
  unsigned statuses=wire_status;query();for(unsigned i=0;i<4;i++)tick();assert(wire_status==statuses&&query_answers()==1);
  frame(0x0a);em_poll();capture_wire();tick();assert(host_status()&&wire_queries==cycle+1&&!query_answers());
 }
 record(EM_REC_STOP);tick();tick();assert(wire_stops==1&&servo_calls==1);
 frame(0x16);tick();assert(em_shutdown_requested()&&em_shutdown_acked&&wire_shutdown==1);
 printf("PASS %s servo=%u completed=%u origin=%u status=%u shutdown=%u driveCut=%u\n",mode,servo_calls,wire_moves,resets,wire_status,wire_shutdown,cut_at-drive_at);
 return 0;
}
