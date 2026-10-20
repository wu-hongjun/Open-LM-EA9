#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include "abs_encoder.h"
#include "startup_trace.h"
#define ENC_COUNTS 16384
#define HOME_STILL_COUNTS 6
struct home_still {int32_t at;uint32_t t;};
static int32_t g_track;
static uint16_t g_track_last,raw;
static uint32_t clock_now;
static unsigned inhibited,faults;
uint16_t abs_encoder_raw(void){return raw;}
void motor_inhibit(void){inhibited=1;}
void st_inhibit_fault(uint8_t f){assert(f==ST_ENCODER_OVERFLOW);faults++;}
static uint32_t millis(void){return clock_now;}
/* EXTRACTED_TRACKER */
/* EXTRACTED_HELPERS */
static uint32_t seed=0xea947;
static uint32_t next(void){seed=seed*1664525u+1013904223u;return seed;}
int main(void){
 unsigned compared=0;
 /* Exhaust all admitted anchors against threshold-adjacent and extreme samples.
  * Time controls include under/at/over40, normal wrap and UINT32_MAX. */
 const int32_t samples[]={-ENC_TRACK_LIMIT,-7,-6,-1,0,1,6,7,ENC_TRACK_LIMIT};
 const uint32_t times[]={0,39,40,41,UINT32_MAX};
 for(int32_t anchor=-ENC_TRACK_LIMIT;anchor<=ENC_TRACK_LIMIT;anchor++){
  for(unsigned j=0;j<sizeof(samples)/sizeof(*samples);j++)for(unsigned k=0;k<5;k++){
   int32_t sample=samples[j];uint32_t t=next();clock_now=t+times[k];
   struct home_still a={anchor,t},b=a;
   /* Same raw delta0 preserves the admitted tracker value for both calls. */
   g_track=sample;g_track_last=raw=0;
   uint8_t x=baseline(&a,40),y=proposal(&b,40);
   assert(x==y && a.at==b.at && a.t==b.t);assert(!inhibited);compared++;
  }
 }
 /* Real production tracker preserves capacity and latches inhibition rather
  * than publishing an out-of-range addition. Test both signs and raw seams. */
 for(unsigned sign=0;sign<2;sign++){
  raw=0;abs_encoder_track_reset();inhibited=faults=0;
  for(unsigned i=0;i<20;i++){raw=(raw+(sign?8191:8192))&16383;int32_t n=abs_encoder_track();assert(n>=-ENC_TRACK_LIMIT&&n<=ENC_TRACK_LIMIT);}
  assert(inhibited && faults); /* sign0 increments, sign1 increments8191 also bounded */
 }
 raw=0;abs_encoder_track_reset();inhibited=faults=0;
 for(unsigned i=0;i<20;i++){raw=(raw+8193)&16383;int32_t n=abs_encoder_track();assert(n>=-ENC_TRACK_LIMIT&&n<=ENC_TRACK_LIMIT);}
 assert(inhibited && faults);
 /* Existing corrupted-state guard retains corruption and inhibits. */
 for(unsigned i=0;i<2;i++){g_track=i?INT32_MAX:INT32_MIN;g_track_last=raw=0;inhibited=faults=0;assert(abs_encoder_track()==g_track && inhibited && faults==1);}
 /* Compare the real tracker/helper combination at signed extremes, thresholds,
  * and deterministic full-range random coordinates, including inhibition. */
 const int32_t edges[]={INT32_MIN,INT32_MIN+6,INT32_MIN+7,-65537,-7,-6,0,6,7,65537,INT32_MAX-7,INT32_MAX-6,INT32_MAX};
 for(unsigned j=0;j<1000169;j++){
  int32_t anchor=j<169?edges[j/13]:(int32_t)next();
  int32_t sample=j<169?edges[j%13]:(int32_t)next();
  uint32_t t=next();clock_now=t+times[j%5];
  struct home_still a={anchor,t},b=a;
  g_track=sample;g_track_last=raw=0;inhibited=faults=0;
  uint8_t x=baseline(&a,40);unsigned old_inhibited=inhibited,old_faults=faults;
  inhibited=faults=0;
  uint8_t y=proposal(&b,40);
  assert(x==y && a.at==b.at && a.t==b.t);
  assert(inhibited==old_inhibited && faults==old_faults);compared++;
 }
 printf("PASS %u bounded/full-int32-domain stillness comparisons; actual tracker capacity/overflow/corrupted-state controls\n",compared);
}
