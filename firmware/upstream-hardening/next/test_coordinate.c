#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "servo.h"
#include "emount.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
#include "startup_trace.h"
#ifndef ENC_TRACK_LIMIT
#define ENC_TRACK_LIMIT 65536 /* Expected future contract, for frozen controls. */
#endif
#define ENC_COUNTS 16384
static int32_t g_track;
static uint16_t g_track_last, raw;
static int inhibited, nonzero_drive, running;
static uint32_t clock_ms;
static unsigned fault;
uint16_t abs_encoder_raw(void){return raw;}
void motor_inhibit(void){inhibited=1;}
uint8_t motor_is_inhibited(void){return inhibited;}
void motor_attach_pins(void){}
void motor_drive(int16_t duty){assert(!inhibited || duty==0);if(duty)nonzero_drive++;}
void motor_brake(void){}
void st_inhibit_fault(uint8_t f){fault=f;}
uint32_t millis(void){return clock_ms;}
static uint8_t focus_abort(void){return running && clock_ms>=15;}
static uint8_t focus_retarget(int32_t *t){(void)t;return 0;}
static void pump(int32_t p){(void)p;}
uint16_t em_defocus_scale(void){return 8;}
#include "tracker.inc"
int32_t tracked(void){if(running)clock_ms+=5;return abs_encoder_track();}
#include "target.inc"
#include "stock.inc"
static void set(int32_t here){g_track=here;raw=g_track_last=0;inhibited=0;fault=0;}
int main(int argc,char **argv){
 assert(argc==2);assert(ENC_TRACK_LIMIT==65536);
 if(!strcmp(argv[1],"capacity")){
  const int32_t at[]={-65536,-65535,-57344,-1,0,1,57344,65535,65536};unsigned n=0;
  for(unsigned k=0;k<sizeof at/sizeof at[0];k++)for(unsigned v=0;v<16384;v++){
   set(at[k]);raw=v;int32_t d=v>8192?(int32_t)v-16384:(int32_t)v;
   int64_t next=(int64_t)at[k]+d;int bad=next < -65536 || next>65536;
   int32_t result=abs_encoder_track();assert(inhibited==bad);
   assert(result==(bad?at[k]:(int32_t)next));assert(!bad || fault==ST_ENCODER_OVERFLOW);n++;
  }
  printf("PASS capacity=%u\n",n);return 0;
 }
 if(!strcmp(argv[1],"fault-history")){
  for(int sign=-1;sign<=1;sign+=2){set(0);unsigned first=0;
   for(unsigned i=1;i<=525;i++){raw=(raw+sign*4096)&16383;abs_encoder_track();if(inhibited&&!first)first=i;assert(g_track>=-65536 && g_track<=65536);}
   assert(first==17 && g_track==sign*65536 && fault==ST_ENCODER_OVERFLOW);
   struct servo_result result;struct servo_cfg cfg=STOCK;running=1;clock_ms=0;nonzero_drive=0;
   servo_move_rel(-g_track,&cfg,&result);assert(result.outcome==SERVO_ABORTED && !nonzero_drive);running=0;
  }
  puts("PASS history capacity inhibits before servo arithmetic");return 0;
 }
 if(!strcmp(argv[1],"normal")){
  uint64_t hash=1469598103934665603ULL;unsigned checks=0;
  for(unsigned v=0;v<65536;v++)for(int op=0;op<2;op++)for(int edge=-1;edge<=1;edge++){
   set(edge*65536);struct em_focus_cmd c={.op=op?EM_OP_MOVE_DEFOCUS:EM_OP_MOVE_REL,.delta=(int16_t)v};int32_t answer;
   assert(focus_cmd_target(&c,&answer));int64_t expected=(int64_t)g_track+(int64_t)c.delta*(op?8:1)*4;
   expected=expected<0?0:expected>5952?5952:expected;assert(answer==expected);
   hash=(hash^(uint32_t)answer)*1099511628211ULL;checks++;
  }
  printf("PASS targets=%u hash=%llu\n",checks,(unsigned long long)hash);return 0;
 }
 if(!strcmp(argv[1],"predictor")){
  const uint32_t periods[]={0,1,5,30,0x7fffffff,0x80000000,0xffffffff};unsigned n=0;
  for(int a=-1;a<=1;a++)for(int b=-1;b<=1;b++)for(int goal=0;goal<=5952;goal+=5952)
   for(unsigned k=0;k<sizeof periods/sizeof periods[0];k++)for(unsigned frame=10;frame<=30;frame++){
    int32_t pos=a*65536,next=b*65536;struct focus_pred pred;focus_pred_begin(&pred,pos,goal,0xffffff00);
    focus_pred_sample(&pred,next,0xffffff00+periods[k]);int32_t ahead=focus_pred_ahead(&pred,next,frame);
    assert(ahead>=(next<goal?next:goal) && ahead<=(next>goal?next:goal));n++;
   }
  printf("PASS predictor=%u\n",n);return 0;
 }
 if(!strcmp(argv[1],"servo-normal")){
  set(1000);running=1;struct servo_result result;struct servo_cfg cfg=STOCK;
  servo_move_rel(200,&cfg,&result);assert(result.outcome==SERVO_ABORTED && !inhibited && nonzero_drive);
  printf("PASS servo-normal drives=%d end=%d\n",nonzero_drive,result.end);return 0;
 }
 return 2;
}
