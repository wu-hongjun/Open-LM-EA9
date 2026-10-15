#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "servo.h"
static unsigned reads,drives;
static int mode,latch;
static uint32_t now;
uint32_t millis(void) {return now;}
int32_t abs_encoder_track(void) {
    reads++;
    if(reads>1000010) {puts("FAIL frozen clock has no finite work bound");exit(1);}
    if(mode==0) return 0;
    if(reads==1)return 0;
    if(mode==5)return 800;
    if(mode==6)return -121;
    now=reads==2?5:reads==3?10:reads==4?15:reads==5?16:reads==6?20:25;
    if(mode==1 && reads>=5)return 110;
    if(mode==3 && reads==5) {latch=1;return 100;}
    return 100;
}
uint16_t abs_encoder_raw(void) {return 100;}
uint8_t motor_is_inhibited(void) {return latch;}
void motor_inhibit(void) {latch=1;}
void motor_attach_pins(void) {}
void motor_drive(int16_t d) {(void)d;drives++;}
void motor_brake(void) {}
static uint8_t stop(void) {return (mode==1 || mode==4) && now>=25;}
static uint8_t retarget(int32_t *t) {if(mode==4 && now>=16){*t=110;return 1;}return 0;}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    mode=!strcmp(argv[1],"runaway")?5:!strcmp(argv[1],"wrongway")?6:!strcmp(argv[1],"retarget")?4:!strcmp(argv[1],"freeze")?0:!strcmp(argv[1],"stale")?1:!strcmp(argv[1],"final-inhibit")?3:2;
    struct servo_cfg cfg={.stop_ms=30,.v_cruise=10000,.ff_div=40,.kp_div=50,.tau_ms=33,.v_arrive=500,.arrive_steps=2,.duty_max=1000,.tolerance=12,.noise=8,.timeout_ms=400,.stall_ms=300,.abort=stop,.retarget=retarget,.retarget_max=1};
    struct servo_result r;
    servo_move_rel(100,&cfg,&r);
    int good=mode==5?(r.outcome==SERVO_RUNAWAY && latch):mode==6?(r.outcome==SERVO_WRONG_WAY && latch):mode==0?(r.outcome==SERVO_TIMEOUT && latch):(mode==1 || mode==4)?r.outcome==SERVO_ABORTED:mode==3?r.outcome!=SERVO_OK:r.outcome==SERVO_OK;
    printf("%s outcome=%u reads=%u drives=%u inhibit=%d\n",good?"PASS":"FAIL",r.outcome,reads,drives,latch);
    return !good;
}
