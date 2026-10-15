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
void host_body_frame(const uint8_t *, uint16_t);
void host_frame_sync(void);
uint32_t millis(void);
static const char *mode;
static int g_aborted, g_homed, g_next_pending, inhibited;
static uint8_t g_abort_pending, g_abort_by_stop;
static uint16_t g_last_target;
static uint32_t g_focus_session, g_next_session, g_home_session;
static int32_t g_last_reported;
static struct em_focus_cmd g_next;
static struct focus_pred g_pred;
static enum home_state {HOME_UNTRIED, HOME_ACTIVE, HOME_READY, HOME_CANCELLED, HOME_FAILED} g_home_state;
static int32_t g_track;
static uint16_t g_track_last;
static unsigned raw, reads, resets, pumps, conversions, brakes, drives, mask, injected;
static unsigned actual_phase, first_nonzero, last_nonzero;
static uint32_t phase_start, injected_elapsed;
static int32_t pump_vel, pump_ahead;
static void pump(int32_t pos);
static uint8_t focus_abort(void);
static uint8_t focus_retarget(int32_t *target);
#include "config.inc"
uint32_t st_lock(void) { unsigned old=mask; mask=1; return old; }
void st_unlock(uint32_t k) { mask=k; }
uint8_t motor_is_inhibited(void) { return inhibited; }
void motor_inhibit(void) { inhibited=1; }
void motor_emergency_release(void) {}
void motor_attach_pins(void) {}
void motor_drive(int16_t d) {
    if(d && !inhibited){drives++;if(!first_nonzero)first_nonzero=host_millis;last_nonzero=host_millis;}
}
void motor_brake(void) { brakes++; actual_phase=1;phase_start=host_millis; }
static void vdd_track_reset(void) {}
static void vdd_track_result(uint16_t *lo, uint16_t *hi) { *lo=*hi=0; }
static void seal(uint8_t *p,unsigned n) {
    unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;
    for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
}
static void query(void) {
    uint8_t p[25]={0};p[3]=1;p[4]=0x72;p[5]=4;
    p[19]=EM_REC_Q_POS2D;p[20]=5000&255;p[21]=5000>>8;
    seal(p,sizeof p);host_body_frame(p,sizeof p);
}
static unsigned cut_phase(void) {return strstr(mode,"settle")!=0;}
static void inject_deadline(void) {
    unsigned cap=actual_phase?HOME_SETTLE_MS:HOME_MS;
    if(strstr(mode,"before"))cap--;
    if(strstr(mode,"over"))cap++;
    host_millis=phase_start+cap;injected=1;injected_elapsed=cap;
}
static void compute_hook(void) {
    assert(!mask);conversions++;
    if(strstr(mode,"home-") && strstr(mode,"pump-") && !injected && actual_phase==cut_phase())inject_deadline();
}
static void vdd_track_sample(void) {
    pumps++;
    pump_vel=g_pred.vel_q8;
    pump_ahead=focus_pred_ahead(&g_pred,g_track,17);
    if(strstr(mode,"home-") && !strstr(mode,"freeze")) {
        /* The injected query conversion defines the exact observation boundary. */
        if(!injected)host_millis+=10;
        else if(actual_phase!=cut_phase())host_millis+=10;
        if(!injected && actual_phase==cut_phase() && strstr(mode,"pump-"))query();
    }
}
#ifndef SERVO_FIRST_FEEDBACK_READ
#define SERVO_FIRST_FEEDBACK_READ 3
#endif
uint16_t abs_encoder_raw(void) {
    reads++;
    if(strstr(mode,"home-") && strstr(mode,"-read-") && !injected && actual_phase==cut_phase()
       && host_millis-phase_start>=HOME_MIN_MS)inject_deadline();
    if(strstr(mode,"servo-gap") && reads==SERVO_FIRST_FEEDBACK_READ) {
        host_millis+=strstr(mode,"half")?0x80000000u:0xffffffffu;
        raw-=40;host_frame_sync();
    } else if(!strcmp(mode,"servo-full-wrap-alias")) {
        if(reads==SERVO_FIRST_FEEDBACK_READ)host_millis=5;
        if(reads==SERVO_FIRST_FEEDBACK_READ+1){host_millis=4;raw-=40;}
        if(reads==SERVO_FIRST_FEEDBACK_READ+2)inhibited=1;
    } else if(!strcmp(mode,"servo-wrap"))host_millis+=5;
    else if(!strcmp(mode,"servo-freeze-driven") && reads==SERVO_FIRST_FEEDBACK_READ)host_millis+=5;
    return raw;
}
#include "tracker.inc"
#include "main.inc"
static void verify_wire(void) {
    assert(!sent_overflow);
    for(int i=0;i<sent_n;i++) {
        unsigned n=sent_len[i],sum=0;uint8_t *p=sent[i];
        assert(n>=9 && p[0]==0xf0 && p[1]==n && p[n-1]==0x55);
        for(unsigned j=1;j<n-3;j++)sum+=p[j];
        assert(p[n-3]==(sum&255) && p[n-2]==(sum>>8));
    }
}
int main(int argc,char **argv) {
    assert(argc==3);mode=argv[1];unsigned fixed=!strcmp(argv[2],"proposal");
    em_init();uint8_t init[11]={0};init[3]=2;init[4]=0x71;init[5]=0x0a;seal(init,sizeof init);
    host_body_frame(init,sizeof init);em_poll();assert(em_handshake_done);
    sent_n=0;host_millis=0;g_home_session=g_focus_session=em_session_generation();
    if(strstr(mode,"home-")) {
        if(strstr(mode,"wrap"))host_millis=UINT32_MAX-25;
        phase_start=host_millis;g_home_state=HOME_ACTIVE;g_next_pending=1;
        query();motor_home();
        printf("%s variant=%u homed=%d state=%d pumps=%u reads=%u conversions=%u injected_elapsed=%u resets=%u inhibited=%u\n",mode,fixed,g_homed,g_home_state,pumps,reads,conversions,injected_elapsed,resets,inhibited);fflush(stdout);
        unsigned fail=strstr(mode,"freeze")!=0 || (fixed && (strstr(mode,"cap") || strstr(mode,"over")));
        if(fail)assert(!g_homed && g_home_state==HOME_FAILED && inhibited && !resets && !g_next_pending);
        else assert(g_homed && g_home_state==HOME_READY && !inhibited && resets==1);
        if(strstr(mode,"freeze"))assert(pumps==HOME_POLL_LIMIT-1);
    } else if(strstr(mode,"servo-")) {
        raw=4000;g_homed=1;
        if(!strcmp(mode,"servo-wrap"))host_millis=UINT32_MAX-15;
        unsigned outcome=focus_run(0,4144,&STOCK);
        printf("%s variant=%u outcome=%u drives=%u last_nonzero=%u pumps=%u reads=%u final_pump_vel=%d ahead=%d wire=%d\n",mode,fixed,outcome,drives,last_nonzero,pumps,reads,pump_vel,pump_ahead,sent_n);fflush(stdout);
        if(strstr(mode,"gap")) {
            assert(outcome==SERVO_TIMEOUT && !drives && pumps==1 && sent_n==2);
            assert(pump_vel==(fixed || strstr(mode,"half") ? -1024 : 4096));
            assert(pump_ahead==(fixed || strstr(mode,"half") ? 3892 : 3960));
            assert(sent[1][5]==6 && (sent[1][0x1a]|sent[1][0x1b]<<8)==focus_counts_to_em06(3960));
            assert((sent[1][8]|sent[1][9]<<8)==focus_counts_to_em06(pump_ahead));
            assert((sent[1][6]&0x80)==(pump_ahead==3960?0x80:0));
        } else if(strstr(mode,"freeze"))assert(outcome==SERVO_ABORTED && inhibited && drives==(strstr(mode,"driven")?1u:0u) && pumps==1000000u);
        else if(strstr(mode,"alias"))assert(outcome==SERVO_ABORTED && drives==2 && last_nonzero==4);
        else assert(outcome==SERVO_STALL && !inhibited && drives>0);
        assert(!g_pred.active);
    } else if(!strcmp(mode,"predictor-zero")) {
        struct focus_pred p;focus_pred_begin(&p,100,1000,7);focus_pred_sample(&p,110,7);
        assert(p.last_pos==100 && p.last_ms==7 && p.vel_q8==2048);
    } else {
        uint32_t dt[]={1,5,0x7fffffffu,0x80000000u,0xffffff00u,0xffffffffu};
        for(unsigned i=0;i<sizeof(dt)/sizeof(dt[0]);i++)for(int sign=-1;sign<=1;sign+=2) {
            struct focus_pred p;focus_pred_begin(&p,4000,sign>0?5000:0,11);
            int32_t pos=4000+sign*40;focus_pred_sample(&p,pos,11+dt[i]);
            int32_t fresh=(int32_t)((int64_t)sign*40*256/dt[i]);
            int32_t old=sign*2048,d=fresh-old,expected=old+(d+(d>=0?1:-1))/2;
            if(fixed || dt[i]<=0x80000000u)assert(p.vel_q8==expected);
        }
        printf("%s variant=%u checked=12\n",mode,fixed);
    }
    verify_wire();assert(!mask);return 0;
}
