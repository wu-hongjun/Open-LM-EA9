#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "abs_encoder.h"
#include "motor.h"
#include "servo.h"
#include "startup_trace.h"
#include "emount.h"
static uint32_t now;
static int g_aborted, g_homed, g_next_pending;
static enum home_state {HOME_UNTRIED,HOME_ACTIVE,HOME_READY,HOME_CANCELLED,HOME_FAILED} g_home_state;
static uint32_t g_home_session;
static unsigned reads, raw, inject_at, pumps, resets, brakes, actual_drives, commands;
static uint8_t inhibited, fault;
static int32_t g_track;
static uint16_t g_track_last;
static const struct servo_cfg STOCK = {.dry=0};
volatile uint8_t em_handshake_done = 1;
uint32_t em_session_generation(void) {return 0;}
uint8_t em_shutdown_requested(void) {return 0;}
uint32_t millis(void) {return now;}
uint32_t st_lock(void) {return 0;}
void st_unlock(uint32_t key) {(void)key;}
void st_inhibit_fault(uint8_t reason) {if(!fault)fault=reason;}
uint8_t motor_is_inhibited(void) {return inhibited;}
void motor_inhibit(void) {inhibited=1;}
void motor_attach_pins(void) {}
void motor_drive(int16_t duty) {if(!inhibited && duty)actual_drives++;}
void motor_brake(void) {brakes++;}
static void home_cutoff(void) {}
static uint8_t home_command(void) {commands++;return 0;}
static void vdd_track_reset(void) {}
static void vdd_track_result(uint16_t *lo,uint16_t *hi) {*lo=*hi=0;}
static void pump(int32_t pos) {(void)pos;now+=10;pumps++;}
uint16_t abs_encoder_raw(void) {
 reads++;
 if(inject_at==100)raw=reads<=8?((reads&1)?8192:0):1;
 else if(reads==inject_at)raw=1;
 return raw;
}
#include "tracker.inc"
#include "home.inc"
int main(int argc,char **argv) {
 assert(argc==3);inject_at=atoi(argv[1]);int fixed=atoi(argv[2]);
 /* Establish +65536 through eight accepted production tracker calls. */
 unsigned cut=inject_at;inject_at=0;
 if(cut!=100){
  for(unsigned i=0;i<8;i++){raw=(i&1)?0:8192;assert(abs_encoder_track()==(int32_t)((i+1)*8192));}
  assert(!inhibited && g_track==ENC_TRACK_LIMIT);
 }
 reads=0;raw=0;inject_at=cut;g_home_state=HOME_ACTIVE;g_next_pending=1;
 motor_home();
 printf("cut=%u fixed=%d inhibited=%u fault=%u state=%d homed=%d track=%d resets=%u pumps=%u drives=%u reads=%u\n",cut,fixed,inhibited,fault,g_home_state,g_homed,g_track,resets,pumps,actual_drives,reads);fflush(stdout);
 if(!cut){assert(!inhibited && !fault && g_homed && g_home_state==HOME_READY && resets==1);}
 else {
  assert(inhibited && fault==ST_ENCODER_OVERFLOW);
  if(fixed){assert(!g_homed && g_home_state==HOME_FAILED && !g_next_pending && !resets);}
  else {assert(g_homed && g_home_state==HOME_READY && resets==1 && g_track==0);}
 }
 return 0;
}
