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
#include "abs_encoder.h"
#include "motion_trace.h"
extern uint32_t host_millis;
extern int sent_n, sent_overflow;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
uint32_t millis(void);
unsigned query_pending(void);
unsigned query_answers(void);
unsigned host_fault(void);
static uint8_t g_homed, g_aborted, g_next_pending;
static struct em_focus_cmd g_next;
static uint32_t g_next_session;
static struct focus_pred g_pred;
static const struct servo_cfg STOCK={.dry=0};
static const char *mode;
static uint32_t start_time, phase_time;
static unsigned samples, brakes, releases, resets, drives, reports, wire_queries, wire_status, wire_shutdown, query_n;
static unsigned qualifying, cutoff, final_reads;
static unsigned cross_done, post_failure, lock_depth, conversion_action;
static int32_t g_track;
static uint16_t g_track_last;
static unsigned raw_reads, uart_waits, uart_frame_id, adc_samples;
static uint8_t g_disabled;
static struct {struct {struct{uint32_t reg;}INTFLAG,DATA;}USART;} peripheral;
#define EMSERCOM (&peripheral)
#define SERCOM_USART_INTFLAG_TXC 2u
#define ENC_COUNTS 16384
static uint32_t foreground_step;
uint32_t st_lock(void){unsigned old=lock_depth;lock_depth=1;return old;}
void st_unlock(uint32_t old){lock_depth=old;}
union mmreg {uint32_t reg; struct {unsigned PMUXEN:1;} bit;};
static struct {struct {union mmreg PINCFG[32],PMUX[16],DIRCLR,OUTSET;} Group[1];} port;
static struct {union mmreg SYNCBUSY,CC[4];} tcc;
#define PORT (&port)
#define TCC0 (&tcc)
#define MOTOR_PIN_WO0 8
#define MOTOR_PIN_WO1 9
#define MOTOR_PIN_WO2 18
#define MOTOR_PIN_WO3 19
#define MOTOR_MUX_WO01 4
#define MOTOR_MUX_WO23 5
#define MOTOR_DUTY_MAX 2560
#define PORT_PINCFG_PMUXEN 1
#define PORT_PMUX_PMUXE(x) (x)
#define PORT_PMUX_PMUXO(x) ((x)<<4)
#include "motor.inc"
#define inhibited g_motor_inhibited
uint16_t abs_encoder_raw(void){
    raw_reads++;
    uint32_t t=host_millis-start_time;
    int32_t p=0;
    if(!strcmp(mode,"drive-deadline"))p=20*(int32_t)t;
    if(!strcmp(mode,"session") || !strcmp(mode,"shutdown") || !strcmp(mode,"stop") || !strcmp(mode,"corrupt") || !strcmp(mode,"ramp200") || !strcmp(mode,"storm") || !strcmp(mode,"uart-ordinary"))p=-20*(int32_t)(t<200?t:200);
    if(!strcmp(mode,"ramp259") || !strcmp(mode,"ramp260")){unsigned end=!strcmp(mode,"ramp259")?259:260;p=-20*(int32_t)(t<end?t:end);}
    if(!strcmp(mode,"settle-deadline") && brakes)p=7*(int32_t)(host_millis-phase_time);
    if(!strcmp(mode,"noise6"))p=(t&1)?6:0;
    if(!strcmp(mode,"noise7"))p=(t && !(t&1))?7:0;
    if(!strcmp(mode,"late280") || !strcmp(mode,"release-drift") || !strcmp(mode,"final-drift") || !strcmp(mode,"after-drift") || !strcmp(mode,"late-uart-cross") || !strcmp(mode,"settle-session") || !strcmp(mode,"settle-shutdown") || !strcmp(mode,"settle-stop"))p=-(int32_t)(t<280?(2902*t/280):2902);
    if(!strcmp(mode,"moving"))p=-(int32_t)(t<300?10*t:3000);
    if(!strcmp(mode,"wrong-way"))p=(int32_t)(t<280?10*t:2800);
    if(!strcmp(mode,"too-far"))p=-(int32_t)(t<280?25*t:7000);
    if(!strcmp(mode,"release-drift") && releases)p+=7;
    if(!strcmp(mode,"final-drift") && t>=340 && ++final_reads>=3)p+=7;
    if(!strcmp(mode,"after-drift") && t>=340 && ++final_reads==2)p+=7;
    return (uint16_t)((5000+p)&(ENC_COUNTS-1));
}
#include "tracker.inc"
void uart_begin(const uint8_t *p){uart_frame_id=p[5];}
static unsigned uart_ready(unsigned flag){
    if(!cross_done && uart_frame_id==5 && ((flag==1 && !strcmp(mode,"uart-drive-cross") && !brakes) || (flag==2 && !strcmp(mode,"uart-settle-cross") && brakes))){
        uart_waits++;host_millis++;
        if(uart_waits==(brakes?500u:300u))cross_done=1;
        return 0;
    }
    return 1;
}
#include "uart.inc"
static void focus_report_at(int32_t p){(void)p;reports++;}
static void focus_report(void){reports++;}
static void focus_exec(const struct em_focus_cmd *c,uint32_t s){(void)c;(void)s;assert(g_homed && !inhibited);}
void vdd_track_reset(void){}
void vdd_track_result(uint16_t *lo,uint16_t *hi){*lo=*hi=0;}
static void seal(uint8_t *p,unsigned n){unsigned sum=0;p[0]=0xf0;p[1]=n;p[2]=0;p[n-1]=0x55;for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;}
static void frame(unsigned id){uint8_t p[17]={0};unsigned n=id==1?17:11;p[3]=2;p[4]=0x71;p[5]=id;seal(p,n);host_body_frame(p,n);}
static void query(void){uint8_t p[25]={0};p[3]=1;p[4]=0x72;p[5]=4;p[19]=(query_n++&1)?EM_REC_Q_D2POS:EM_REC_Q_POS2D;p[20]=0x88;p[21]=0x13;seal(p,sizeof p);host_body_frame(p,sizeof p);}
void send_hook(const uint8_t *p){
    if(!strcmp(mode,"late-uart-cross") && !cross_done && p[5]==5 && host_millis-start_time>=290){host_millis+=20;cross_done=1;}
    if((!strcmp(mode,"drive-cross") && !brakes) || (!strcmp(mode,"settle-cross") && brakes)){
        if(!cross_done && p[5]==5){host_millis+=brakes?500:300;cross_done=1;}
    }
}
static void capture_wire(void){
    for(int i=0;i<sent_n;i++){
        uint8_t *p=sent[i];unsigned n=sent_len[i],sum=0;
        assert(n>=9 && p[0]==0xf0 && p[1]==n && p[n-1]==0x55);
        for(unsigned j=1;j<n-3;j++)sum+=p[j];assert(p[n-3]==(sum&255) && p[n-2]==(sum>>8));
        if(p[5]==0x16)wire_shutdown++;
        if(p[5]==6){wire_status++;for(unsigned j=45;j+2<n-3;j+=3){
            unsigned tag=p[j],value=p[j+1]|p[j+2]<<8;
            assert(tag==EM_REC_Q_POS2D || tag==EM_REC_Q_D2POS);
            unsigned expected=tag==EM_REC_Q_POS2D?focus_distance_code(focus_em06_to_counts(5000),EM_FOCAL_MM10):focus_counts_to_em06(focus_counts_for_code(5000,EM_FOCAL_MM10));
            assert(value==expected);wire_queries++;
        }}
    }
    assert(!sent_overflow);sent_n=0;
}
void vdd_track_sample(void){adc_samples++;}
static void schedule_tick(void){
    samples++;capture_wire();
    if(samples==320){
        if(!strcmp(mode,"settle-session"))frame(1);
        if(!strcmp(mode,"settle-shutdown"))frame(0x16);
        if(!strcmp(mode,"settle-stop")){uint8_t p[23]={0};p[3]=1;p[4]=0x72;p[5]=4;p[19]=EM_REC_STOP;seal(p,sizeof p);host_body_frame(p,sizeof p);}
    }
    if(samples==100){
        if(!strcmp(mode,"session"))frame(1);
        if(!strcmp(mode,"shutdown"))frame(0x16);
        if(!strcmp(mode,"stop")){uint8_t p[23]={0};p[3]=1;p[4]=0x72;p[5]=4;p[19]=EM_REC_STOP;seal(p,sizeof p);host_body_frame(p,sizeof p);}
        if(!strcmp(mode,"corrupt"))g_track=INT32_MAX;
    }
    if(!strcmp(mode,"shared-budget")){if(!brakes && samples%15000==0)host_millis++;}
    else if(strcmp(mode,"frozen-budget"))host_millis++;
    /* Hardware-boundary script offers real RX and VD. One query per 8 polls
     * avoids pretending frozen-clock million-poll input is a physical rate. */
    if(!strcmp(mode,"storm")){for(unsigned k=0;k<EM_QUERY_Q;k++)query();host_frame_sync();}
    else if(samples%8==0){query();host_frame_sync();}
}
static void compute_hook(void){
    assert(!lock_depth);
    if(conversion_action){unsigned action=conversion_action;conversion_action=0;frame(action);}
}
#include "worker.inc"
#include "pump.inc"
#include "home.inc"
#include "foreground.inc"
int main(int argc,char **argv){
    assert(argc==3);mode=argv[1];unsigned expect_snapshot=(unsigned)atoi(argv[2]);
    qualifying=expect_snapshot;ea9_packets_init();em_init();frame(0x0a);em_poll();assert(em_handshake_done);sent_n=0;
    if(!strcmp(mode,"wrap"))host_millis=UINT32_MAX-35;
    em_set_shutdown_inhibit_handler(motion_shutdown_inhibit);
    start_time=host_millis;abs_encoder_track_reset();resets=0;raw_reads=0;query();host_frame_sync();home_service();capture_wire();
    uint32_t elapsed=host_millis-start_time;
    int success=!strcmp(mode,"normal") || !strcmp(mode,"wrap") || !strcmp(mode,"stuck") || !strcmp(mode,"noise6") || !strcmp(mode,"ramp200") || !strcmp(mode,"ramp259") || !strcmp(mode,"storm") || !strcmp(mode,"uart-ordinary");
    if(qualifying && (!strcmp(mode,"ramp260") || !strcmp(mode,"late280")))success=1;
    if(success){assert(g_homed && g_home_state==HOME_READY && !inhibited && resets==1); if(!strcmp(mode,"late280") || !strcmp(mode,"ramp260"))assert(elapsed==340 && cutoff-start_time==300 && !brakes && !tcc.CC[0].reg && !tcc.CC[1].reg && !tcc.CC[2].reg && !tcc.CC[3].reg);}
    else {assert(!g_homed && !resets);assert(g_home_state==HOME_FAILED || g_home_state==HOME_CANCELLED);}
    if(!strcmp(mode,"moving") || !strcmp(mode,"wrong-way") || !strcmp(mode,"too-far") || !strcmp(mode,"release-drift") || !strcmp(mode,"final-drift") || !strcmp(mode,"noise7"))assert(!success);
    if(!strcmp(mode,"frozen-budget") || !strcmp(mode,"shared-budget"))assert(samples==HOME_POLL_LIMIT-1 && host_fault()==ST_HOME_BUDGET);
    if(!strcmp(mode,"late280") && !qualifying){uint32_t h[8];memcpy(h,st_motion_data()+112,sizeof h);assert(h[0]==(0x39u|(ST_HOME_DRIVE<<8)) && h[5]-start_time==280 && (int32_t)h[4]==-2902 && h[7]-start_time==299 && elapsed==300);}
    if(!success){unsigned attempts=g_home_attempts;home_service();assert(g_home_attempts==attempts && !g_homed && drives==1);}
    assert(drives==1 && !lock_depth);
    printf("home mode=%s qualified=%u elapsed=%u samples=%u ready=%u fault=%u cutoff=%u resets=%u\n",mode,qualifying,elapsed,samples,g_homed,host_fault(),cutoff?cutoff-start_time:0,resets);
    (void)expect_snapshot;(void)foreground;(void)post_failure;(void)foreground_step;
    return 0;
}
