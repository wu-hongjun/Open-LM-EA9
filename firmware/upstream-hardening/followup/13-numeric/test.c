#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "servo.h"
#include "emount.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
#define ENC_COUNTS 16384
static int32_t g_track;
static uint16_t g_track_last, raw;
static int latch, drives, running;
static uint32_t now;
static unsigned calls;
uint16_t abs_encoder_raw(void) {return raw;}
void motor_inhibit(void) {latch=1;}
uint8_t motor_is_inhibited(void) {return latch;}
void motor_attach_pins(void) {}
void motor_drive(int16_t d) {assert(d>=-1280 && d<=1280);drives++;}
void motor_brake(void) {}
void st_inhibit_fault(uint8_t f) {(void)f;}
uint32_t millis(void) {return now;}
static uint8_t focus_abort(void) {return running && now >=15;}
static uint8_t focus_retarget(int32_t *t) {(void)t;return 0;}
static void pump(int32_t p) {(void)p;}
uint16_t em_defocus_scale(void) {return 16;}
#include "tracker.inc"
static int32_t tracked(void) {if(running) {calls++;now=calls*5;}return abs_encoder_track();}
#include "target.inc"
#include "stock.inc"
static void accumulate(unsigned n, int step) {
    for(unsigned i=0;i<n;i++) {raw=(uint16_t)((raw+step)&16383);abs_encoder_track();}
    assert(!latch);
}
int main(int argc,char **argv) {
    assert(argc==2);
    if(!strcmp(argv[1],"servo-positive") || !strcmp(argv[1],"servo-negative")) {
        int sign=!strcmp(argv[1],"servo-positive")?1:-1;
        accumulate(525,sign*4096);
        int32_t want=sign>0?0:5952, delta=want-g_track;
        printf("REACHABLE rawReads=525 track=%d inhibit=%d target=%d\n",g_track,latch,want);fflush(stdout);
        struct servo_cfg cfg=STOCK;struct servo_result r;running=1;
        servo_move_rel(delta,&cfg,&r);assert(r.outcome==SERVO_ABORTED && !latch);
        printf("PASS outcome=%u drives=%d\n",r.outcome,drives);return 0;
    }
    if(!strncmp(argv[1],"relative-",9)) {
        int sign=!strcmp(argv[1],"relative-positive")?1:-1;
        accumulate(524287,sign*4096);
        struct em_focus_cmd c={.op=EM_OP_MOVE_REL,.delta=sign>0?32767:-32768};int32_t out;
        printf("REACHABLE rawReads=524287 track=%d inhibit=%d delta=%d\n",g_track,latch,c.delta);fflush(stdout);
        assert(focus_cmd_target(&c,&out));assert(out==(sign>0?5952:0));puts("PASS");return 0;
    }
    if(!strcmp(argv[1],"predictor-arbitrary")) {
        struct focus_pred p;focus_pred_begin(&p,0,5952,0);
        focus_pred_sample(&p,INT32_MAX,1);puts("UNEXPECTED");return 1;
    }
    if(!strcmp(argv[1],"normal")) {
        uint64_t hash=1469598103934665603ULL;unsigned checks=0;
        for(unsigned i=0;i<65536;i++) {
            int32_t pos=focus_em06_to_counts(i), dist=focus_counts_for_code(i,500);
            assert(pos>=0 && pos<=5952 && dist>=0 && dist<=5952);
            for(unsigned j=0;j<2;j++) {
                g_track=j?5952:0;g_track_last=raw;
                struct em_focus_cmd c={.op=EM_OP_MOVE_REL,.delta=(int16_t)i};int32_t out;
                assert(focus_cmd_target(&c,&out));int64_t wide=(int64_t)g_track+(int16_t)i*4;
                assert(out==(wide<0?0:wide>5952?5952:wide));
                hash=(hash^(uint32_t)out)*1099511628211ULL;checks++;
            }
            hash=(hash^(uint32_t)pos^(uint32_t)dist)*1099511628211ULL;checks+=2;
        }
        for(int a=0;a<=5952;a+=31) for(int b=0;b<=5952;b+=31) for(unsigned dt=1;dt<=30;dt++) {
            struct focus_pred p;focus_pred_begin(&p,a,b,UINT32_MAX-10);
            focus_pred_sample(&p,b,UINT32_MAX-10+dt);
            for(unsigned period=10;period<=30;period+=10) {
                int32_t v=focus_pred_ahead(&p,a,period);
                assert(v>=(a<b?a:b) && v<=(a>b?a:b));hash=(hash^(uint32_t)v)*1099511628211ULL;checks++;
            }
        }
        printf("PASS normal checks=%u hash=%llu\n",checks,(unsigned long long)hash);return 0;
    }
    return 2;
}
