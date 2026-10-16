#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "abs_encoder.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
#include "servo.h"
#include "startup_trace.h"
#include "motion_trace.h"
extern uint32_t host_millis;
void host_body_frame(const uint8_t *, uint16_t);
uint32_t millis(void);
unsigned test_events(void);
unsigned test_event_code(void);
static int g_homed=1, g_aborted, inhibited;
static uint32_t g_focus_session, g_next_session;
static uint8_t g_abort_pending, g_abort_by_stop, g_next_pending, g_last_op;
static uint16_t g_last_target, g_focus_aborts, g_stops_idle;
static struct em_focus_cmd g_next;
static struct focus_pred g_pred;
static struct servo_result observed;
static unsigned observed_n, reads, idle_reads, active_reads, drives, reports;
static int32_t g_track;
static uint16_t g_track_last;
static int32_t first, here, moved, expected;
static unsigned action, expected_retargets;
static const char *scenario;
static uint32_t words[8192]; static unsigned word_n;
static void word(uint32_t k,int32_t v) {assert(word_n+2<8192);words[word_n++]=k;words[word_n++]=(uint32_t)v;}
extern uint8_t sent[256][256]; extern uint16_t sent_len[256]; extern int sent_n;

static void frame(unsigned id) {
    uint8_t p[17]={0}; unsigned n=id==1?17:11, sum=0;
    p[0]=0xf0;p[1]=n;p[3]=2;p[4]=0x71;p[5]=id;p[n-1]=0x55;
    for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
    host_body_frame(p,n);
}
static void command(unsigned mode, uint16_t operand, int stop) {
    uint8_t p[27]={0}; unsigned n=stop?23:27, sum=0;
    p[0]=0xf0;p[1]=n;p[3]=1;p[4]=0x72;p[5]=4;p[n-1]=0x55;
    p[19]=stop?EM_REC_STOP:EM_REC_MOVE;p[20]=operand;p[21]=operand>>8;p[23]=mode;
    for(unsigned i=1;i<n-3;i++)sum+=p[i];p[n-3]=sum;p[n-2]=sum>>8;
    host_body_frame(p,n);
}
uint8_t motor_is_inhibited(void) {return inhibited;}
void motor_inhibit(void) {inhibited=1;word(2,1);}
void motor_attach_pins(void) {word(3,1);}
void motor_drive(int16_t duty) {word(4,duty);if(duty){assert(active_reads && !inhibited);drives++;}}
void motor_brake(void) {word(5,1);}
uint16_t abs_encoder_raw(void) {
    reads++;
    if(!g_pred.active){idle_reads++;word(1,idle_reads==1?first:here);return idle_reads==1?first:here;}
    active_reads++;host_millis+=5;
    if(active_reads==1 && action){
        unsigned a=action;action=0;
        if(a==1 || a==0x16)frame(a);
        else if(a==2)command(0,0,1);
        else if(a==3)command(0,focus_counts_to_em06(2000),0);
        else if(a==4)command(4,100,0);
        else if(a==5)command(6,10,0);
        else if(a==6)command(0,focus_counts_to_em06(1000),0);
        else if(a==7)command(0,focus_counts_to_em06(1008),0);
        else if(a==8){motor_inhibit();}
    }
    word(1,moved);return moved;
}
#include "tracker.inc"
static void pump(int32_t pos) {word(6,pos);focus_pred_sample(&g_pred,pos,millis());}
static void focus_report(void) {reports++;(void)abs_encoder_track();}
static void focus_scan(const struct em_focus_cmd *c) {(void)c;assert(0);}
static void focus_drive(const struct em_focus_cmd *c) {(void)c;assert(0);}
static void observe(const struct servo_result *r) {observed=*r;observed_n++;}
#include "main.inc"
int main(int argc,char **argv) {
    assert(argc==3);scenario=argv[1];
    em_init();frame(0x0a);em_poll();assert(em_handshake_done);
    first=here=500;moved=532;expected=1000;
    unsigned mode=0;uint16_t operand=focus_counts_to_em06(expected);
    if(!strcmp(scenario,"upper")){first=here=5800;moved=5832;expected=5952;operand=FOCUS_EM06_HI;}
    else if(!strcmp(scenario,"lower")){first=here=152;moved=120;expected=0;operand=FOCUS_EM06_LO;}
    else if(!strcmp(scenario,"relative")){first=1000;here=1020;moved=1052;mode=4;operand=100;expected=1400;}
    else if(!strcmp(scenario,"defocus")){first=1000;here=1020;moved=1052;mode=6;operand=10;expected=1320;}
    else if(!strcmp(scenario,"relative-clamp")){first=5800;here=5810;moved=5842;mode=4;operand=100;expected=5952;}
    else if(!strcmp(scenario,"distance")){mode=3;operand=0x700;expected=0;moved=468;}
    else if(!strcmp(scenario,"wrongway")){moved=379;}
    else if(!strcmp(scenario,"runaway")){moved=1601;}
    else if(!strcmp(scenario,"stationary")){moved=here;}
    else if(!strcmp(scenario,"arrival")){first=here=800;moved=expected;}
    else if(!strcmp(scenario,"deadband")){first=here=moved=expected;}
    else if(!strcmp(scenario,"session")){action=1;}
    else if(!strcmp(scenario,"shutdown")){action=0x16;}
    else if(!strcmp(scenario,"stop")){action=2;}
    else if(!strcmp(scenario,"fault")){action=8;}
    else if(!strcmp(scenario,"retarget")){action=3;expected=2000;expected_retargets=1;}
    else if(!strcmp(scenario,"retarget-relative")){action=4;expected=moved+400;expected_retargets=1;}
    else if(!strcmp(scenario,"retarget-defocus")){action=5;expected=moved+320;expected_retargets=1;}
    else if(!strcmp(scenario,"retarget-repeat")){action=6;}
    else if(!strcmp(scenario,"retarget-small")){action=7;}
    struct em_focus_cmd c;
    command(mode,operand,0);assert(em_take_focus_cmd(&c));
    unsigned epoch=em_session_generation();
    if(!strcmp(scenario,"stale"))epoch--;
    focus_exec(&c,epoch);
    int cancelled=!strcmp(scenario,"session") || !strcmp(scenario,"shutdown") || !strcmp(scenario,"stop") || !strcmp(scenario,"fault");
    int bypass=!strcmp(scenario,"deadband") || !strcmp(scenario,"stale");
    int good=!g_pred.active;
    if(bypass)good &= observed_n==0 && drives==0 && test_events()==(!strcmp(scenario,"deadband")?1u:0u);
    else if(cancelled)good &= observed_n==1 && observed.outcome==SERVO_ABORTED && drives==0 && test_events()==(!strcmp(scenario,"stop")?1u:0u);
    else good &= observed_n==1 && observed.target==expected && observed.retargets==expected_retargets;
    if(!strcmp(scenario,"wrongway") || !strcmp(scenario,"runaway"))good &= inhibited && test_events()==0;
    if(!strcmp(scenario,"arrival"))good &= observed.outcome==SERVO_OK;
    if(!strcmp(scenario,"retarget-small"))good &= g_pred.target==1008;
    if(!strcmp(scenario,"stop"))good &= test_event_code()==EM_REC_STOP;
    printf("{\"case\":\"%s\",\"pass\":%s,\"target\":%d,\"expected\":%d,\"start\":%d,\"retargets\":%u,\"outcome\":%u,\"events\":%u,\"drives\":%u,\"reads\":%u,\"reports\":%u}\n",scenario,good?"true":"false",observed.target,expected,observed.start,observed.retargets,observed.outcome,test_events(),drives,reads,reports);
    FILE *f=fopen(argv[2],"wb");assert(f);fwrite(words,sizeof *words,word_n,f);
    for(int i=0;i<sent_n;i++){fwrite(&sent_len[i],sizeof sent_len[i],1,f);fwrite(sent[i],1,sent_len[i],f);}fclose(f);
    printf("{\"trace\":\"");const uint8_t *data=st_motion_data();for(unsigned i=0;i<ST_MOTION_BYTES;i++)printf("%02x",data[i]);puts("\"}");
    return !good;
}
