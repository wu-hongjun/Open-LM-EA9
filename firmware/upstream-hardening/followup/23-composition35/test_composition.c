#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "abs_encoder.h"
#include "motor.h"
#include "servo.h"
#include "startup_trace.h"
#include "focus_pred.h"
#include "focus_map.h"
#include "focus_dist.h"
extern uint32_t host_millis;
extern unsigned char sent[][256];
extern uint16_t sent_len[];
extern int sent_n, sent_overflow;
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
uint32_t millis(void);
unsigned test_events(void),query_answers(void),query_pending(void),test_fault(void),test_scan(void);
static const char *mode;
static int g_aborted,g_homed,g_next_pending,inhibited;
static uint8_t g_abort_pending,g_abort_by_stop,g_home_attempts,g_last_op;
static uint16_t g_last_target,g_stops_idle,g_focus_aborts;
static uint32_t g_focus_session,g_next_session,g_home_session;
static int32_t g_last_reported;
static struct em_focus_cmd g_next;
static struct focus_pred g_pred;
static enum home_state {HOME_UNTRIED,HOME_ACTIVE,HOME_READY,HOME_CANCELLED,HOME_FAILED} g_home_state;
static int32_t g_track;
static uint16_t g_track_last;
static unsigned raw,reads,resets,pumps,conversions,brakes,drives,mask,injected;
static unsigned actual_phase,in_home,priming,moving,idle_reads,active_reads,capture_arm,cut_sent;
static uint32_t phase_start,injected_elapsed,epoch;
static int32_t expected_target,pump_vel,pump_ahead;
static unsigned observed_n,deadband_hits;
static struct servo_result observed;
static void pump(int32_t pos);
static uint8_t focus_abort(void);
static uint8_t focus_retarget(int32_t *target);
#include "config.inc"
static int has(const char *s){return strstr(mode,s)!=0;}
uint32_t st_lock(void){unsigned old=mask;mask=1;return old;}
void st_unlock(uint32_t k){mask=k;}
uint8_t motor_is_inhibited(void){return inhibited;}
void motor_inhibit(void){inhibited=1;}
void motor_emergency_release(void){}
void motor_attach_pins(void){}
void motor_drive(int16_t d){if(d && !inhibited)drives++;}
void motor_brake(void){brakes++;actual_phase=1;phase_start=host_millis;}
static void vdd_track_reset(void){}
static void vdd_track_result(uint16_t *lo,uint16_t *hi){*lo=*hi=0;}
static void observe(const struct servo_result *r){observed=*r;observed_n++;}
static void seal(uint8_t *p,unsigned n){
 unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;
 for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
}
static void frame(unsigned id){uint8_t p[17]={0};unsigned n=id==1?17:11;p[3]=2;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);}
static void command(unsigned kind,uint16_t operand,int stop){
 uint8_t p[27]={0};unsigned n=stop?23:27;p[3]=1;p[4]=0x72;p[5]=4;
 p[19]=stop?EM_REC_STOP:EM_REC_MOVE;p[20]=operand;p[21]=operand>>8;p[23]=kind;
 seal(p,n);host_body_frame(p,n);
}
static void query(void){
 uint8_t p[25]={0};p[3]=1;p[4]=0x72;p[5]=4;p[19]=EM_REC_Q_POS2D;p[20]=5000&255;p[21]=5000>>8;
 seal(p,sizeof p);host_body_frame(p,sizeof p);
}
static void action(void){
 if(has("inhibit"))motor_inhibit();
 else if(has("session"))frame(1);
 else if(has("shutdown"))frame(0x16);
 else if(has("stop"))command(0,0,1);
 else if(has("fault"))raw=1;
 else if(has("relative"))command(4,100,0);
 else if(has("defocus"))command(6,10,0);
 else command(0,focus_counts_to_em06(1000),0);
}
static unsigned cut_phase(void){return has("settle");}
static void inject_deadline(void){
 unsigned cap=actual_phase?HOME_SETTLE_MS:HOME_MS;if(has("before"))cap--;
 host_millis=phase_start+cap;injected=1;injected_elapsed=cap;
 if(!has("capture"))action();
}
static void compute_hook(void){
 assert(!mask);conversions++;
 if(in_home && has("pump-") && !injected && actual_phase==cut_phase())inject_deadline();
 if(!in_home && has("query-") && !injected){injected=1;cut_sent=sent_n;action();}
}
void send_hook(const uint8_t *p){if(capture_arm && p[5]==5){capture_arm=0;frame(1);}}
static void vdd_track_sample(void){
 pumps++;pump_vel=g_pred.vel_q8;pump_ahead=focus_pred_ahead(&g_pred,g_track,em_frame_period_ms);
 if(in_home){
  if(!injected || actual_phase!=cut_phase())host_millis+=10;
  if(!injected && actual_phase==cut_phase() && has("pump-"))query();
  host_frame_sync();
 }
}
uint16_t abs_encoder_raw(void){
 reads++;if(priming)return raw;
 if(in_home){
  if(has("-read-") && !injected && actual_phase==cut_phase() && host_millis-phase_start>=HOME_MIN_MS)inject_deadline();
  if(has("home-final-fault") && reads==8)raw=1;
  if(has("home-reset-session") && resets==1 && !injected){injected=1;frame(1);}
  return raw;
 }
 if(!moving)return raw;
 if(!g_pred.active){
  idle_reads++;
  if(has("deadband")){
   if(idle_reads==(has("scan")?2u:1u)){injected=1;action();}
   return has("drive")?0:800;
  }
  if(has("start-") && idle_reads==1){injected=1;action();}
  if(has("fault"))return raw;
  if(has("gap"))raw=4000;
  else if(has("relative")||has("defocus"))raw=(resets?4000:0)+(idle_reads==1?1000:1020);
  else raw=(resets?4000:0)+800;
  return raw;
 }
 active_reads++;
 if(has("gap") && active_reads==1){host_millis+=UINT32_MAX;raw-=40;}
 else if(!has("gap"))host_millis+=5;
 if(active_reads==1){
  if(has("query-")||(!has("home-") && has("capture")))query();
  if(!has("home-") && has("capture"))capture_arm=1;
  if(has("retarget")){command(4,100,0);expected_target=1400;}
 }
 if(has("final-fault") && brakes)raw=1;
 else if(!has("gap") && !has("fault"))raw=(resets?4000:0)+(unsigned)((has("retarget") && active_reads<=2)?1000:expected_target);
 host_frame_sync();return raw;
}
#include "tracker.inc"
#include "main.inc"
static unsigned wire_answers(void){
 unsigned answers=0;assert(!sent_overflow);
 for(int i=0;i<sent_n;i++){
  unsigned n=sent_len[i],sum=0;uint8_t *p=sent[i];assert(n>=9 && p[0]==0xf0 && p[1]==n && p[n-1]==0x55);
  for(unsigned j=1;j<n-3;j++)sum+=p[j];assert(p[n-3]==(sum&255) && p[n-2]==(sum>>8));
  if(p[5]==6)for(unsigned j=45;j<n-3;){
   if(p[j]==EM_REC_Q_POS2D){assert(j+2<n-3 && (p[j+1]|p[j+2]<<8)==focus_distance_code(focus_em06_to_counts(5000),EM_FOCAL_MM10));answers++;j+=3;}
   else {assert((p[j]==EM_REC_MOVE || p[j]==EM_REC_STOP) && j+1<n-3);j+=2;}
  }
 }
 return answers;
}
static void prime_limit(void){
 priming=1;for(unsigned i=0;i<8;i++){raw=(i&1)?0:8192;assert(abs_encoder_track()==(int32_t)((i+1)*8192));}priming=0;reads=0;
}
int main(int argc,char **argv){
 assert(argc==2);mode=argv[1];st_init();em_init();frame(0x0a);em_poll();assert(em_handshake_done);
 sent_n=0;host_millis=0;g_home_session=g_focus_session=epoch=em_session_generation();expected_target=1000;
 if(has("deadband")){
  g_homed=moving=1;
  struct em_focus_cmd c={.op=EM_OP_MOVE,.target=focus_counts_to_em06(800)};
  if(has("scan")){c.op=EM_OP_SCAN;c.scan_a=c.scan_b=focus_counts_to_em06(1100);}
  if(has("drive")){c.op=EM_OP_DRIVE;c.drive_vel=-100;}
  focus_exec(&c,epoch);
  assert(injected && deadband_hits==1 && !observed_n && !drives && !g_pred.active && !test_events());
  assert(idle_reads==(has("scan")?2u:1u));
  if(has("scan"))assert(test_scan()!=EM_SCAN_SWEEPING && test_scan()!=EM_SCAN_DONE);
  if(has("inhibit"))assert(inhibited);
  if(has("session"))assert(em_session_generation()==epoch+1);
  if(has("shutdown"))assert(em_shutdown_requested());
 }else if(has("home-")){
  in_home=1;raw=4000;if(has("fault"))prime_limit();phase_start=host_millis;
  if(has("home-to-relative")){command(4,100,0);expected_target=1400;}
  else if(has("home-to-defocus")){command(6,10,0);expected_target=1320;}
  else command(0,focus_counts_to_em06(1000),0);
  if(has("capture"))capture_arm=1;
  query();home_service();
  if(has("capture"))assert(!capture_arm && em_session_generation()==epoch && em_handshake_done);
  unsigned fail=has("-cap-")||has("fault"),cancel=has("session")||has("shutdown");
  if(fail||cancel){
   assert(!g_homed && !g_next_pending);
   if(cancel)assert(g_home_state==HOME_CANCELLED && !inhibited);
   else assert(g_home_state==HOME_FAILED && inhibited);
   assert(resets==(has("reset-session")?1u:0u));
   unsigned attempts=g_home_attempts,old_drives=drives;
   home_service();assert(g_home_attempts==attempts && drives==old_drives);
   if(fail && !cancel){command(0,focus_counts_to_em06(1000),0);home_service();assert(g_home_attempts==attempts && drives==old_drives && !g_homed);}
  }else{
   assert(g_homed && g_home_state==HOME_READY && !inhibited && resets==1 && g_next_pending);
   if(has("relative"))expected_target=1400;
   if(has("defocus"))expected_target=1320;
   moving=1;in_home=0;brakes=0;reads=idle_reads=active_reads=0;
   struct em_focus_cmd c=g_next;g_next_pending=0;focus_exec(&c,g_next_session);
   assert(observed_n==1 && observed.target==expected_target && observed.outcome==SERVO_OK && !g_pred.active);
   assert(em_session_generation()==epoch && em_handshake_done);
   if(has("capture")){frame(0x0a);em_poll();host_millis+=17;host_frame_sync();pump(g_track);assert(wire_answers()==1);}
  }
 }else{
  g_homed=moving=1;
  if(has("fault"))prime_limit();
  if(has("wrap"))host_millis=UINT32_MAX-15;
  if(has("gap"))expected_target=0;
  if(has("gap") && has("relative")){expected_target=0;command(4,(uint16_t)-1000,0);}
  else command(0,focus_counts_to_em06(expected_target),0);
  struct em_focus_cmd c;assert(em_take_focus_cmd(&c));focus_exec(&c,epoch);
  assert(!g_pred.active && observed_n==1);
  if(has("start-")||has("query-session")||has("query-shutdown")||has("final-fault")){
   assert(g_focus_aborts==1 && test_events()==(has("stop")?1u:0u));
   if(has("start-"))assert(!drives);
   if(has("query-"))assert(conversions==1 && !query_answers() && !query_pending() && !wire_answers());
   if(has("shutdown"))for(int i=cut_sent;i<sent_n;i++)assert(sent[i][5]!=6);
  }else if(has("gap")){
   assert(observed.target==0 && observed.outcome==SERVO_TIMEOUT && !drives && pumps==1);
   assert(pump_vel==-1024 && pump_ahead==3892);
   if(!has("capture")){assert(sent_n==2 && sent[1][5]==6 && (sent[1][8]|sent[1][9]<<8)==focus_counts_to_em06(3892));}
  }else{
   assert(observed.target==expected_target && observed.outcome==SERVO_OK);
   if(has("retarget"))assert(observed.retargets==1);
  }
  if(has("capture")){
   assert(!capture_arm && em_session_generation()==epoch && em_handshake_done);
   host_millis+=17;host_frame_sync();pump(g_track);frame(0x0a);em_poll();host_millis+=17;host_frame_sync();pump(g_track);assert(wire_answers()==1 && !query_answers() && !query_pending());
  }
 }
 if(has("fault"))assert(test_fault()==ST_ENCODER_OVERFLOW && inhibited);
 if(has("-cap-") && !has("fault") && !has("session") && !has("shutdown"))assert(test_fault()==ST_HOME_FAILED);
 assert(!mask);unsigned answers=wire_answers();
 printf("PASS %s home=%u state=%u reset=%u observed=%u target=%d outcome=%u reads=%u drives=%u pumps=%u conversions=%u answers=%u elapsed=%u epoch=%u\n",mode,g_homed,g_home_state,resets,observed_n,observed.target,observed.outcome,reads,drives,pumps,conversions,answers,injected_elapsed,(unsigned)em_session_generation());
 return 0;
}
