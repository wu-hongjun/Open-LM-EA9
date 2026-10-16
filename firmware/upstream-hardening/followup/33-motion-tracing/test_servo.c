/* Synthetic coordinates only. The linked servo body is the pinned production C. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "servo.h"
#include "motion_trace.h"
#include "startup_trace.h"
static uint32_t now, words[1024];
static unsigned words_n, reads, drives, brakes, attaches, pumps;
static int inhibited, scenario, retargeted;
static int32_t sequence[32];
static unsigned sequence_n;
static void word(uint32_t kind, int32_t value) {
    assert(words_n+2<=sizeof words/sizeof *words);
    words[words_n++]=kind;words[words_n++]=(uint32_t)value;
}
uint32_t millis(void) {return now;}
int32_t abs_encoder_track(void) {
    assert(reads<sequence_n); int32_t p=sequence[reads++];
    now+=5;word(1,p);return p;
}
uint16_t abs_encoder_raw(void) {assert(0);return 0;}
uint8_t motor_is_inhibited(void) {return inhibited;}
void motor_inhibit(void) {inhibited=1;word(2,1);}
void motor_attach_pins(void) {attaches++;word(3,1);}
void motor_drive(int16_t duty) {drives++;word(4,duty);}
void motor_brake(void) {brakes++;word(5,1);}
static void pump(int32_t pos) {pumps++;word(6,pos);}
static uint8_t abort_move(void) {return scenario==6 && reads>=7;}
static uint8_t retarget(int32_t *target) {
    if (scenario>=4 && scenario<=6 && !retargeted && reads==2) {
        retargeted=1;*target=200;
        st_motion_command(3,(uint16_t)-250);return 1;
    }
    return 0;
}
int main(int argc,char **argv) {
    assert(argc==3);scenario=atoi(argv[1]);
    int32_t start=500,target=1000;
    const int32_t positive[]={490,460,420,380,379,999};
    const int32_t negative[]={1010,1080,1120,1121,501};
    const int32_t runaway[]={510,1000,1600,1601,999};
    const int32_t runneg[]={990,500,-100,-101,501};
    /* Reversal coasts old way, rebase follows it, then turns and rearms.
     * Crossing >120 behind rebase must capture 640 as the leg start. */
    const int32_t reversal[]={520,550,640,630,700,760,761,0};
    const int32_t rebase_expiry[]={520,550,640,640,640,640,640,761,0};
    const int32_t rebase_abort[]={520,550,640,630,500,200,0,0};
    const int32_t *p=positive;sequence_n=sizeof positive/sizeof *positive;
    if(scenario==1){p=negative;sequence_n=5;start=1000;target=500;}
    if(scenario==2){p=runaway;sequence_n=5;}
    if(scenario==3){p=runneg;sequence_n=5;start=1000;target=500;}
    if(scenario==4){p=reversal;sequence_n=8;}
    if(scenario==5){p=rebase_expiry;sequence_n=9;}
    if(scenario==6){p=rebase_abort;sequence_n=8;}
    memcpy(sequence,p,sequence_n*sizeof *p);
    struct servo_cfg cfg={.stop_ms=30,.v_cruise=10000,.ff_div=40,.kp_div=50,
        .tau_ms=33,.v_arrive=500,.arrive_steps=2,.duty_max=1000,.tolerance=12,
        .noise=8,.timeout_ms=400,.stall_ms=scenario==5?25:300,.pump=pump,
        .abort=abort_move,.retarget=retarget,.retarget_max=1,.retarget_min=10,
        .reverse_brake_ms=10,.reverse_brake_above=500};
    struct servo_result r;
    st_motion_command(1,0x1234);servo_move_from(start,target,&cfg,&r);
    assert(reads==sequence_n);
    assert(r.outcome==(scenario==2||scenario==3?SERVO_RUNAWAY:scenario==6?SERVO_ABORTED:SERVO_WRONG_WAY));
    assert(inhibited==(scenario!=6));
    /* A later unrelated command and shutdown must not overwrite first fault. */
    st_motion_completion(scenario==6?ST_MC_ABORTED:ST_MC_SUPPRESSED,0);
    if(scenario!=6) {
        st_motion_command(7,0xffff);st_motion_begin(10,20,now+100,0);
        st_motion_sample(now+101,15);st_motion_leg(20,10,0);
        st_motion_drive(999);st_motion_finish(SERVO_OK);
        st_motion_completion(ST_MC_TX_RETURN,0x1c);
        st_note(ST_SHUTDOWN,1,0,0,0,0,now+102);
    }
    FILE *f=fopen(argv[2],"wb");assert(f);
    assert(fwrite(words,sizeof *words,words_n,f)==words_n);fclose(f);
    printf("{\"case\":%d,\"outcome\":%u,\"reads\":%u,\"drives\":%u,\"brakes\":%u,\"attaches\":%u,\"pumps\":%u,\"inhibited\":%d,\"trace\":\"",scenario,r.outcome,reads,drives,brakes,attaches,pumps,inhibited);
    const uint8_t *data=st_motion_data();for(unsigned i=0;i<ST_MOTION_BYTES;i++)printf("%02x",data[i]);
    puts("\"}");return 0;
}
