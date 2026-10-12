/* Quantized/clamped repeated targets, cancellation and finite redirect
 * budgets against the production wrapper. Scripted feedback, no physics. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "factory_servo.h"
#include "factory_af.h"
#include "io_guard.h"
#include "focus_map.h"
static unsigned mode,calls;
static uint64_t ticks,begun,last;
static int16_t duty;
uint32_t millis(void) {return ticks/48000u;}
uint32_t clock_cycles(void) {ticks+=5000u;return ticks;}
void motor_emergency_release(void) {duty=0;}
void motor_release(void) {duty=0;}
void motor_brake(void) {duty=0;}
void motor_drive(int16_t d) {assert(!ea9_io_faults());duty=d;}
int32_t abs_encoder_track(void) {return (ticks-begun)/48000u;}
static uint8_t retarget(int32_t *target) {
 if(ticks-last<16u*48000u)return 0;
 last=ticks;++calls;
 *target=mode==2?INT32_MAX:mode==3?(calls%2?1000:2000):4000+(calls%4);
 return 1;
}
static uint8_t abort_motion(void) {return mode==1 && ticks-begun>=100u*48000u;}
int main(int argc,char **argv) {
 assert(argc==2);mode=atoi(argv[1]);assert(mode<=3);begun=ticks;
 struct servo_cfg cfg={.duty_max=800,.stall_ms=600,.timeout_ms=380,.total_ms=5000,.retarget=retarget,.retarget_max=mode==3?1:0,.abort=abort_motion};
 struct servo_result r;factory_servo_move_to(mode==2?5952:4000,&cfg,&r);
 assert(!duty && !ea9_io_faults());
 if(mode==1)assert(r.outcome==SERVO_ABORTED && r.retargets==0);
 else if(mode==3)assert(r.outcome==SERVO_TIMEOUT && r.retargets==1);
 else assert(r.outcome==SERVO_DEADLINE && r.retargets==0 && r.ms<380 && calls>16);
 printf("quantized mode=%u outcome=%u ms=%u retargets=%u callbacks=%u target=%d end=%d\n",mode,r.outcome,r.ms,r.retargets,calls,r.target,r.end);return 0;
}
